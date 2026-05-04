import copy
import json
import os
import re
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from azure_data_loader import load_candidate_results, load_party_results


st.set_page_config(
    page_title="Constituency Map",
    page_icon="🗺️",
    layout="wide",
)


CANDIDATE_FILE = "data/processed/latest_candidate_results.csv"
PARTY_FILE = "data/processed/latest_results.csv"
GEOJSON_DIR = "data/geojson"
TAMIL_NADU_GEOJSON = os.path.join(GEOJSON_DIR, "tamil_nadu_ac.geojson")


PARTY_COLORS = {
    "DMK": "#f97316",
    "AIADMK": "#22c55e",
    "ADMK": "#22c55e",
    "BJP": "#fb923c",
    "INC": "#2563eb",
    "TVK": "#dc2626",
    "NTK": "#8b5cf6",
    "VCK": "#7c3aed",
    "CPI": "#ef4444",
    "CPI(M)": "#b91c1c",
    "PMK": "#06b6d4",
    "DMDK": "#eab308",
    "IND": "#94a3b8",
    "NOTA": "#64748b",
    "OTHERS": "#a3a3a3",
}


DEFAULT_COLOR = "#94a3b8"
NO_DATA_COLOR = "#1f2937"


def inject_css():
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top left, #07111f 0%, #020617 42%, #0b111d 100%);
            color: #ffffff;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        }

        .hero-card {
            padding: 32px;
            border-radius: 28px;
            background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 60%, #111827 100%);
            border: 1px solid rgba(147, 197, 253, 0.25);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
            margin-bottom: 24px;
        }

        .hero-title {
            font-size: 42px;
            font-weight: 900;
            color: white;
            margin-bottom: 12px;
            letter-spacing: -1.2px;
        }

        .hero-subtitle {
            font-size: 18px;
            color: #dbeafe;
            line-height: 1.65;
            max-width: 1180px;
        }

        .metric-card {
            padding: 22px;
            border-radius: 22px;
            background: rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(148, 163, 184, 0.18);
            min-height: 128px;
        }

        .metric-label {
            font-size: 14px;
            font-weight: 800;
            color: #93c5fd;
            margin-bottom: 12px;
        }

        .metric-value {
            font-size: 32px;
            font-weight: 900;
            color: white;
            line-height: 1.1;
        }

        .metric-help {
            font-size: 14px;
            color: #bfdbfe;
            margin-top: 10px;
        }

        .info-box {
            padding: 18px 22px;
            border-radius: 18px;
            background: rgba(30, 41, 59, 0.75);
            border: 1px solid rgba(59, 130, 246, 0.35);
            color: #dbeafe;
            font-size: 16px;
            line-height: 1.55;
            margin: 18px 0;
        }

        .warning-box {
            padding: 18px 22px;
            border-radius: 18px;
            background: rgba(120, 53, 15, 0.35);
            border: 1px solid rgba(234, 179, 8, 0.45);
            color: #fde68a;
            font-size: 16px;
            line-height: 1.55;
            margin: 18px 0;
        }

        .success-box {
            padding: 18px 22px;
            border-radius: 18px;
            background: rgba(6, 78, 59, 0.45);
            border: 1px solid rgba(16, 185, 129, 0.45);
            color: #bbf7d0;
            font-size: 16px;
            line-height: 1.55;
            margin: 18px 0;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
        }

        .section-title {
            font-size: 28px;
            font-weight: 900;
            margin-top: 28px;
            margin-bottom: 18px;
            color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_party(value):
    value = clean_text(value).upper()
    value = value.replace("A.I.A.D.M.K.", "AIADMK")
    value = value.replace("AIADMK", "AIADMK")
    return value


def clean_status(value):
    value = clean_text(value).lower()

    if value in ["won", "winner", "declared"]:
        return "Won"

    if value in ["leading", "lead"]:
        return "Leading"

    if value in ["trailing", "lost", "loss"]:
        return "Trailing"

    if value == "":
        return "Unknown"

    return value.title()


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        value = str(value).replace(",", "").strip()
        match = re.search(r"-?\d+", value)
        if not match:
            return default
        return int(match.group())
    except Exception:
        return default


@st.cache_data(show_spinner=False)
def load_candidate_data():
    df = load_candidate_results()

    if df.empty:
        return df

    required_columns = [
        "constituency",
        "constituency_no",
        "candidate",
        "party",
        "votes",
        "status",
        "margin",
    ]

    for col in required_columns:
        if col not in df.columns:
            if col in ["votes", "margin", "constituency_no"]:
                df[col] = 0
            else:
                df[col] = ""

    df["constituency"] = df["constituency"].apply(clean_text)
    df["candidate"] = df["candidate"].apply(clean_text)
    df["party"] = df["party"].apply(clean_party)
    df["status"] = df["status"].apply(clean_status)
    df["votes"] = df["votes"].apply(safe_int)
    df["margin"] = df["margin"].apply(safe_int)
    df["constituency_no"] = df["constituency_no"].apply(safe_int)

    if "state_code" not in df.columns:
        df["state_code"] = "S22"

    if "state_name" not in df.columns:
        df["state_name"] = "Tamil Nadu"

    return df


@st.cache_data(show_spinner=False)
def load_party_data():
    df = load_party_results()

    if df.empty:
        return df

    for col in ["state", "party", "won", "leading", "total"]:
        if col not in df.columns:
            if col in ["won", "leading", "total"]:
                df[col] = 0
            else:
                df[col] = ""

    df["state"] = df["state"].apply(clean_text)
    df["party"] = df["party"].apply(clean_party)
    df["won"] = df["won"].apply(safe_int)
    df["leading"] = df["leading"].apply(safe_int)
    df["total"] = df["total"].apply(safe_int)

    return df


@st.cache_data(show_spinner=False)
def load_geojson():
    if not os.path.exists(TAMIL_NADU_GEOJSON):
        return None, "GeoJSON file not found."

    if os.path.getsize(TAMIL_NADU_GEOJSON) == 0:
        return None, "GeoJSON file exists but is empty."

    try:
        with open(TAMIL_NADU_GEOJSON, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "features" not in data or not data["features"]:
            return None, "Invalid GeoJSON: no features found."

        return data, None

    except json.JSONDecodeError as error:
        return None, f"Invalid GeoJSON JSON format: {error}"

    except Exception as error:
        return None, f"Failed to load GeoJSON: {error}"


def prepare_constituency_summary(candidate_df):
    if candidate_df.empty:
        return pd.DataFrame()

    working = candidate_df.copy()

    for col in ["constituency", "constituency_no", "candidate", "party", "votes", "status", "margin"]:
        if col not in working.columns:
            if col in ["votes", "margin", "constituency_no"]:
                working[col] = 0
            else:
                working[col] = ""

    working["votes"] = working["votes"].apply(safe_int)
    working["margin"] = working["margin"].apply(safe_int)
    working["constituency_no"] = working["constituency_no"].apply(safe_int)
    working["status"] = working["status"].apply(clean_status)
    working["party"] = working["party"].apply(clean_party)

    working = working[working["constituency_no"] > 0].copy()

    if working.empty:
        return pd.DataFrame()

    working = working.sort_values(
        by=["constituency_no", "votes"],
        ascending=[True, False],
    )

    top_rows = working.groupby("constituency_no", as_index=False).first()

    candidate_counts = (
        working.groupby("constituency_no")
        .agg(
            total_candidates=("candidate", "count"),
            total_votes_recorded=("votes", "sum"),
        )
        .reset_index()
    )

    summary = top_rows.merge(candidate_counts, on="constituency_no", how="left")

    summary = summary.rename(
        columns={
            "candidate": "leading_candidate",
            "party": "leading_party",
            "votes": "leading_votes",
            "status": "leading_status",
            "margin": "leading_margin",
        }
    )

    summary["leading_party"] = summary["leading_party"].apply(clean_party)
    summary["leading_status"] = summary["leading_status"].apply(clean_status)

    final_columns = [
        "constituency_no",
        "constituency",
        "leading_candidate",
        "leading_party",
        "leading_votes",
        "leading_status",
        "leading_margin",
        "total_candidates",
        "total_votes_recorded",
    ]

    for col in final_columns:
        if col not in summary.columns:
            summary[col] = ""

    return summary[final_columns].copy()


def get_party_color(party):
    party = clean_party(party)

    if party in PARTY_COLORS:
        return PARTY_COLORS[party]

    for known_party, color in PARTY_COLORS.items():
        if known_party in party or party in known_party:
            return color

    if party:
        return DEFAULT_COLOR

    return NO_DATA_COLOR


def enrich_geojson_with_results(geojson_data, summary_df):
    enriched = copy.deepcopy(geojson_data)

    if summary_df.empty:
        return enriched, 0

    summary_lookup = {
        int(row["constituency_no"]): row.to_dict()
        for _, row in summary_df.iterrows()
        if safe_int(row.get("constituency_no")) > 0
    }

    matched = 0

    for feature in enriched.get("features", []):
        properties = feature.get("properties", {})

        ac_no = safe_int(properties.get("AC_NO"))

        result = summary_lookup.get(ac_no)

        if result:
            matched += 1

            properties["dashboard_match"] = "Matched"
            properties["dashboard_constituency"] = result.get("constituency", "")
            properties["leading_candidate"] = result.get("leading_candidate", "")
            properties["leading_party"] = result.get("leading_party", "")
            properties["leading_votes"] = safe_int(result.get("leading_votes"))
            properties["leading_status"] = result.get("leading_status", "")
            properties["leading_margin"] = safe_int(result.get("leading_margin"))
            properties["total_candidates"] = safe_int(result.get("total_candidates"))
            properties["total_votes_recorded"] = safe_int(result.get("total_votes_recorded"))
            properties["fill_color"] = get_party_color(result.get("leading_party", ""))
        else:
            properties["dashboard_match"] = "Not matched"
            properties["dashboard_constituency"] = ""
            properties["leading_candidate"] = "No candidate data available"
            properties["leading_party"] = "No Data"
            properties["leading_votes"] = 0
            properties["leading_status"] = "No Data"
            properties["leading_margin"] = 0
            properties["total_candidates"] = 0
            properties["total_votes_recorded"] = 0
            properties["fill_color"] = NO_DATA_COLOR

    return enriched, matched


def build_map(enriched_geojson):
    m = folium.Map(
        location=[10.9, 78.7],
        zoom_start=7,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    def style_function(feature):
        properties = feature.get("properties", {})
        return {
            "fillColor": properties.get("fill_color", NO_DATA_COLOR),
            "color": "#ffffff",
            "weight": 0.6,
            "fillOpacity": 0.78,
        }

    def highlight_function(feature):
        return {
            "fillColor": "#facc15",
            "color": "#ffffff",
            "weight": 2.2,
            "fillOpacity": 0.92,
        }

    folium.GeoJson(
        enriched_geojson,
        name="Tamil Nadu Assembly Constituencies",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "AC_NO",
                "AC_NAME",
                "DIST_NAME",
                "leading_party",
                "leading_candidate",
                "leading_votes",
                "leading_status",
                "total_candidates",
            ],
            aliases=[
                "AC No:",
                "Map Constituency:",
                "District:",
                "Leading Party:",
                "Leading Candidate:",
                "Votes:",
                "Status:",
                "Candidates:",
            ],
            localize=True,
            sticky=True,
            labels=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=[
                "AC_NO",
                "AC_NAME",
                "DIST_NAME",
                "leading_party",
                "leading_candidate",
                "leading_votes",
                "leading_status",
                "leading_margin",
                "total_candidates",
                "total_votes_recorded",
            ],
            aliases=[
                "AC No:",
                "Constituency:",
                "District:",
                "Leading Party:",
                "Leading Candidate:",
                "Votes:",
                "Status:",
                "Margin:",
                "Total Candidates:",
                "Total Votes Recorded:",
            ],
            localize=True,
            labels=True,
            max_width=420,
        ),
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    return m


def render_metric(label, value, help_text=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_party_legend(summary_df):
    if summary_df.empty:
        return

    party_counts = (
        summary_df.groupby("leading_party")
        .agg(constituencies=("constituency_no", "count"))
        .reset_index()
        .sort_values("constituencies", ascending=False)
    )

    st.markdown('<div class="section-title">Party Colour Legend</div>', unsafe_allow_html=True)

    legend_cols = st.columns(4)

    for idx, row in party_counts.iterrows():
        party = row["leading_party"]
        count = row["constituencies"]
        color = get_party_color(party)

        with legend_cols[idx % 4]:
            st.markdown(
                f"""
                <div style="
                    padding: 12px 14px;
                    border-radius: 14px;
                    background: rgba(15, 23, 42, 0.9);
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    margin-bottom: 10px;
                ">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <div style="width:16px; height:16px; border-radius:4px; background:{color};"></div>
                        <div style="font-weight:800; color:white;">{party}</div>
                    </div>
                    <div style="color:#bfdbfe; font-size:13px; margin-top:4px;">{count} constituencies</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_constituency_detail(candidate_df, selected_constituency_no):
    filtered = candidate_df[
        candidate_df["constituency_no"].apply(safe_int) == safe_int(selected_constituency_no)
    ].copy()

    if filtered.empty:
        st.warning("No candidate rows found for the selected constituency.")
        return

    filtered["votes"] = filtered["votes"].apply(safe_int)
    filtered = filtered.sort_values("votes", ascending=False)

    constituency_name = filtered["constituency"].iloc[0]
    district_name = "Not available"

    st.markdown(
        f"""
        <div class="info-box">
            <b>Selected Constituency:</b> {constituency_name}<br>
            <b>AC Number:</b> {selected_constituency_no}<br>
            <b>District:</b> {district_name}
        </div>
        """,
        unsafe_allow_html=True,
    )

    top = filtered.iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_metric("Leading Candidate", clean_text(top["candidate"]), "Highest vote row in current feed")

    with c2:
        render_metric("Leading Party", clean_party(top["party"]), "Party from candidate dataset")

    with c3:
        render_metric("Votes", f"{safe_int(top['votes']):,}", "Current candidate vote count")

    with c4:
        render_metric("Status", clean_status(top["status"]), "Won / Leading / Unknown")

    display_cols = [
        "candidate",
        "party",
        "votes",
        "status",
        "margin",
    ]

    for col in display_cols:
        if col not in filtered.columns:
            filtered[col] = ""

    st.dataframe(
        filtered[display_cols].rename(
            columns={
                "candidate": "Candidate",
                "party": "Party",
                "votes": "Votes",
                "status": "Status",
                "margin": "Margin",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def main():
    inject_css()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Constituency Map Intelligence</div>
            <div class="hero-subtitle">
                Interactive Tamil Nadu assembly constituency map joined with candidate-level election data.
                Constituencies are matched using AC number, not constituency names, because map names may be truncated or formatted differently.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    candidate_df = load_candidate_data()
    party_df = load_party_data()
    geojson_data, geojson_error = load_geojson()

    if candidate_df.empty:
        st.error("Candidate dataset not found or empty. Run candidate ingestion first.")
        st.code("python eci_candidate_auto_ingest_v2.py --visible", language="powershell")
        return

    if geojson_error:
        st.error(geojson_error)
        st.markdown(
            """
            <div class="warning-box">
                Fix: place a valid Tamil Nadu assembly constituency GeoJSON file at:
                <br><b>data/geojson/tamil_nadu_ac.geojson</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    summary_df = prepare_constituency_summary(candidate_df)
    enriched_geojson, matched_count = enrich_geojson_with_results(geojson_data, summary_df)

    total_features = len(geojson_data.get("features", []))
    total_candidate_constituencies = summary_df["constituency_no"].nunique() if not summary_df.empty else 0
    total_candidate_rows = len(candidate_df)
    total_parties = candidate_df["party"].nunique() if "party" in candidate_df.columns else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_metric("Map Features", total_features, "Constituencies in GeoJSON")

    with c2:
        render_metric("Matched Features", matched_count, "Matched using AC_NO")

    with c3:
        render_metric("Candidate Rows", f"{total_candidate_rows:,}", "Rows in candidate dataset")

    with c4:
        render_metric("Candidate Parties", total_parties, "Unique parties in candidate feed")

    if matched_count == 0:
        st.markdown(
            """
            <div class="warning-box">
                No map features matched with candidate data. This means AC_NO and constituency_no are not aligned.
                Check whether the GeoJSON belongs to assembly constituencies and whether AC_NO values match ECI constituency numbers.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif matched_count < total_features:
        st.markdown(
            f"""
            <div class="warning-box">
                Partial map match: {matched_count} out of {total_features} map features matched.
                This is acceptable if one constituency has missing candidate data or if the feed has incomplete rows.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="success-box">
                Map matching is healthy. {matched_count} out of {total_features} constituency map features matched with candidate data.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Tamil Nadu Constituency Map</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="info-box">
            Click or hover over a constituency polygon to view leading party, leading candidate, votes, status, margin, and candidate count.
        </div>
        """,
        unsafe_allow_html=True,
    )

    map_object = build_map(enriched_geojson)

    st_folium(
        map_object,
        width=None,
        height=720,
        returned_objects=["last_clicked", "last_object_clicked"],
    )

    render_party_legend(summary_df)

    st.markdown('<div class="section-title">Constituency Drilldown</div>', unsafe_allow_html=True)

    if not summary_df.empty:
        summary_df = summary_df.sort_values("constituency_no")

        options = [
            f"{int(row['constituency_no'])} - {row['constituency']}"
            for _, row in summary_df.iterrows()
        ]

        selected = st.selectbox(
            "Select constituency",
            options=options,
            index=0,
        )

        selected_no = safe_int(selected.split(" - ")[0])
        render_constituency_detail(candidate_df, selected_no)

    st.markdown('<div class="section-title">Map-Matched Constituency Summary</div>', unsafe_allow_html=True)

    display_summary = summary_df.copy()

    if not display_summary.empty:
        display_summary = display_summary.rename(
            columns={
                "constituency_no": "AC No",
                "constituency": "Constituency",
                "leading_candidate": "Leading Candidate",
                "leading_party": "Leading Party",
                "leading_votes": "Votes",
                "leading_status": "Status",
                "leading_margin": "Margin",
                "total_candidates": "Candidates",
                "total_votes_recorded": "Total Votes Recorded",
            }
        )

        st.dataframe(
            display_summary,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown('<div class="section-title">Important Limitation</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="warning-box">
            This map currently supports Tamil Nadu candidate-level results because the available discovered constituency pages expose S22 assembly constituency data.
            Party-level trend monitoring still covers Assam, Kerala, Tamil Nadu, West Bengal, and Puducherry.
            Other state constituency maps and candidate pages should be added only after verified discovery.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()