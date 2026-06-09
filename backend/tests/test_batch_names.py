from app.schemas import PageInput
from app.utils.batch_names import format_batch_name


def test_format_batch_name_single_page():
    pages = [PageInput(puja="Satyanarayan Puja", city="Los Angeles", state="California", country="USA")]
    assert format_batch_name(pages) == "Satyanarayan Puja · Los Angeles, California"


def test_format_batch_name_multiple_pages():
    pages = [
        PageInput(puja="Satyanarayan Puja", city="Los Angeles", state="California", country="USA"),
        PageInput(puja="Ganesh Puja", city="New York", state="New York", country="USA"),
    ]
    assert format_batch_name(pages) == "Satyanarayan Puja · Los Angeles, California + 1 more"
