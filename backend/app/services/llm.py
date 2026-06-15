import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.prompts.page_content import (
    CONTENT_META_SYSTEM,
    CONTENT_PART_A_SYSTEM,
    CONTENT_PART_B_SYSTEM,
    PART_B_RETRY_SYSTEM,
    build_content_user_prompt,
    build_part_b_retry_prompt,
    build_part_b_user_prompt,
)
from app.services.content_html import extract_content_from_llm_response, is_valid_html_content
from app.services.gemini import gemini_service

logger = logging.getLogger("llm")
settings = get_settings()

RATE_LIMIT_MARKERS = ("rate_limit", "429", "413", "too many requests", "too large", "tpm")
RETRY_DELAYS_SECONDS = (5, 15, 30, 60)
LLM_CALL_DELAY_SECONDS = 4
HUMANIZE_LLM_CHAR_LIMIT = 12_000
CONTENT_MAX_TOKENS = 8192


def slugify(*parts: str) -> str:
    raw = "-".join(parts).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    return raw.strip("-")


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in RATE_LIMIT_MARKERS)


class LlmService:
    def __init__(self) -> None:
        self._groq_client: OpenAI | None = None
        self._openai_client: OpenAI | None = None
        self._provider = settings.effective_llm_provider
        self._model = settings.active_llm_model

        if settings.groq_api_key:
            self._groq_client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
            )
        if settings.openai_api_key:
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    def is_live(self) -> bool:
        if settings.use_mock_llm or self._provider == "mock":
            return False
        return self._has_groq() or gemini_service.is_configured() or self._openai_client is not None

    def _has_groq(self) -> bool:
        client = getattr(self, "_groq_client", None)
        return client is not None and bool(settings.groq_api_key)

    def ping(self) -> dict[str, Any]:
        if not self.is_live():
            return {
                "status": "mock",
                "provider": self._provider,
                "model": self._model,
                "message": "Set GROQ_API_KEY or GEMINI_API_KEY for live generation",
            }

        result = self._chat_json(
            "You respond only with valid JSON.",
            'Return {"ok": true, "message": "NamanPuja LLM connected"}',
            max_tokens=256,
        )
        if result.get("ok"):
            return {
                "status": "ok",
                "provider": result.get("_provider", self._provider),
                "model": result.get("_model", self._model),
                "response": {k: v for k, v in result.items() if not k.startswith("_")},
            }
        raise RuntimeError(f"Unexpected LLM ping response: {result}")

    def _pause_between_calls(self) -> None:
        time.sleep(LLM_CALL_DELAY_SECONDS)

    def _with_retries(self, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt, delay in enumerate(RETRY_DELAYS_SECONDS):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                if not _is_rate_limit_error(exc) or attempt == len(RETRY_DELAYS_SECONDS) - 1:
                    raise
                logger.warning("llm_rate_limit_retry attempt=%s delay=%s error=%s", attempt + 1, delay, exc)
                time.sleep(delay)
        if last_error:
            raise last_error
        raise RuntimeError("LLM call failed without an error")

    def _chat_json(self, system: str, user: str, max_tokens: int = CONTENT_MAX_TOKENS) -> dict[str, Any]:
        errors: list[str] = []

        if self._has_groq():
            try:
                return self._with_retries(
                    lambda: self._call_groq(system, user, max_tokens),
                )
            except Exception as exc:
                errors.append(f"groq: {exc}")
                logger.warning("groq_content_failed error=%s", exc)

        if gemini_service.is_configured():
            try:
                return self._with_retries(
                    lambda: self._call_gemini(system, user, max_tokens),
                )
            except Exception as exc:
                errors.append(f"gemini: {exc}")
                logger.warning("gemini_content_fallback_failed error=%s", exc)

        if errors:
            raise RuntimeError("Content generation failed: " + "; ".join(errors))
        return {}

    def _call_groq(self, system: str, user: str, max_tokens: int) -> dict[str, Any]:
        result = self._call_openai_compatible(
            self._groq_client,
            settings.groq_model,
            system,
            user,
            max_tokens,
        )
        result["_provider"] = "groq"
        result["_model"] = settings.groq_model
        return result

    def _call_gemini(self, system: str, user: str, max_tokens: int) -> dict[str, Any]:
        result = gemini_service.chat_json(system, user, max_output_tokens=max_tokens)
        result["_provider"] = "gemini"
        result["_model"] = settings.gemini_content_model
        return result

    @staticmethod
    def _call_openai_compatible(
        client: OpenAI | None,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not client:
            raise RuntimeError("LLM client not configured")

        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.55,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def generate_content(
        self,
        puja: str,
        city: str,
        state: str,
        country: str,
        feedback_context: str = "",
        on_progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        slug = slugify(puja, "in", city, state)

        if not self.is_live():
            return self._mock_content(puja, city, state, country, slug)

        def progress(message: str) -> None:
            if on_progress:
                on_progress(message)

        user = build_content_user_prompt(puja, city, state, country, slug, feedback_context)
        progress(f"Drafting introduction and local sections for {puja} in {city}…")
        part_a = self._chat_json(CONTENT_PART_A_SYSTEM, user)
        part_a_content = extract_content_from_llm_response(part_a, part="a")
        if not part_a_content:
            part_a_content = extract_content_from_llm_response({"content": part_a.get("content", "")}, part="a")
        slug = part_a.get("slug", slug) if isinstance(part_a.get("slug"), str) else slug

        self._pause_between_calls()
        progress(f"Writing rituals, benefits, and booking sections for {city}…")
        part_b_user = build_part_b_user_prompt(
            puja, city, state, country, part_a_content, feedback_context
        )
        part_b = self._chat_json(CONTENT_PART_B_SYSTEM, part_b_user)
        part_b_content = extract_content_from_llm_response(part_b, part="b")

        if not is_valid_html_content(part_b_content, min_h2=5):
            logger.warning("part_b_invalid_html retrying puja=%s city=%s", puja, city)
            self._pause_between_calls()
            retry_user = build_part_b_retry_prompt(
                puja,
                city,
                state,
                part_b_content or json.dumps(part_b)[:6000],
            )
            retry = self._chat_json(PART_B_RETRY_SYSTEM, retry_user)
            part_b_content = extract_content_from_llm_response(retry, part="b")

        merged_content = f"{part_a_content}\n{part_b_content}".strip()

        self._pause_between_calls()
        progress(f"Building FAQ, SEO, and image prompts for {puja}…")
        meta_user = build_content_user_prompt(puja, city, state, country, slug, feedback_context)
        meta = self._chat_json(CONTENT_META_SYSTEM, meta_user, max_tokens=4096)

        result = {
            "slug": slug,
            "content": merged_content,
            "faq": meta.get("faq", []),
            "seo": self._normalize_seo(meta.get("seo", {}), puja, city, state, country),
            "areas_served": self._normalize_string_list(meta.get("areas_served"), [city, state]),
            "occasions": self._normalize_string_list(meta.get("occasions"), []),
            "local_landmarks": self._normalize_string_list(meta.get("local_landmarks"), []),
            "image_prompts": self._default_image_prompts(puja, city, state, country, slug),
        }
        return result

    @staticmethod
    def _normalize_string_list(value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return fallback

    @staticmethod
    def _normalize_seo(
        seo_data: dict[str, Any],
        puja: str,
        city: str,
        state: str,
        country: str,
    ) -> dict[str, Any]:
        normalized = dict(seo_data)
        normalized["keywords"] = LlmService._normalize_string_list(
            normalized.get("keywords"),
            [puja, city, state, country, "Hindu priest", "home puja"],
        )
        normalized["title"] = str(normalized.get("title") or f"{puja} in {city}, {state} | NamanPuja")
        normalized["description"] = str(
            normalized.get("description")
            or f"Book {puja} in {city}, {state}. Authentic Vedic rituals with Naman Puja."
        )[:165]
        normalized["focus_keyword"] = str(normalized.get("focus_keyword") or f"{puja} in {city}")
        normalized["tagline"] = str(normalized.get("tagline") or f"Authentic {puja} in {city}")
        normalized["breadcrumb"] = str(
            normalized.get("breadcrumb") or f"Home > {country} > {state} > {city} > {puja}"
        )
        return normalized

    def humanize_content(self, content: str, feedback_context: str = "") -> str:
        if not self.is_live():
            return self._lightweight_humanize(content)

        if len(content) > HUMANIZE_LLM_CHAR_LIMIT:
            logger.info("humanize_skipped_llm content_chars=%s", len(content))
            return self._lightweight_humanize(content)

        system = (
            "Rewrite the HTML to sound natural and warm. Keep all headings and facts. "
            "Do not shorten. Return JSON: {humanized_content: string}."
        )
        excerpt = content[:6000] + "\n...\n" + content[-4000:] if len(content) > 10_000 else content
        user = f"Content:\n{excerpt}\n\n{feedback_context}"
        result = self._chat_json(system, user, max_tokens=CONTENT_MAX_TOKENS)
        return result.get("humanized_content", content)

    @staticmethod
    def _lightweight_humanize(content: str) -> str:
        replacements = [
            ("Furthermore,", "Also,"),
            ("Additionally,", "Plus,"),
            ("It is important to note that", ""),
            ("In today's world,", ""),
            ("delve into", "explore"),
            ("tapestry of", ""),
        ]
        for old, new in replacements:
            content = content.replace(old, new)
        return content

    def generate_image_metadata(
        self,
        puja: str,
        city: str,
        state: str,
        country: str,
        slug: str,
        image_prompts: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return {"images": self._default_image_prompts(puja, city, state, country, slug)}

    def run_qc(
        self,
        content: str,
        seo: dict[str, Any],
        slug: str,
        feedback_context: str = "",
    ) -> dict[str, Any]:
        issues: list[str] = []

        min_words = 50 if settings.use_mock_llm else 2800
        min_h2 = 2 if settings.use_mock_llm else 10
        word_count = len(re.sub(r"<[^>]+>", " ", content).split())
        if word_count < min_words:
            issues.append(f"Content is too short ({word_count} words; minimum {min_words} for 10+ pages).")
        if not seo.get("title"):
            issues.append("SEO title is missing.")
        if not seo.get("description"):
            issues.append("SEO description is missing.")
        if len(seo.get("description", "")) > 165:
            issues.append("SEO description exceeds 165 characters.")
        if "lorem ipsum" in content.lower():
            issues.append("Placeholder text detected.")
        if "'section8'" in content or '"section8"' in content:
            issues.append("Raw JSON structure detected in content — sections must be HTML.")
        if not slug or " " in slug:
            issues.append("Invalid slug format.")
        if content.count("<h2") < min_h2:
            issues.append(f"Content should include at least {min_h2} section headings (h2).")
        if not settings.use_mock_llm and content.count("<h3") < 8:
            issues.append("Content should include h3 sub-headings for rituals and benefits.")
        if not settings.use_mock_llm and content.count("<li") < 12:
            issues.append("Content should include bullet lists with local details.")
        if not settings.use_mock_llm and len(seo.get("keywords", [])) < 10:
            issues.append("SEO keywords should include at least 10 location-specific terms.")

        if not self.is_live():
            return {"passed": len(issues) == 0, "issues": issues}

        system = (
            "QC agent for NamanPuja pages. Check grammar, SEO, structure, location specificity. "
            "Return JSON: {passed: boolean, issues: string[]}."
        )
        excerpt = (
            content[:2500] + "\n...[middle omitted]...\n" + content[-1500:]
            if len(content) > 5000
            else content
        )
        user = f"Slug: {slug}\nSEO: {json.dumps(seo)}\nContent excerpt:\n{excerpt}\n{feedback_context}"
        result = self._chat_json(system, user, max_tokens=1024)
        merged_issues = list(dict.fromkeys(issues + result.get("issues", [])))
        passed = len(merged_issues) == 0
        return {"passed": passed, "issues": merged_issues}

    @staticmethod
    def _default_image_prompts(
        puja: str, city: str, state: str, country: str, slug: str
    ) -> list[dict[str, str]]:
        from app.services.image_prompts import build_distinct_image_specs

        return build_distinct_image_specs(puja, city, state, country, slug, None)

    @staticmethod
    def _mock_content(puja: str, city: str, state: str, country: str, slug: str) -> dict[str, Any]:
        title = f"{puja} in {city}, {state} | NamanPuja"
        return {
            "slug": slug,
            "content": (
                f'<h1>{puja} in {city}, {state} – Divine Blessings for Your Family</h1>'
                f'<p class="lead">Book authentic {puja} services in {city}, {state}, {country} '
                f"with experienced Vedic priests from Naman Puja.</p>"
                f"<h2>Why {city} families choose {puja}</h2>"
                f"<ul><li>Experienced Hindu priests</li><li>Home and venue ceremonies</li>"
                f"<li>Authentic Vedic rituals</li></ul>"
                f"<h2>Traditional rituals included</h2>"
                f"<h3>Ganesh Puja</h3><p>Seeking blessings before the main ceremony.</p>"
                f"<h3>Satyanarayan Katha</h3><p>Recitation of the sacred story.</p>"
                f"<h2>Book {puja} in {city} today</h2>"
                f"<p>Contact Naman Puja to schedule your ceremony.</p>"
            ),
            "faq": [
                {
                    "question": f"Can {puja} be performed in {city}?",
                    "answer": f"Yes. Naman Puja provides {puja} services throughout {city}, {state}, and surrounding areas.",
                },
                {
                    "question": f"How long does {puja} take?",
                    "answer": "A complete ceremony typically takes 2 to 3 hours.",
                },
            ],
            "seo": {
                "title": title,
                "description": (
                    f"Book {puja} in {city}, {state}. Experienced priests, authentic Vedic rituals, "
                    "and convenient home puja services via Naman Puja."
                ),
                "keywords": [puja, city, state, country, "Hindu priest", "home puja", "Vedic rituals"],
                "focus_keyword": f"{puja} in {city}",
                "tagline": f"Authentic {puja} services in {city}",
                "breadcrumb": f"Home > {country} > {state} > {city} > {puja}",
            },
            "areas_served": [city, state],
            "occasions": ["Housewarming", "Birthday", "Anniversary"],
            "image_prompts": LlmService._default_image_prompts(puja, city, state, country, slug),
        }


llm_service = LlmService()
