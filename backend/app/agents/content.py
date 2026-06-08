from datetime import datetime, timezone

from app.sanitize import sanitize_html
from app.schemas import FaqItem, PageDocument, SeoMetadata
from app.services.llm import llm_service


def run_content_agent(page: PageDocument, feedback_context: str = "") -> PageDocument:
    result = llm_service.generate_content(
        puja=page.puja,
        city=page.city,
        state=page.state,
        country=page.country,
        feedback_context=feedback_context,
    )

    page.slug = result.get("slug", page.slug)
    page.content = sanitize_html(result.get("content", ""))
    page.faq = [FaqItem(**item) for item in result.get("faq", [])]
    seo_data = result.get("seo", {})
    if seo_data:
        page.seo = SeoMetadata(**seo_data)
    page.generated_at = datetime.now(timezone.utc)
    return page
