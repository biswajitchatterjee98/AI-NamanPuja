import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.content import run_content_agent
from app.agents.humanizer import run_humanizer_agent
from app.agents.image import run_image_agent
from app.agents.qc import run_qc_agent
from app.config import get_settings
from app.queue import is_batch_cancelled
from app.schemas import PageDocument

logger = logging.getLogger("pipeline")
settings = get_settings()


class BatchCancelled(Exception):
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        super().__init__(f"Batch {batch_id} was cancelled")


class PipelineState(TypedDict):
    batch_id: str
    pages: list[PageDocument]
    status: str
    qc_results: list[dict[str, Any]]
    feedback_context: str


def _ensure_not_cancelled(batch_id: str) -> None:
    if is_batch_cancelled(batch_id):
        raise BatchCancelled(batch_id)


def _run_parallel(pages: list[PageDocument], worker: Callable[[PageDocument], PageDocument]) -> list[PageDocument]:
    if len(pages) <= 1:
        return [worker(page) for page in pages]

    max_workers = min(settings.pipeline_max_workers, len(pages))
    results: list[PageDocument | None] = [None] * len(pages)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(worker, page): index for index, page in enumerate(pages)}
        for future in as_completed(future_map):
            index = future_map[future]
            results[index] = future.result()

    return [page for page in results if page is not None]


def _content_node(state: PipelineState) -> PipelineState:
    _ensure_not_cancelled(state["batch_id"])
    worker = lambda page: run_content_agent(page, state["feedback_context"])
    pages = _run_parallel(state["pages"], worker)
    return {**state, "pages": pages, "status": "content_complete"}


def _image_node(state: PipelineState) -> PipelineState:
    _ensure_not_cancelled(state["batch_id"])
    pages = _run_parallel(state["pages"], run_image_agent)
    return {**state, "pages": pages, "status": "image_complete"}


def _humanizer_node(state: PipelineState) -> PipelineState:
    _ensure_not_cancelled(state["batch_id"])
    worker = lambda page: run_humanizer_agent(page, state["feedback_context"])
    pages = _run_parallel(state["pages"], worker)
    return {**state, "pages": pages, "status": "humanized"}


def _qc_node(state: PipelineState) -> PipelineState:
    _ensure_not_cancelled(state["batch_id"])
    worker = lambda page: run_qc_agent(page, state["feedback_context"])
    pages = _run_parallel(state["pages"], worker)
    qc_results = [
        {
            "slug": page.slug,
            "passed": page.qc.passed if page.qc else False,
            "issues": page.qc.issues if page.qc else [],
        }
        for page in pages
    ]
    return {**state, "pages": pages, "qc_results": qc_results, "status": "qc_complete"}


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("content", _content_node)
    graph.add_node("image", _image_node)
    graph.add_node("humanizer", _humanizer_node)
    graph.add_node("qc", _qc_node)

    graph.set_entry_point("content")
    graph.add_edge("content", "image")
    graph.add_edge("image", "humanizer")
    graph.add_edge("humanizer", "qc")
    graph.add_edge("qc", END)

    return graph.compile()


def run_pipeline(batch_id: str, page_inputs: list[dict[str, str]], feedback_context: str = "") -> PipelineState:
    _ensure_not_cancelled(batch_id)

    pages = [
        PageDocument(
            batch_id=batch_id,
            puja=item["puja"],
            city=item["city"],
            state=item["state"],
            country=item["country"],
            generated_at=datetime.now(timezone.utc),
        )
        for item in page_inputs
    ]

    pipeline = build_pipeline()
    initial: PipelineState = {
        "batch_id": batch_id,
        "pages": pages,
        "status": "generating",
        "qc_results": [],
        "feedback_context": feedback_context,
    }

    logger.info("pipeline_start batch_id=%s page_count=%s workers=%s", batch_id, len(pages), settings.pipeline_max_workers)
    result = pipeline.invoke(initial)
    _ensure_not_cancelled(batch_id)
    logger.info("pipeline_complete batch_id=%s status=%s", batch_id, result["status"])
    return result
