from app.sanitize import sanitize_html


def test_strips_script_tags():
    dirty = '<p>Hello</p><script>alert("xss")</script>'
    clean = sanitize_html(dirty)
    assert "<script>" not in clean
    assert "Hello" in clean
