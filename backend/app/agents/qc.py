from app.schemas import PageDocument, QcResult
from app.services.llm import llm_service


def run_qc_agent(page: PageDocument, feedback_context: str = "") -> PageDocument:
    seo = page.seo.model_dump() if page.seo else {}
    result = llm_service.run_qc(page.content, seo, page.slug, feedback_context=feedback_context)
    page.qc = QcResult(passed=result.get("passed", False), issues=result.get("issues", []))
    return page
