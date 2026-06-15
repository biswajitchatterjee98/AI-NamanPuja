import re

IMAGE_COUNT = 3

SCENE_TYPES = (
    ("ceremony", "Priest-led ceremony"),
    ("altar", "Sacred altar & samagri"),
    ("devotees", "Family & devotees"),
)

IMAGE_QUALITY_SUFFIX = (
    "Award-winning editorial photograph, photorealistic, cinematic natural lighting, "
    "rich authentic colors, shallow depth of field, highly detailed textures, "
    "respectful Hindu devotional scene, no cartoon, no illustration, no CGI, no text, no watermark"
)

PUJA_SCENE_SETS: dict[str, list[str]] = {
    "satyanarayan": [
        "Vedic priest in white dhoti reciting Satyanarayan Katha before Lord Vishnu deity, banana leaf prasad, brass kalash, marigold garlands",
        "Detailed Satyanarayan altar close-up: panchamrit bowls, tulsi garland, sacred katha book, incense smoke, fresh flowers",
        "Indian family in traditional dress seated on floor receiving prasad during Satyanarayan Puja in home mandir",
    ],
    "ganesh": [
        "Hindu priest performing abhishek on Ganesha murti with modak offerings, red hibiscus garlands, chanting mantras",
        "Close-up Ganesha idol with sandalwood paste, durva grass, brass diya flames, coconut kalash",
        "Multi-generation family doing aarti before Ganesha altar during home Ganesh Puja",
    ],
    "lakshmi": [
        "Priest conducting Lakshmi Puja with silver coins, lotus flowers, oil lamps before Goddess Lakshmi idol",
        "Macro Lakshmi altar: vermillion, rice grains, ornate thali, marigolds, glowing diyas",
        "Family in silk attire lighting diyas during Lakshmi worship with rangoli at doorstep",
    ],
    "durga": [
        "Priest offering dhup and sindoor before ornate Durga murti with traditional decorations",
        "Close-up Durga idol with weapons, red saree, jasmine garlands, dhunuchi incense",
        "Devotees in traditional attire near Durga puja altar during home ceremony",
    ],
    "navratri": [
        "Navratri puja with nine lit diyas, colorful chunari over Devi murti, kalash with coconut",
        "Vibrant Navratri altar with fresh flowers, brass bells, festival textiles, garba elements",
        "Women in chaniya choli performing aarti during home Navratri celebration",
    ],
    "diwali": [
        "Diwali Lakshmi-Ganesh puja: priest guiding family before dual deity idols, hundreds of clay diyas, intricate rangoli",
        "Close-up Diwali altar: Lakshmi-Ganesh idols, gold coins, kaju katli sweets, marigold garlands, glowing lamps",
        "Indian family in festive attire doing Diwali aarti at home, warm diya light, celebratory atmosphere",
    ],
    "kali": [
        "Priest offering red hibiscus before Kali murti during night Kali Puja, dozens of oil lamps",
        "Close-up Kali deity with lemon garland, red cloth, sindoor, dramatic crimson altar lighting",
        "Devotees performing Kali Puja aarti with dhunuchi incense smoke",
    ],
    "hanuman": [
        "Priest applying sindoor to Hanuman murti with banana and laddu offerings, brass bell",
        "Close-up Hanuman idol with orange marigold garlands, sacred thread, camphor aarti flame",
        "Devotees chanting before Hanuman altar during Tuesday puja",
    ],
    "rudrabhishek": [
        "Priest pouring milk and honey abhishek over Shiva Lingam with bilva leaves, brass vessels",
        "Close-up Shiva Lingam with panchamrit streams, white flowers, bilva patra, incense",
        "Devotees seated during Rudrabhishek with conch shell and Vedic altar",
    ],
}

DEFAULT_SCENE_SET = [
    "Hindu priest chanting mantras during {puja} with brass bells, camphor aarti, traditional altar",
    "Macro photograph of {puja} altar with kalash, coconut, fruits, incense, deity image, marigolds",
    "Multi-generation Indian family gathered for {puja} sharing prasad in warmly lit home mandir",
]


def build_distinct_image_specs(
    puja: str,
    city: str,
    state: str,
    country: str,
    slug: str,
    image_prompts: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    scene_set = _puja_scene_set(puja)
    specs: list[dict[str, str]] = []

    for index in range(IMAGE_COUNT):
        scene_key, scene_label = SCENE_TYPES[index]
        raw = image_prompts[index] if image_prompts and index < len(image_prompts) else {}
        scene_detail = scene_set[index]
        caption = str(
            raw.get("caption")
            or f"{scene_label} — {puja} in {city}, {state}"
        )
        alt = str(
            raw.get("alt")
            or f"{puja} {scene_label.lower()} in {city}, {state}"
        )
        specs.append(
            {
                "filename": f"{_slug_file_base(slug)}-{index + 1}.jpg",
                "prompt": _build_photography_prompt(puja, city, state, country, scene_detail, index),
                "alt": alt,
                "caption": caption,
            }
        )

    return specs


def _build_photography_prompt(
    puja: str,
    city: str,
    state: str,
    country: str,
    scene_detail: str,
    index: int,
) -> str:
    compositions = (
        f"Wide establishing shot of {scene_detail}, set in a real home or venue in {city}, {state}, {country}",
        f"Intimate close-up detail shot of {scene_detail}, {puja} ceremony in {city}, {state}",
        f"Candid medium shot of {scene_detail}, {puja} gathering in {city}, {state}, {country}",
    )
    return f"{compositions[index]}. {IMAGE_QUALITY_SUFFIX}."


def _slug_file_base(slug: str) -> str:
    base = slug.strip().lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9._-]", "", base) or "puja-page"


def _puja_scene_set(puja: str) -> list[str]:
    normalized = puja.lower()
    for key, scenes in PUJA_SCENE_SETS.items():
        if key in normalized:
            return scenes
    return [scene.format(puja=puja) for scene in DEFAULT_SCENE_SET]
