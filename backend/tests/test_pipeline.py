from app.graph.pipeline import run_pipeline
from app.services.llm import slugify


def test_slugify():
    assert slugify("Satyanarayan Puja", "in", "Los Angeles") == "satyanarayan-puja-in-los-angeles"


def test_pipeline_mock_generation():
    result = run_pipeline(
        "test-batch",
        [
            {
                "puja": "Ganesh Puja",
                "city": "New York",
                "state": "NY",
                "country": "USA",
            }
        ],
    )
    assert result["status"] == "qc_complete"
    assert len(result["pages"]) == 1
    page = result["pages"][0]
    assert page.slug
    assert page.content
    assert page.seo is not None
    assert page.qc is not None
