from collections.abc import Callable
from datetime import datetime, timezone

from app.sanitize import sanitize_html
from app.schemas import FaqItem, PageDocument, SeoMetadata
from app.services.llm import llm_service


def run_content_agent(
    page: PageDocument,
    feedback_context: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> PageDocument:
    result = llm_service.generate_content(
        puja=page.puja,
        city=page.city,
        state=page.state,
        country=page.country,
        feedback_context=feedback_context,
        on_progress=on_progress,
    )

    page.slug = result.get("slug", page.slug)
    page.content = sanitize_html(result.get("content", ""))
    page.faq = [
        FaqItem(**item)
        for item in result.get("faq", [])
        if isinstance(item, dict) and item.get("question") and item.get("answer")
    ]
    page.areas_served = result.get("areas_served", [])
    page.occasions = result.get("occasions", [])
    page.image_prompts = result.get("image_prompts", [])

    seo_data = result.get("seo", {})
    if seo_data:
        page.seo = SeoMetadata(**seo_data)
    page.generated_at = datetime.now(timezone.utc)
    return page
