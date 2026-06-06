import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger("llm")
settings = get_settings()


def slugify(*parts: str) -> str:
    raw = "-".join(parts).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    return raw.strip("-")


class LlmService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if not settings.use_mock_llm and settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        if settings.use_mock_llm or not self._client:
            return {}

        response = self._client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
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
    ) -> dict[str, Any]:
        slug = slugify(puja, "in", city)

        if settings.use_mock_llm or not self._client:
            return self._mock_content(puja, city, state, country, slug)

        system = (
            "You are an expert Hindu puja content writer for NamanPuja.com. "
            "Return JSON with keys: content (HTML string), faq (array of {question, answer}), "
            "seo ({title, description, keywords array}), slug (string)."
        )
        user = (
            f"Write a SEO-optimized service page for {puja} in {city}, {state}, {country}. "
            f"Suggested slug: {slug}. "
            f"{feedback_context}"
        )
        result = self._chat_json(system, user)
        result.setdefault("slug", slug)
        return result

    def humanize_content(self, content: str, feedback_context: str = "") -> str:
        if settings.use_mock_llm or not self._client:
            return content.replace("Furthermore,", "Also,").replace("Additionally,", "Plus,")

        system = (
            "Rewrite the HTML content to sound natural and human. "
            "Reduce AI-like phrasing. Return JSON: {humanized_content: string}."
        )
        user = f"Content:\n{content}\n\n{feedback_context}"
        result = self._chat_json(system, user)
        return result.get("humanized_content", content)

    def generate_image_metadata(self, puja: str, city: str, slug: str) -> dict[str, Any]:
        if settings.use_mock_llm or not self._client:
            return {
                "images": [
                    {
                        "filename": f"{slug}-hero.jpg",
                        "caption": f"{puja} ceremony in {city}",
                        "alt": f"{puja} performed in {city}",
                    }
                ]
            }

        system = (
            "Return JSON with images array. Each item: filename, caption, alt. "
            "Use descriptive, SEO-friendly alt text."
        )
        user = f"Puja: {puja}, City: {city}, slug: {slug}"
        return self._chat_json(system, user)

    def run_qc(
        self,
        content: str,
        seo: dict[str, Any],
        slug: str,
        feedback_context: str = "",
    ) -> dict[str, Any]:
        issues: list[str] = []

        if len(content) < 200:
            issues.append("Content is too short (minimum 200 characters).")
        if not seo.get("title"):
            issues.append("SEO title is missing.")
        if not seo.get("description"):
            issues.append("SEO description is missing.")
        if len(seo.get("description", "")) > 160:
            issues.append("SEO description exceeds 160 characters.")
        if "lorem ipsum" in content.lower():
            issues.append("Placeholder text detected.")
        if not slug or " " in slug:
            issues.append("Invalid slug format.")

        if settings.use_mock_llm or not self._client:
            return {"passed": len(issues) == 0, "issues": issues}

        system = (
            "You are a content QC agent. Check grammar, SEO, and template compliance. "
            "Return JSON: {passed: boolean, issues: string[]}."
        )
        user = f"Slug: {slug}\nSEO: {json.dumps(seo)}\nContent:\n{content}\n{feedback_context}"
        result = self._chat_json(system, user)
        merged_issues = list(dict.fromkeys(issues + result.get("issues", [])))
        return {"passed": result.get("passed", len(merged_issues) == 0) and len(merged_issues) == 0, "issues": merged_issues}

    @staticmethod
    def _mock_content(puja: str, city: str, state: str, country: str, slug: str) -> dict[str, Any]:
        title = f"{puja} in {city} | NamanPuja"
        return {
            "slug": slug,
            "content": (
                f"<h1>{puja} in {city}</h1>"
                f"<p>Book authentic {puja} services in {city}, {state}, {country} with experienced priests.</p>"
                f"<p>Our team helps families perform {puja} with proper vidhi, samagri guidance, and scheduling support.</p>"
                f"<h2>Why choose NamanPuja</h2>"
                f"<ul><li>Verified pandits</li><li>Transparent pricing</li><li>Location-specific coordination</li></ul>"
            ),
            "faq": [
                {
                    "question": f"How do I book {puja} in {city}?",
                    "answer": "Submit your request on NamanPuja and our team will confirm priest availability and samagri details.",
                },
                {
                    "question": f"What is included in {puja}?",
                    "answer": "The package typically includes priest service, ritual guidance, and optional samagri support based on your needs.",
                },
            ],
            "seo": {
                "title": title,
                "description": f"Book {puja} in {city}, {state}. Trusted priests, clear process, and local coordination via NamanPuja.",
                "keywords": [puja, city, state, country, "puja booking", "hindu priest"],
            },
        }


llm_service = LlmService()
