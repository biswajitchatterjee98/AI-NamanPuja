def get_location_angle(country: str, state: str, city: str) -> str:
    country_key = country.strip().lower()
    state_key = state.strip().lower()
    city_key = city.strip().lower()

    if country_key in {"usa", "us", "united states", "america"}:
        return (
            f"Write for the Hindu diaspora in {city}, {state}, USA. Mention home puja, pandit/priest booking, "
            f"suburbs and neighborhoods families actually live in, samagri preparation, Griha Pravesh, birthdays, "
            f"and multi-generational gatherings. Use terms like 'Hindu priest', 'Vedic ceremony', and 'book puja'."
        )

    if country_key in {"uk", "united kingdom", "england", "scotland", "wales"}:
        return (
            f"Write for Indian and Hindu families in {city}, {state}, UK. Mention home mandir setups, "
            f"priest visits, festival gatherings, and the local South Asian community."
        )

    if country_key in {"canada", "australia", "new zealand"}:
        return (
            f"Write for diaspora families in {city}, {state}, {country}. Mention home ceremonies, "
            f"priest booking, multicultural neighborhoods, and festival celebrations."
        )

    if "indonesia" in country_key or state_key in {"bali", "gianyar", "denpasar", "badung"} or "bali" in city_key:
        return (
            f"Write for {city}, {state}, Indonesia. Mention villa ceremonies, spiritual retreats, island living, "
            f"Balinese-Hindu cultural context, tourists and expat families, and temple-inspired devotion."
        )

    if country_key in {"india", "bharat"}:
        return (
            f"Write for families in {city}, {state}, India. Mention local temples, festival seasons, "
            f"community halls, apartment puja setups, and regional cultural identity."
        )

    return (
        f"Write specifically for {city}, {state}, {country}. Reference real neighborhoods, "
        f"who books this puja locally, and how Naman Puja serves that community."
    )
