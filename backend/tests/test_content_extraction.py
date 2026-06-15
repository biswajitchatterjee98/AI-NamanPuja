from app.services.content_html import extract_content_from_llm_response, is_valid_html_content


def test_extract_part_a_when_content_is_nested_dict():
    data = {
        "slug": "diwali-puja-in-los-angeles-california",
        "content": {
            "section1": {
                "title": "Diwali Puja in Los Angeles",
                "description": "Families across Los Angeles celebrate Diwali with home puja.",
            }
        },
    }
    html = extract_content_from_llm_response(data, part="a")
    assert "<h2>" in html
    assert is_valid_html_content(html, min_h2=1)
