from app.schemas import ImageAsset, PageDocument
from app.services.llm import llm_service
from app.services.storage import image_storage


def run_image_agent(page: PageDocument) -> PageDocument:
    metadata = llm_service.generate_image_metadata(page.puja, page.city, page.slug)
    images: list[ImageAsset] = []

    for item in metadata.get("images", []):
        filename = item.get("filename", f"{page.slug}-hero.jpg")
        path = image_storage.ensure_placeholder(filename, page.slug)
        images.append(
            ImageAsset(
                path=path,
                caption=item.get("caption", ""),
                alt=item.get("alt", ""),
            )
        )

    if not images:
        path = image_storage.ensure_placeholder(f"{page.slug}-hero.jpg", page.slug)
        images.append(ImageAsset(path=path, caption=f"{page.puja} in {page.city}", alt=f"{page.puja} in {page.city}"))

    page.images = images
    return page
