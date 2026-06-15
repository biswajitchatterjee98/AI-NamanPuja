import hashlib
import io
import logging
import random
import re
from collections.abc import Callable

from PIL import Image, ImageDraw

from app.config import get_settings
from app.schemas import ImageAsset
from app.services.gemini import gemini_service
from app.services.image_prompts import SCENE_TYPES, build_distinct_image_specs
from app.services.storage import image_storage

logger = logging.getLogger("image_gen")
settings = get_settings()


def generate_page_images(
    puja: str,
    city: str,
    state: str,
    country: str,
    slug: str,
    image_prompts: list[dict[str, str]] | None = None,
    on_image_progress: Callable[[int, int, str], None] | None = None,
) -> list[ImageAsset]:
    specs = build_distinct_image_specs(puja, city, state, country, slug, image_prompts)
    images: list[ImageAsset] = []
    total = len(specs)

    for index, item in enumerate(specs):
        if on_image_progress:
            on_image_progress(index, total, item["caption"])

        prompt = item["prompt"]
        seed = _seed_for_image(slug, index, prompt)
        image_bytes, source = _generate_photorealistic_image(prompt, seed=seed, scene_index=index)
        path = image_storage.save_image_bytes(item["filename"], image_bytes)
        images.append(ImageAsset(path=path, caption=item["caption"], alt=item["alt"]))
        logger.info(
            "image_saved slug=%s file=%s bytes=%s source=%s scene=%s",
            slug,
            item["filename"],
            len(image_bytes),
            source,
            SCENE_TYPES[index][0],
        )

    return images


def _seed_for_image(slug: str, index: int, prompt: str) -> int:
    digest = hashlib.sha256(f"{slug}:{index}:{prompt}".encode()).hexdigest()
    return int(digest[:8], 16) % 1_000_000


def _generate_photorealistic_image(prompt: str, seed: int = 0, scene_index: int = 0) -> tuple[bytes, str]:
    if settings.use_mock_llm:
        return _procedural_devotional_image(seed, scene_index), "mock"

    attempts: list[tuple[str, Callable[[], bytes | None]]] = [
        ("pollinations_flux", lambda: gemini_service.generate_pollinations_image(prompt, seed=seed, model="flux")),
        ("pollinations_turbo", lambda: gemini_service.generate_pollinations_image(prompt, seed=seed + 17, model="turbo")),
        ("gemini", lambda: gemini_service.generate_image_bytes(prompt, seed=seed)),
        (
            "pollinations_realism",
            lambda: gemini_service.generate_pollinations_image(_simplify_prompt(prompt), seed=seed + 31, model="flux-realism"),
        ),
    ]

    for source, provider in attempts:
        try:
            image_bytes = provider()
            if image_bytes and len(image_bytes) > 2000:
                return image_bytes, source
        except Exception as exc:
            logger.warning("image_provider_failed source=%s error=%s", source, exc)

    logger.warning("image_all_providers_failed_using_procedural prompt=%s", prompt[:80])
    return _procedural_devotional_image(seed, scene_index), "procedural"


def _simplify_prompt(prompt: str) -> str:
    cleaned = re.sub(r"\s+", " ", prompt).strip()
    if len(cleaned) <= 140:
        return cleaned
    return cleaned[:140]


def _procedural_devotional_image(seed: int, scene_index: int) -> bytes:
    """Distinct altar-style fallback per scene index — no text."""
    width, height = 1200, 630
    random.seed(seed)
    palettes = [
        ("#1f1208", "#6b3a1f", "#e8a030"),
        ("#2a1810", "#4a2818", "#ffd878"),
        ("#1a1008", "#5c2e1a", "#c87828"),
    ]
    bg, mid, accent = palettes[scene_index % len(palettes)]
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line([(0, y), (width, y)], fill=_blend_hex(bg, mid, ratio))

    if scene_index == 0:
        _draw_ceremony_scene(draw, width, height, accent)
    elif scene_index == 1:
        _draw_altar_closeup(draw, width, height, accent)
    else:
        _draw_gathering_scene(draw, width, height, accent)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def _draw_ceremony_scene(draw: ImageDraw.ImageDraw, width: int, height: int, accent: str) -> None:
    altar_top = int(height * 0.5)
    draw.rectangle([width * 0.3, altar_top, width * 0.7, height * 0.82], fill="#4a2818", outline=accent, width=3)
    draw.ellipse([width * 0.44, altar_top - 70, width * 0.56, altar_top], fill="#8b4518", outline=accent, width=2)
    for offset in (-80, 0, 80):
        draw.ellipse([width * 0.5 + offset - 18, altar_top + 40, width * 0.5 + offset + 18, altar_top + 76], fill=accent)


def _draw_altar_closeup(draw: ImageDraw.ImageDraw, width: int, height: int, accent: str) -> None:
    draw.rectangle([width * 0.2, height * 0.25, width * 0.8, height * 0.85], fill="#3d2918", outline=accent, width=4)
    for x in range(int(width * 0.28), int(width * 0.72), 50):
        draw.ellipse([x, height * 0.35, x + 35, height * 0.35 + 35], fill=accent, outline="#c87828")
    for x in range(int(width * 0.32), int(width * 0.68), 70):
        draw.rectangle([x, height * 0.55, x + 14, height * 0.72], fill="#ffd878", outline=accent)


def _draw_gathering_scene(draw: ImageDraw.ImageDraw, width: int, height: int, accent: str) -> None:
    altar_top = int(height * 0.58)
    draw.rectangle([width * 0.35, altar_top, width * 0.65, height * 0.8], fill="#4a2818", outline=accent, width=2)
    for offset in (-120, -40, 40, 120):
        draw.ellipse(
            [width * 0.5 + offset - 22, altar_top + 90, width * 0.5 + offset + 22, altar_top + 134],
            fill="#5c3a22",
            outline=accent,
        )
    draw.ellipse([width * 0.46, altar_top - 50, width * 0.54, altar_top + 10], fill="#8b4518", outline=accent, width=2)


def _blend_hex(start: str, end: str, ratio: float) -> str:
    start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
    end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
    blended = tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * ratio) for i in range(3))
    return f"#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}"
