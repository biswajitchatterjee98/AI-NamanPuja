import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger("storage")
settings = get_settings()


class ImageStorage:
    def __init__(self) -> None:
        self._s3 = boto3.client("s3", region_name=settings.aws_region) if settings.use_s3_storage else None

    def save_image_bytes(self, filename: str, data: bytes) -> str:
        if settings.use_s3_storage and self._s3:
            key = f"pages/{filename}"
            content_type = "image/jpeg" if filename.endswith((".jpg", ".jpeg")) else "image/png"
            self._s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)
            base = settings.s3_public_base_url.rstrip("/")
            return f"{base}/{key}"

        local_dir = Path(settings.local_image_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        target = local_dir / filename
        target.write_bytes(data)
        return f"/images/{filename}"

    def resolve_local_path(self, public_path: str) -> Path | None:
        if not public_path.startswith("/images/"):
            return None
        filename = public_path.removeprefix("/images/")
        return Path(settings.local_image_dir) / filename

    def ensure_placeholder(self, filename: str, slug: str) -> str:
        if settings.use_s3_storage and self._s3:
            return self._s3_path(filename)

        local_dir = Path(settings.local_image_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        target = local_dir / filename

        if not target.exists():
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">'
                f'<rect width="100%" height="100%" fill="#f5e6d3"/>'
                f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
                f'font-family="Arial" font-size="42" fill="#5c3d2e">{slug}</text></svg>'
            )
            target.write_text(svg, encoding="utf-8")

        return f"/images/{filename}"

    def _s3_path(self, filename: str) -> str:
        key = f"pages/{filename}"
        try:
            self._s3.head_object(Bucket=settings.s3_bucket, Key=key)
        except ClientError:
            placeholder = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
                b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            self._s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=placeholder, ContentType="image/png")

        base = settings.s3_public_base_url.rstrip("/")
        return f"{base}/{key}"

    def ping(self) -> bool:
        if not settings.use_s3_storage:
            return True
        try:
            self._s3.head_bucket(Bucket=settings.s3_bucket)
            return True
        except Exception:
            return False


image_storage = ImageStorage()
