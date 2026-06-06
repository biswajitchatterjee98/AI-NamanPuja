from app.schemas import PageDocument
from app.services.llm import llm_service


def run_humanizer_agent(page: PageDocument, feedback_context: str = "") -> PageDocument:
    page.content = llm_service.humanize_content(page.content, feedback_context=feedback_context)
    return page
