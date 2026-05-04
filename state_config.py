STATE_CONFIG = {
    "S03": {
        "state_name": "Assam",
        "state_slug": "assam",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S03.htm",
        "candidate_status": "pending_discovery",
    },
    "S11": {
        "state_name": "Kerala",
        "state_slug": "kerala",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S11.htm",
        "candidate_status": "pending_discovery",
    },
    "S22": {
        "state_name": "Tamil Nadu",
        "state_slug": "tamil_nadu",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S22.htm",
        "candidate_status": "available",
    },
    "S25": {
        "state_name": "West Bengal",
        "state_slug": "west_bengal",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S25.htm",
        "candidate_status": "pending_discovery",
    },
    "U07": {
        "state_name": "Puducherry",
        "state_slug": "puducherry",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-U07.htm",
        "candidate_status": "pending_discovery",
    },
}


def get_state_name(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("state_name", "Unknown")


def get_state_slug(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("state_slug", "unknown")


def get_all_configured_states():
    rows = []

    for state_code, state_info in STATE_CONFIG.items():
        rows.append(
            {
                "state_code": state_code,
                "state_name": state_info["state_name"],
                "state_slug": state_info["state_slug"],
                "party_url": state_info["party_url"],
                "configured_candidate_status": state_info["candidate_status"],
            }
        )

    return rows