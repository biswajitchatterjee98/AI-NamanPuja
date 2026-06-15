import html
import json
import re
from typing import Any

_HTML_TAG_PATTERN = re.compile(r"</?(?:h[1-3]|p|ul|ol|li)\b", re.IGNORECASE)
_JSON_ARTIFACT_PATTERN = re.compile(r"['\"]section\d+['\"]\s*:")


def is_valid_html_content(content: str, min_h2: int = 4) -> bool:
    if not content or not content.strip():
        return False
    if _JSON_ARTIFACT_PATTERN.search(content):
        return False
    if content.strip().startswith(("{", "[")):
        return False
    if not _HTML_TAG_PATTERN.search(content):
        return False
    return content.lower().count("<h2") >= min_h2


def extract_content_from_llm_response(data: dict[str, Any], part: str = "b") -> str:
    raw = data.get("content")
    if isinstance(raw, str) and raw.strip():
        converted = _coerce_to_html(raw)
        if converted:
            return converted

    if isinstance(raw, dict):
        converted = structured_sections_to_html(raw)
        if converted:
            return converted

    section_keys = [key for key in data if re.match(r"section\d+", str(key), re.IGNORECASE)]
    if section_keys:
        converted = structured_sections_to_html({key: data[key] for key in sorted(section_keys)})
        if converted:
            return converted

    if part == "a" and data.get("slug"):
        for key in ("sections", "body", "html"):
            value = data.get(key)
            if isinstance(value, str):
                converted = _coerce_to_html(value)
                if converted:
                    return converted

    return ""


def structured_sections_to_html(sections: dict[str, Any]) -> str:
    chunks: list[str] = []

    for key in sorted(sections.keys(), key=_section_sort_key):
        block = sections[key]
        if isinstance(block, str):
            if _HTML_TAG_PATTERN.search(block):
                chunks.append(block)
            else:
                chunks.append(f"<p>{html.escape(block)}</p>")
            continue

        if not isinstance(block, dict):
            continue

        title = block.get("title") or block.get("heading") or _title_from_section_key(key)
        if title:
            chunks.append(f"<h2>{html.escape(str(title))}</h2>")

        description = block.get("description") or block.get("text") or block.get("content")
        if description:
            chunks.append(f"<p>{html.escape(str(description))}</p>")

        additional = block.get("additionalInfo") or block.get("additional_info")
        if additional:
            chunks.append(f"<p>{html.escape(str(additional))}</p>")

        cta = block.get("cta")
        if cta:
            chunks.append(f"<p>{html.escape(str(cta))}</p>")

        rituals = block.get("rituals") or block.get("items")
        if isinstance(rituals, list):
            for item in rituals:
                if not isinstance(item, dict):
                    continue
                item_title = item.get("title") or item.get("name")
                item_body = item.get("description") or item.get("text")
                if item_title:
                    chunks.append(f"<h3>{html.escape(str(item_title))}</h3>")
                if item_body:
                    chunks.append(f"<p>{html.escape(str(item_body))}</p>")

        benefits = block.get("benefits")
        if isinstance(benefits, list):
            for item in benefits:
                if not isinstance(item, dict):
                    continue
                item_title = item.get("title") or item.get("name")
                item_body = item.get("description") or item.get("text")
                if item_title:
                    chunks.append(f"<h3>{html.escape(str(item_title))}</h3>")
                if item_body:
                    chunks.append(f"<p>{html.escape(str(item_body))}</p>")

        neighborhoods = block.get("neighborhoods") or block.get("areas") or block.get("areas_served")
        if isinstance(neighborhoods, list):
            items = "".join(f"<li>{html.escape(str(n))}</li>" for n in neighborhoods if str(n).strip())
            if items:
                chunks.append(f"<ul>{items}</ul>")

    return "\n".join(chunks)


def _coerce_to_html(value: str) -> str:
    stripped = value.strip()
    if is_valid_html_content(stripped, min_h2=1):
        return stripped

    if stripped.startswith(("{", "[")):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return ""
        if isinstance(parsed, dict):
            return structured_sections_to_html(parsed)
        return ""

    return ""


def _section_sort_key(key: str) -> int:
    match = re.search(r"\d+", str(key))
    return int(match.group()) if match else 0


def _title_from_section_key(key: str) -> str:
    match = re.search(r"\d+", str(key))
    number = int(match.group()) if match else 0
    titles = {
        8: "Traditional Rituals",
        9: "Spiritual Benefits",
        10: "Why This Location is Ideal for Hindu Ceremonies",
        11: "Areas We Serve",
        12: "Celebrate Faith",
        13: "Create Sacred Memories",
        14: "Book Today",
    }
    return titles.get(number, "Section")
