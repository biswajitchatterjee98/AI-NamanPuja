PUJA_RITUALS: dict[str, list[str]] = {
    "satyanarayan": [
        "Ganesh Puja (auspicious beginning)",
        "Sankalp (sacred intention)",
        "Kalash Sthapana (sacred pot installation)",
        "Satyanarayan Puja & Katha recitation",
        "Panchamrit Abhishek",
        "Aarti & camphor offering",
        "Prasad distribution & blessings",
    ],
    "diwali": [
        "Ganesh-Lakshmi invocation",
        "Kalash & diya lighting",
        "Lakshmi-Ganesh worship & mantras",
        "Coin & prosperity offerings",
        "Aarti with ghee lamps",
        "Rangoli & home blessing",
        "Prasad & family blessings",
    ],
    "ganesh": [
        "Avahan (invoking Lord Ganesha)",
        "Pranpratishtha",
        "Shodashopachar Puja",
        "Modak & flower offerings",
        "Aarti & mantra chanting",
        "Visarjan preparation (if applicable)",
    ],
    "lakshmi": [
        "Ganesh Puja before Lakshmi worship",
        "Kalash Sthapana",
        "Lakshmi idol invocation",
        "Coin, lotus & diya offerings",
        "Lakshmi Aarti",
        "Prasad distribution",
    ],
    "navratri": [
        "Ghatasthapana / Kalash Sthapana",
        "Daily Devi invocation",
        "Kumkum & chunari offerings",
        "Aarti with nine diyas",
        "Fasting & prasad blessings",
    ],
    "durga": [
        "Bodhon & Kalash Sthapana",
        "Pushpanjali & dhup offering",
        "Durga mantra & stotra",
        "Sindoor khela (if applicable)",
        "Aarti & dhunuchi",
        "Bhog & prasad",
    ],
    "kali": [
        "Kali invocation & tantric offerings",
        "Red hibiscus & sweet offerings",
        "Maha aarti with oil lamps",
        "Prasad & community blessings",
    ],
}


def get_puja_rituals(puja: str) -> list[str]:
    normalized = puja.lower()
    for key, rituals in PUJA_RITUALS.items():
        if key in normalized:
            return rituals
    return [
        "Ganesh Puja (auspicious start)",
        "Sankalp",
        "Kalash Sthapana",
        f"Main {puja} worship",
        "Aarti",
        "Prasad distribution",
    ]
