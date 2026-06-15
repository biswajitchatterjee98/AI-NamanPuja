from app.services.content_html import (
    extract_content_from_llm_response,
    is_valid_html_content,
    structured_sections_to_html,
)


def test_structured_sections_to_html():
    html = structured_sections_to_html(
        {
            "section8": {
                "title": "Traditional Rituals",
                "rituals": [
                    {"title": "Diya Lighting", "description": "Families light clay lamps across Los Angeles."},
                ],
            },
            "section14": {"title": "Book Today", "cta": "Contact Naman Puja to schedule your Diwali Puja."},
        }
    )
    assert "<h2>Traditional Rituals</h2>" in html
    assert "<h3>Diya Lighting</h3>" in html
    assert "<h2>Book Today</h2>" in html
    assert "section8" not in html


def test_extract_content_from_malformed_part_b():
    data = {
        "section8": {
            "title": "Traditional Rituals",
            "rituals": [{"title": "Lakshmi-Ganesh Puja", "description": "Central Diwali worship in Los Angeles."}],
        }
    }
    html = extract_content_from_llm_response(data, part="b")
    assert "<h2>Traditional Rituals</h2>" in html
    assert is_valid_html_content(html, min_h2=1)


def test_rejects_json_artifact_string():
    bad = "{'section8': {'title': 'Traditional Rituals'}}"
    assert not is_valid_html_content(bad)
