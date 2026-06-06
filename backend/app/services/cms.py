import logging
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import PageDocument

logger = logging.getLogger("cms")
settings = get_settings()


class CmsService:
    async def upload_page(self, page: PageDocument) -> dict[str, Any]:
        if not settings.cms_upload_enabled:
            logger.info("cms_upload_skipped slug=%s (CMS_UPLOAD_ENABLED=false)", page.slug)
            return {"slug": page.slug, "status": "skipped", "reason": "upload_disabled"}

        if not settings.cms_base_url:
            raise ValueError("CMS_BASE_URL is required when upload is enabled")

        payload = {
            "slug": page.slug,
            "title": page.seo.title if page.seo else page.slug,
            "description": page.seo.description if page.seo else "",
            "content": page.content,
            "faq": [item.model_dump() for item in page.faq],
            "seo": page.seo.model_dump() if page.seo else {},
            "images": [item.model_dump() for item in page.images],
            "location": {
                "city": page.city,
                "state": page.state,
                "country": page.country,
            },
            "puja": page.puja,
        }

        headers = {"Authorization": f"Bearer {settings.cms_api_key}"} if settings.cms_api_key else {}
        url = f"{settings.cms_base_url.rstrip('/')}/pages"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json() if response.content else {"status": "uploaded"}
            return {"slug": page.slug, "status": "uploaded", "cms_response": body}

    async def ping(self) -> bool:
        if not settings.cms_upload_enabled or not settings.cms_base_url:
            return True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.cms_base_url.rstrip('/')}/health")
                return response.status_code < 500
        except Exception:
            return False


cms_service = CmsService()
