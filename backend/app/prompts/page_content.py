from app.prompts.location_context import get_location_angle
from app.prompts.puja_rituals import get_puja_rituals

HTML_RULES = """
OUTPUT FORMAT (mandatory):
- Return JSON only. The "content" value is ONE HTML string.
- Use ONLY: h1, h2, h3, p, ul, ol, li, strong, em.
- NEVER return nested JSON (no section8, rituals arrays, or Python dicts).
- Every section: <h2> heading → 2-3 <p> paragraphs and/or <ul><li> bullet lists.
- Rituals & benefits: <h3> sub-heading per item + <p> (2-3 sentences each).
- Use <p class="lead"> for the opening hook paragraph under h1.
- Minimum 3,500 words total across parts A+B. No duplicate paragraphs.
- Write ONLY about the requested puja — never list unrelated pujas as rituals.
"""

CONTENT_PART_A_SYSTEM = f"""You are an expert NamanPuja.com SEO landing page writer.
Model your output on professional 10-12 page puja location briefs (PDF-style).

{HTML_RULES}

PART A — HTML sections 1-7:

1. <h1>[Puja] in [City], [State] – [emotional subtitle]</h1>
   <p class="lead">…</p> + <p> (location hook, who books, Naman Puja intro)

2. <h2>[City nickname] – [local identity headline]</h2>
   2-3 <p> + <ul> with 6-8 location-specific traits

3. <h2>Why [Puja] holds timeless significance</h2>
   2-3 <p> on devotion meaning + <ul> of 5-6 spiritual themes

4. <h2>A perfect [Puja] for [local audience] in [City]</h2>
   <p> + <ul> of 8-10 occasions (localized to the city)

5. <h2>Inspired by [real local landmark or cultural anchor]</h2>
   3-4 <p> tying landmark/tradition to the puja experience

6. <h2>A celebration of gratitude, heritage, and blessings</h2>
   2 <p> + <ul> of 6 devotional intentions

7. <h2>Why families in [City] trust Naman Puja</h2>
   <p> + <ul> of 6 service strengths (priests, home puja, authentic rituals, etc.)
"""


CONTENT_PART_B_SYSTEM = f"""You are an expert NamanPuja.com SEO landing page writer.
Continue the SAME page from Part A. Match tone and facts.

{HTML_RULES}

PART B — HTML sections 8-14 (use these exact h2 patterns):

8. <h2>Traditional rituals included in [Puja Name]</h2>
   For EACH ritual: <h3>Ritual name</h3> + <p> (2-3 sentences, localized to city)

9. <h2>Spiritual benefits of [Puja Name]</h2>
   Six benefits: each <h3>Benefit</h3> + <p>

10. <h2>Why [City] is ideal for Hindu ceremonies</h2>
    2 <p> + <ul> of 6 unique local factors

11. <h2>Areas we serve across [City] and [State]</h2>
    <p> intro + <ul> listing 10-14 real neighborhoods/suburbs

12. <h2>Celebrate faith in [City]</h2>
    2-3 <p> (unique, inspirational, location-specific)

13. <h2>Create sacred memories in [City]</h2>
    2-3 <p> (distinct phrasing from section 12)

14. <h2>Book [Puja Name] in [City], [State] today</h2>
    <p> CTA + <ul> of 6 services + closing paragraph mentioning Naman Puja contact
"""


CONTENT_META_SYSTEM = """Return ONLY valid JSON with:
faq (exactly 10 location-specific {question, answer} pairs, 2-4 sentences each),
seo (title, description max 155 chars, keywords 12-18, focus_keyword, tagline, breadcrumb),
areas_served (10-14 real neighborhoods),
occasions (8-10),
local_landmarks (3-5 real places)."""


PART_B_RETRY_SYSTEM = """Return ONLY valid JSON: {"content": "<html string>"}.
Convert the malformed draft into proper HTML with h2, h3, p, ul, li.
Use the PDF-style structure for sections 8-14. Keep location facts. Remove unrelated puja names."""


def build_content_user_prompt(
    puja: str,
    city: str,
    state: str,
    country: str,
    slug: str,
    feedback_context: str = "",
) -> str:
    feedback = f"\nReviewer feedback:\n{feedback_context}\n" if feedback_context else ""
    rituals = get_puja_rituals(puja)
    ritual_list = "\n".join(f"  - {name}" for name in rituals)
    location_angle = get_location_angle(country, state, city)

    return (
        f"INPUT\n"
        f"Puja: {puja}\n"
        f"City: {city}\n"
        f"State/Region: {state}\n"
        f"Country: {country}\n"
        f"Slug: {slug}\n\n"
        f"LOCATION ANGLE\n{location_angle}\n\n"
        f"PUJA-SPECIFIC RITUALS (use these in section 8, expand each as h3+p)\n{ritual_list}\n\n"
        f"Write unique, publication-ready HTML for {puja} in {city} only — not a template swap.\n"
        f"{feedback}"
    )


def build_part_b_user_prompt(
    puja: str,
    city: str,
    state: str,
    country: str,
    part_a_tail: str,
    feedback_context: str = "",
) -> str:
    feedback = f"\nReviewer feedback:\n{feedback_context}\n" if feedback_context else ""
    rituals = get_puja_rituals(puja)
    ritual_list = "\n".join(f"  - {name}" for name in rituals)

    return (
        f"Puja: {puja}\nCity: {city}\nState: {state}\nCountry: {country}\n\n"
        f"Continue seamlessly from Part A. Output HTML in the content field only.\n"
        f"Section 8 rituals MUST be these (each as h3 + p):\n{ritual_list}\n\n"
        f"Part A ending:\n...{part_a_tail[-600:]}\n{feedback}"
    )


def build_part_b_retry_prompt(puja: str, city: str, state: str, malformed: str) -> str:
    return (
        f"Puja: {puja}\nCity: {city}\nState: {state}\n\n"
        f"Malformed draft to convert to HTML:\n{malformed[:8000]}"
    )
