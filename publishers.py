"""
Static publisher metadata: ownership, perceived leaning, and a numeric Bias Factor.

Bias Factor scale (-1.0 .. +1.0):
  -1.0  strongly left / anti-establishment
   0.0  centrist / neutral
  +1.0  strongly right / pro-establishment

These values are *perceived* historical leanings drawn from public reporting and
academic press-freedom indices; they are intentionally conservative and should be
read as priors, not verdicts. Users see the methodology via the UI button.
"""

PUBLISHERS = {
    "ndtv": {
        "id": "ndtv",
        "name": "NDTV",
        "owner": "Adani Group / AMG Media Networks",
        "ownership_type": "Corporate conglomerate",
        "influence": "Corporate-heavy. Perceived shift toward pro-establishment "
                     "leaning since the 2023 Adani acquisition.",
        "bias_factor": 0.30,
        "color_accent": "#E11D48",  # rose-600
        "logo_initials": "NDTV",
    },
    "thehindu": {
        "id": "thehindu",
        "name": "The Hindu",
        "owner": "Kasturi & Sons Ltd.",
        "ownership_type": "Independent / family-owned",
        "influence": "Liberal / centre-left historical record. Strong editorial "
                     "independence and long-form policy coverage.",
        "bias_factor": -0.40,
        "color_accent": "#1D4ED8",  # blue-700
        "logo_initials": "TH",
    },
    "republic": {
        "id": "republic",
        "name": "Republic TV",
        "owner": "ARG Outlier Media (Arnab Goswami)",
        "ownership_type": "Founder-promoter owned",
        "influence": "Strongly nationalist editorial line. Perceived pro-government "
                     "/ pro-BJP framing.",
        "bias_factor": 0.70,
        "color_accent": "#B91C1C",  # red-700
        "logo_initials": "RTV",
    },
    "toi": {
        "id": "toi",
        "name": "Times of India",
        "owner": "Bennett, Coleman & Co. (The Times Group)",
        "ownership_type": "Private conglomerate",
        "influence": "Centrist / pro-business. Largest English daily by circulation.",
        "bias_factor": 0.10,
        "color_accent": "#0F766E",  # teal-700
        "logo_initials": "TOI",
    },
    "indianexpress": {
        "id": "indianexpress",
        "name": "The Indian Express",
        "owner": "The Indian Express Group (Goenka family)",
        "ownership_type": "Independent legacy",
        "influence": "Centrist with a strong investigative tradition. Known for "
                     "accountability reporting across governments.",
        "bias_factor": 0.00,
        "color_accent": "#475569",  # slate-600
        "logo_initials": "IE",
    },
}


def get_publisher(pub_id: str) -> dict:
    return PUBLISHERS[pub_id]


def all_publishers() -> list[dict]:
    return list(PUBLISHERS.values())
