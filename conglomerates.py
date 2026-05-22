"""
Owner → business-sector lookup for the Ownership lens (O).

For each outlet we list the *sectors of interest* held by the parent group.
When an article covers one of those sectors, the engine flags a potential
conflict of interest; the magnitude of the flag is amplified if the lexical
framing is pro-establishment (Lens 3).

Sources of the sector lists below: publicly reported group-company structures
of Adani, Reliance, Bennett-Coleman, etc. Update as ownership shifts.
"""
from __future__ import annotations

CONGLOMERATE_INTERESTS: dict[str, dict] = {
    "ndtv": {
        "parent": "Adani Group / AMG Media",
        "sectors": [
            "energy", "coal", "ports", "airports", "renewables",
            "infrastructure", "cement", "logistics", "transmission",
            "data centre", "data centres", "Adani",
        ],
        # Story shapes that would be sensitive given the owner's portfolio.
        "conflict_topics": [
            "Hindenburg", "SEBI probe", "Adani investigation",
            "promoter pledge", "round-tripping",
        ],
    },
    "thehindu": {
        "parent": "Kasturi & Sons Ltd.",
        # Diversified family but not a conglomerate with major industrial bets.
        "sectors": ["publishing", "media"],
        "conflict_topics": [],
    },
    "republic": {
        "parent": "ARG Outlier Media",
        "sectors": ["broadcast"],
        # Funded historically by Asianet News / Rajeev Chandrasekhar; founder is
        # also a serving Union Minister — sensitive when reporting on the BJP /
        # central government.
        "conflict_topics": [
            "Rajeev Chandrasekhar", "BJP", "Union Minister",
        ],
    },
    "toi": {
        "parent": "Bennett, Coleman & Co. (Times Group)",
        "sectors": [
            "real estate", "education", "events", "radio", "OOH",
            "private treaties",
        ],
        # Times Group has been criticised for 'paid news' / Private Treaties
        # arrangements with listed companies it covers.
        "conflict_topics": [
            "Private Treaties", "paid news",
        ],
    },
    "indianexpress": {
        "parent": "The Indian Express Group (Goenka family)",
        "sectors": ["publishing", "media"],
        "conflict_topics": [],
    },
}


def sectors_for(publisher_id: str) -> list[str]:
    return CONGLOMERATE_INTERESTS.get(publisher_id, {}).get("sectors", [])


def conflict_topics_for(publisher_id: str) -> list[str]:
    return CONGLOMERATE_INTERESTS.get(publisher_id, {}).get("conflict_topics", [])


def parent_for(publisher_id: str) -> str:
    return CONGLOMERATE_INTERESTS.get(publisher_id, {}).get("parent", "")
