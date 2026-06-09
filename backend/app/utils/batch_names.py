from app.schemas import PageInput


def format_batch_name(page_inputs: list[PageInput]) -> str:
    if not page_inputs:
        return "Unnamed batch"

    first = page_inputs[0]
    location = f"{first.city}, {first.state}" if first.state else first.city
    label = f"{first.puja} · {location}"
    extra_pages = len(page_inputs) - 1
    if extra_pages > 0:
        return f"{label} + {extra_pages} more"
    return label
