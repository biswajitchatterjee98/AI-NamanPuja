from datetime import datetime, timezone

from app.schemas import FaqItem, PageDocument, SeoMetadata
from app.services.document_export import build_page_docx, build_page_export, build_page_pdf


def _sample_page() -> PageDocument:
    return PageDocument(
        batch_id="batch-1",
        puja="Satyanarayan Puja",
        city="Austin",
        state="Texas",
        country="USA",
        slug="satyanarayan-puja-in-austin-texas",
        content=(
            "<h1>Satyanarayan Puja in Austin, Texas</h1>"
            "<p class='lead'>Lead paragraph about Austin diaspora families.</p>"
            "<h2>Why Austin families choose Satyanarayan Puja</h2>"
            "<p>Location-specific content for Round Rock and Cedar Park.</p>"
        ),
        faq=[
            FaqItem(
                question="Can Satyanarayan Puja be performed at home in Austin?",
                answer="Yes. Naman Puja provides home ceremonies across Travis County.",
            )
        ],
        seo=SeoMetadata(
            title="Satyanarayan Puja in Austin, Texas | NamanPuja",
            description="Book Satyanarayan Puja in Austin with experienced Vedic priests.",
            keywords=["Satyanarayan Puja", "Austin", "Texas", "Hindu priest"],
            focus_keyword="Satyanarayan Puja in Austin",
            tagline="Authentic puja services in Austin",
            breadcrumb="Home > USA > Texas > Austin > Satyanarayan Puja",
        ),
        generated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )


def test_build_page_docx():
    data = build_page_docx(_sample_page())
    assert data[:2] == b"PK"


def test_build_page_pdf():
    data = build_page_pdf(_sample_page())
    assert data.startswith(b"%PDF")


def test_build_page_export_formats():
    docx_data, docx_name, docx_type = build_page_export(_sample_page(), "docx")
    pdf_data, pdf_name, pdf_type = build_page_export(_sample_page(), "pdf")
    assert docx_name.endswith(".docx")
    assert pdf_name.endswith(".pdf")
    assert "wordprocessingml" in docx_type
    assert pdf_type == "application/pdf"
    assert len(docx_data) > 100
    assert len(pdf_data) > 100
