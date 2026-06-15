from collections.abc import Callable

from app.schemas import PageDocument
from app.services.image_gen import generate_page_images


def run_image_agent(
    page: PageDocument,
    on_image_progress: Callable[[int, int, str], None] | None = None,
) -> PageDocument:
    page.images = generate_page_images(
        puja=page.puja,
        city=page.city,
        state=page.state,
        country=page.country,
        slug=page.slug,
        image_prompts=page.image_prompts or None,
        on_image_progress=on_image_progress,
    )
    return page
