STATE_CONFIG = {
    "S03": {
        "state_name": "Assam",
        "state_slug": "assam",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S03.htm",
        "candidate_status": "pending_discovery",
        "expected_ac_count": 126,
        "geojson_path": "data/geojson/assam_ac.geojson",
        "map_center": [26.2006, 92.9376],
        "map_zoom": 7,
    },
    "S11": {
        "state_name": "Kerala",
        "state_slug": "kerala",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S11.htm",
        "candidate_status": "pending_discovery",
        "expected_ac_count": 140,
        "geojson_path": "data/geojson/kerala_ac.geojson",
        "map_center": [10.8505, 76.2711],
        "map_zoom": 7,
    },
    "S22": {
        "state_name": "Tamil Nadu",
        "state_slug": "tamil_nadu",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S22.htm",
        "candidate_status": "available",
        "expected_ac_count": 234,
        "geojson_path": "data/geojson/tamil_nadu_ac.geojson",
        "map_center": [11.1271, 78.6569],
        "map_zoom": 7,
    },
    "S25": {
        "state_name": "West Bengal",
        "state_slug": "west_bengal",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S25.htm",
        "candidate_status": "pending_discovery",
        "expected_ac_count": 294,
        "geojson_path": "data/geojson/west_bengal_ac.geojson",
        "map_center": [22.9868, 87.8550],
        "map_zoom": 7,
    },
    "U07": {
        "state_name": "Puducherry",
        "state_slug": "puducherry",
        "party_url": "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-U07.htm",
        "candidate_status": "pending_discovery",
        "expected_ac_count": 30,
        "geojson_path": "data/geojson/puducherry_ac.geojson",
        "map_center": [11.9416, 79.8083],
        "map_zoom": 10,
    },
}


def get_state_name(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("state_name", "Unknown")


def get_state_slug(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("state_slug", "unknown")


def get_party_url(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("party_url", "")


def get_candidate_status(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("candidate_status", "unknown")


def get_expected_ac_count(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("expected_ac_count", 0)


def get_geojson_path(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("geojson_path", "")


def get_map_center(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("map_center", [22.9734, 78.6569])


def get_map_zoom(state_code):
    state_info = STATE_CONFIG.get(state_code, {})
    return state_info.get("map_zoom", 6)


def get_state_code_from_name(state_name):
    for state_code, state_info in STATE_CONFIG.items():
        if state_info.get("state_name") == state_name:
            return state_code
    return None


def get_state_name_to_code_map():
    return {
        state_info["state_name"]: state_code
        for state_code, state_info in STATE_CONFIG.items()
    }


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
                "expected_ac_count": state_info["expected_ac_count"],
                "geojson_path": state_info["geojson_path"],
                "map_center": state_info["map_center"],
                "map_zoom": state_info["map_zoom"],
            }
        )

    return rows


def get_all_state_names():
    return [
        state_info["state_name"]
        for state_info in STATE_CONFIG.values()
    ]


def get_all_state_codes():
    return list(STATE_CONFIG.keys())