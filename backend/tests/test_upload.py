import pytest

from app.schemas import BatchStatus, PageDocument, SeoMetadata
from app.agents import upload as upload_module


@pytest.mark.asyncio
async def test_partial_upload_status(monkeypatch):
    pages = [
        PageDocument(
            batch_id="batch1",
            puja="Ganesh Puja",
            city="NYC",
            state="NY",
            country="USA",
            slug="ganesh-puja-in-nyc",
            content="<p>test</p>",
            seo=SeoMetadata(title="t", description="d"),
        )
    ]

    async def fake_get_pages(_batch_id):
        return pages

    calls = []

    async def fake_upload_page(page):
        if page.slug.endswith("nyc"):
            raise RuntimeError("cms down")
        return {"status": "uploaded"}

    async def fake_update_status(batch_id, status, **extra):
        calls.append((batch_id, status))

    async def fake_upsert(page):
        return page

    monkeypatch.setattr(upload_module.db, "get_pages_for_batch", fake_get_pages)
    monkeypatch.setattr(upload_module.cms_service, "upload_page", fake_upload_page)
    monkeypatch.setattr(upload_module.db, "update_batch_status", fake_update_status)
    monkeypatch.setattr(upload_module.db, "upsert_page", fake_upsert)

    await upload_module.upload_batch_pages("batch1")
    assert calls[-1][1] == BatchStatus.APPROVED
