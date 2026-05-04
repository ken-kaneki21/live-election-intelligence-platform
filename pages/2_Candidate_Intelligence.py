import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from azure_data_loader import load_candidate_results, load_candidate_coverage_report


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Candidate Intelligence",
    page_icon="CI",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(interval=300000, key="candidate_intelligence_refresh")


# ============================================================
# PATHS
# ============================================================

CANDIDATE_FILE = "data/processed/latest_candidate_results.csv"
COVERAGE_FILE = "data/processed/candidate_coverage_report.csv"


# ============================================================
# PARTY COLORS
# ============================================================

PARTY_COLORS = {
    "BJP": "#F97316",
    "INC": "#2563EB",
    "AITC": "#16A34A",
    "TMC": "#16A34A",
    "DMK": "#EF4444",
    "ADMK": "#22C55E",
    "AIADMK": "#22C55E",
    "TVK": "#7C3AED",
    "CPI": "#DC2626",
    "CPI(M)": "#991B1B",
    "Iuml": "#10B981",
    "IUML": "#10B981",
    "AINRC": "#38BDF8",
    "IND": "#94A3B8",
    "NTK": "#FACC15",
    "VCK": "#A855F7",
    "PMK": "#EC4899",
    "DMDK": "#F59E0B",
    "BSP": "#1D4ED8",
    "NOTA": "#64748B",
}


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(96, 29, 44, 0.28), transparent 35%),
                linear-gradient(135deg, #030712 0%, #07111f 45%, #090b16 100%);
            color: #ffffff;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        .hero-card {
            padding: 28px 32px;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(15, 23, 42, 0.95));
            border: 1px solid rgba(96, 165, 250, 0.28);
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
            margin-bottom: 22px;
        }

        .hero-title {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -1.2px;
        }

        .hero-subtitle {
            font-size: 17px;
            line-height: 1.7;
            color: #cbd5e1;
            max-width: 1100px;
        }

        .metric-card {
            padding: 22px;
            border-radius: 20px;
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.22);
            min-height: 130px;
        }

        .metric-label {
            font-size: 14px;
            font-weight: 700;
            color: #93c5fd;
            margin-bottom: 12px;
        }

        .metric-value {
            font-size: 34px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
        }

        .metric-note {
            margin-top: 12px;
            color: #93c5fd;
            font-size: 13px;
            line-height: 1.5;
        }

        .info-box {
            padding: 18px 22px;
            border-radius: 18px;
            background: rgba(30, 64, 175, 0.18);
            border: 1px solid rgba(59, 130, 246, 0.35);
            color: #dbeafe;
            line-height: 1.6;
            margin: 18px 0;
        }

        .warning-box {
            padding: 18px 22px;
            border-radius: 18px;
            background: rgba(120, 53, 15, 0.35);
            border: 1px solid rgba(245, 158, 11, 0.45);
            color: #fde68a;
            line-height: 1.6;
            margin: 18px 0;
        }

        .section-title {
            font-size: 27px;
            font-weight: 800;
            margin-top: 30px;
            margin-bottom: 16px;
            letter-spacing: -0.6px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(15, 23, 42, 0.86);
            padding: 8px;
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 14px;
            padding: 10px 18px;
            color: #dbeafe;
        }

        .stTabs [aria-selected="true"] {
            background: #2563eb;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    # Defensive handling: sometimes duplicate column names make pandas pass a Series
    # instead of a scalar. Pick the first non-empty value instead of crashing.
    if isinstance(value, pd.Series):
        non_empty = value.dropna().astype(str)
        if non_empty.empty:
            return ""
        value = non_empty.iloc[0]

    if pd.isna(value):
        return ""

    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def coalesce_duplicate_columns(df):
    # After renaming columns like result_status/derived_status -> status, pandas can
    # contain duplicate column names. Then df["status"] becomes a DataFrame, not a Series.
    # This function merges duplicate columns row-wise using the first non-empty value.
    if not df.columns.duplicated().any():
        return df

    output = pd.DataFrame(index=df.index)

    for col in dict.fromkeys(df.columns):
        selected = df.loc[:, df.columns == col]

        if selected.shape[1] == 1:
            output[col] = selected.iloc[:, 0]
            continue

        merged = selected.bfill(axis=1).iloc[:, 0]
        output[col] = merged

    return output


def clean_status(value):
    value = clean_text(value).lower()

    if value in ["won", "winner", "elected"]:
        return "Won"

    if value in ["leading", "lead"]:
        return "Leading"

    if value in ["trailing", "lost", "losing"]:
        return "Trailing"

    if value == "":
        return "Unknown"

    return value.title()


def normalize_party(value):
    value = clean_text(value)
    if not value:
        return "Unknown"
    return value.upper()


def safe_int(value):
    try:
        if pd.isna(value):
            return 0
        value = str(value).replace(",", "")
        match = re.search(r"-?\d+", value)
        if match:
            return int(match.group(0))
        return 0
    except Exception:
        return 0


def get_file_modified_time(path):
    if not os.path.exists(path):
        return "Not available"

    modified = datetime.fromtimestamp(os.path.getmtime(path))
    return modified.strftime("%d %b %Y, %I:%M %p")


@st.cache_data(ttl=60)
def load_candidate_data():
    df = load_candidate_results()

    if df.empty:
        return df

    df.columns = [clean_text(col).lower() for col in df.columns]

    rename_map = {
        "candidate name": "candidate",
        "candidate_name": "candidate",
        "party name": "party",
        "party_name": "party",
        "state_name": "state",
        "ac_name": "constituency",
        "constituency_name": "constituency",
        "ac_no": "constituency_no",
        "constituency_number": "constituency_no",
        "total_votes": "votes",
        "vote": "votes",
        "result_status": "status",
        "derived_status": "status",
        "vote_margin": "margin",
    }

    df = df.rename(columns={col: rename_map.get(col, col) for col in df.columns})
    df = coalesce_duplicate_columns(df)

    required_columns = [
        "state",
        "state_code",
        "constituency",
        "constituency_no",
        "candidate",
        "party",
        "votes",
        "status",
        "margin",
        "scraped_at",
    ]

    for col in required_columns:
        if col not in df.columns:
            if col in ["votes", "margin", "constituency_no"]:
                df[col] = 0
            elif col == "state":
                df[col] = "Tamil Nadu"
            elif col == "state_code":
                df[col] = "S22"
            elif col == "status":
                df[col] = "Unknown"
            else:
                df[col] = ""

    df["state"] = df["state"].apply(clean_text)
    df["state_code"] = df["state_code"].apply(clean_text)
    df["constituency"] = df["constituency"].apply(clean_text)
    df["candidate"] = df["candidate"].apply(clean_text)
    df["party"] = df["party"].apply(normalize_party)
    df["status"] = df["status"].apply(clean_status)
    df["votes"] = df["votes"].apply(safe_int)
    df["margin"] = df["margin"].apply(safe_int)
    df["constituency_no"] = df["constituency_no"].apply(safe_int)

    df = df[
        (df["candidate"].ne("")) |
        (df["party"].ne("UNKNOWN")) |
        (df["votes"].gt(0))
    ].copy()

    return df


@st.cache_data(ttl=60)
def load_coverage_data():
    df = load_candidate_coverage_report()

    if df.empty:
        return df

    df.columns = [clean_text(col).lower() for col in df.columns]
    return df


def prepare_constituency_summary(df):
    if df.empty:
        return pd.DataFrame()

    working = df.copy()

    required_cols = ["state", "constituency", "candidate", "party", "votes", "status"]
    for col in required_cols:
        if col not in working.columns:
            working[col] = ""

    working["votes"] = working["votes"].apply(safe_int)
    working["status"] = working["status"].apply(clean_status)

    working = working.sort_values(
        ["state", "constituency", "votes"],
        ascending=[True, True, False]
    )

    rows = []

    for (state, constituency), group in working.groupby(["state", "constituency"]):
        group = group.sort_values("votes", ascending=False).reset_index(drop=True)

        top = group.iloc[0]
        second = group.iloc[1] if len(group) > 1 else None

        top_votes = safe_int(top.get("votes", 0))
        second_votes = safe_int(second.get("votes", 0)) if second is not None else 0
        margin = top_votes - second_votes

        top_status = clean_status(top.get("status", "Unknown"))

        if top_status == "Unknown":
            top_status = "Leading"

        rows.append(
            {
                "state": state,
                "constituency": constituency,
                "leading_candidate": clean_text(top.get("candidate", "")),
                "leading_party": normalize_party(top.get("party", "")),
                "leading_votes": top_votes,
                "second_candidate": clean_text(second.get("candidate", "")) if second is not None else "",
                "second_party": normalize_party(second.get("party", "")) if second is not None else "",
                "second_votes": second_votes,
                "margin": margin,
                "status": top_status,
                "candidates_count": len(group),
            }
        )

    return pd.DataFrame(rows)


def apply_filters(df, selected_state, selected_party, selected_status, search_text):
    filtered = df.copy()

    if selected_state != "All":
        filtered = filtered[filtered["state"] == selected_state]

    if selected_party != "All":
        filtered = filtered[filtered["party"] == selected_party]

    if selected_status != "All":
        filtered = filtered[filtered["status"] == selected_status]

    if search_text:
        search_text = search_text.lower().strip()
        filtered = filtered[
            filtered["candidate"].str.lower().str.contains(search_text, na=False) |
            filtered["constituency"].str.lower().str.contains(search_text, na=False) |
            filtered["party"].str.lower().str.contains(search_text, na=False)
        ]

    return filtered


def plot_party_candidate_strength(summary_df):
    if summary_df.empty:
        return None

    party_df = (
        summary_df.groupby("leading_party", as_index=False)
        .agg(
            seats=("constituency", "count"),
            avg_margin=("margin", "mean"),
        )
        .sort_values("seats", ascending=False)
    )

    fig = px.bar(
        party_df.head(20),
        x="seats",
        y="leading_party",
        orientation="h",
        text="seats",
        color="leading_party",
        color_discrete_map=PARTY_COLORS,
        title="Leading/Won Constituencies by Party",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.65)",
        font=dict(color="#ffffff"),
        showlegend=False,
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    fig.update_traces(textposition="outside")
    fig.update_yaxes(categoryorder="total ascending")

    return fig


def plot_margin_distribution(summary_df):
    if summary_df.empty:
        return None

    fig = px.histogram(
        summary_df,
        x="margin",
        nbins=35,
        color="leading_party",
        color_discrete_map=PARTY_COLORS,
        title="Constituency Margin Distribution",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.65)",
        font=dict(color="#ffffff"),
        height=480,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig


def plot_top_close_contests(summary_df):
    if summary_df.empty:
        return None

    close_df = summary_df.sort_values("margin", ascending=True).head(25)

    fig = px.bar(
        close_df,
        x="margin",
        y="constituency",
        orientation="h",
        color="leading_party",
        color_discrete_map=PARTY_COLORS,
        hover_data=[
            "leading_candidate",
            "leading_party",
            "second_candidate",
            "second_party",
            "leading_votes",
            "second_votes",
        ],
        title="Closest Constituencies by Vote Margin",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.65)",
        font=dict(color="#ffffff"),
        height=620,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    fig.update_yaxes(categoryorder="total descending")

    return fig


# ============================================================
# LOAD DATA
# ============================================================

candidate_df = load_candidate_data()
coverage_df = load_coverage_data()

if candidate_df.empty:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Candidate Intelligence</div>
            <div class="hero-subtitle">
                Candidate-level dataset is not available yet. Run the candidate scraper first.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.code("python eci_candidate_auto_ingest_v2.py --visible", language="powershell")
    st.stop()


summary_df = prepare_constituency_summary(candidate_df)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## Candidate Controls")

st.sidebar.markdown(
    f"""
    <div class="info-box">
        <b>Dataset:</b> Candidate-level feed<br>
        <b>Last Updated:</b> {get_file_modified_time(CANDIDATE_FILE)}<br>
        <b>Rows:</b> {len(candidate_df):,}<br>
        <b>Constituencies:</b> {candidate_df["constituency"].nunique():,}
    </div>
    """,
    unsafe_allow_html=True,
)

state_options = ["All"] + sorted(candidate_df["state"].dropna().unique().tolist())
party_options = ["All"] + sorted(candidate_df["party"].dropna().unique().tolist())
status_options = ["All"] + sorted(candidate_df["status"].dropna().unique().tolist())

selected_state = st.sidebar.selectbox("State", state_options)
selected_party = st.sidebar.selectbox("Party", party_options)
selected_status = st.sidebar.selectbox("Status", status_options)
search_text = st.sidebar.text_input("Search candidate / constituency / party")

if st.sidebar.button("Refresh Candidate Page", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


filtered_candidate_df = apply_filters(
    candidate_df,
    selected_state,
    selected_party,
    selected_status,
    search_text,
)

filtered_summary_df = prepare_constituency_summary(filtered_candidate_df)


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">Candidate Intelligence</div>
        <div class="hero-subtitle">
            Candidate-level election intelligence for constituency-level monitoring, party performance,
            leading candidate tracking, close-margin detection, and data quality validation.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# KPI CARDS
# ============================================================

total_candidates = len(filtered_candidate_df)
total_constituencies = filtered_candidate_df["constituency"].nunique()
total_parties = filtered_candidate_df["party"].nunique()
total_states = filtered_candidate_df["state"].nunique()

won_count = int((filtered_summary_df["status"] == "Won").sum()) if not filtered_summary_df.empty else 0
leading_count = int((filtered_summary_df["status"] == "Leading").sum()) if not filtered_summary_df.empty else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Candidates</div>
            <div class="metric-value">{total_candidates:,}</div>
            <div class="metric-note">Candidate rows after filters</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Constituencies</div>
            <div class="metric-value">{total_constituencies:,}</div>
            <div class="metric-note">Constituencies represented</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Parties</div>
            <div class="metric-value">{total_parties:,}</div>
            <div class="metric-note">Unique parties in candidate feed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">States</div>
            <div class="metric-value">{total_states:,}</div>
            <div class="metric-note">Candidate-level state coverage</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="warning-box">
        Candidate-level coverage currently depends on constituency pages exposed by the active ECI result path.
        Party-level monitoring may cover more states than candidate-level monitoring.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Candidate Overview",
        "Constituency Tracker",
        "Close Contests",
        "Party Performance",
        "Raw Candidate Data",
    ]
)


# ============================================================
# TAB 1
# ============================================================

with tab1:
    st.markdown('<div class="section-title">Candidate-Level Overview</div>', unsafe_allow_html=True)

    a, b = st.columns([1.15, 0.85])

    with a:
        fig = plot_party_candidate_strength(filtered_summary_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No party strength chart available for current filters.")

    with b:
        if not filtered_summary_df.empty:
            top_party_summary = (
                filtered_summary_df.groupby("leading_party", as_index=False)
                .agg(
                    seats=("constituency", "count"),
                    avg_margin=("margin", "mean"),
                )
                .sort_values("seats", ascending=False)
            )

            st.dataframe(
                top_party_summary,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No summary rows available.")

    st.markdown('<div class="section-title">Margin Distribution</div>', unsafe_allow_html=True)

    fig = plot_margin_distribution(filtered_summary_df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 2
# ============================================================

with tab2:
    st.markdown('<div class="section-title">Constituency Tracker</div>', unsafe_allow_html=True)

    if filtered_summary_df.empty:
        st.warning("No constituency summary available for selected filters.")
    else:
        display_summary = filtered_summary_df.sort_values(
            ["state", "constituency"]
        )

        st.dataframe(
            display_summary[
                [
                    "state",
                    "constituency",
                    "leading_candidate",
                    "leading_party",
                    "leading_votes",
                    "second_candidate",
                    "second_party",
                    "second_votes",
                    "margin",
                    "status",
                    "candidates_count",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        selected_constituency = st.selectbox(
            "Select constituency for detailed candidate list",
            sorted(display_summary["constituency"].dropna().unique().tolist()),
        )

        detail_df = filtered_candidate_df[
            filtered_candidate_df["constituency"] == selected_constituency
        ].sort_values("votes", ascending=False)

        st.markdown(f'<div class="section-title">{selected_constituency} Candidate Details</div>', unsafe_allow_html=True)

        st.dataframe(
            detail_df[
                [
                    "state",
                    "constituency",
                    "candidate",
                    "party",
                    "votes",
                    "status",
                    "margin",
                    "scraped_at",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB 3
# ============================================================

with tab3:
    st.markdown('<div class="section-title">Close Contest Monitor</div>', unsafe_allow_html=True)

    if filtered_summary_df.empty:
        st.warning("No close contest data available.")
    else:
        margin_limit = st.slider(
            "Maximum margin threshold",
            min_value=0,
            max_value=max(1000, int(filtered_summary_df["margin"].max())),
            value=min(1000, max(1, int(filtered_summary_df["margin"].max()))),
            step=50,
        )

        close_df = filtered_summary_df[
            filtered_summary_df["margin"] <= margin_limit
        ].sort_values("margin", ascending=True)

        k1, k2, k3 = st.columns(3)

        with k1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Close Constituencies</div>
                    <div class="metric-value">{len(close_df):,}</div>
                    <div class="metric-note">Margin <= {margin_limit:,}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with k2:
            smallest_margin = int(close_df["margin"].min()) if not close_df.empty else 0
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Smallest Margin</div>
                    <div class="metric-value">{smallest_margin:,}</div>
                    <div class="metric-note">Lowest visible margin</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with k3:
            close_parties = close_df["leading_party"].nunique() if not close_df.empty else 0
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Parties In Close Seats</div>
                    <div class="metric-value">{close_parties:,}</div>
                    <div class="metric-note">Unique leading parties</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        fig = plot_top_close_contests(close_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            close_df[
                [
                    "state",
                    "constituency",
                    "leading_candidate",
                    "leading_party",
                    "leading_votes",
                    "second_candidate",
                    "second_party",
                    "second_votes",
                    "margin",
                    "status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB 4
# ============================================================

with tab4:
    st.markdown('<div class="section-title">Party Performance</div>', unsafe_allow_html=True)

    if filtered_summary_df.empty:
        st.warning("No party performance data available.")
    else:
        party_perf = (
            filtered_summary_df.groupby("leading_party", as_index=False)
            .agg(
                constituencies_led=("constituency", "count"),
                avg_margin=("margin", "mean"),
                max_margin=("margin", "max"),
                min_margin=("margin", "min"),
            )
            .sort_values("constituencies_led", ascending=False)
        )

        party_perf["avg_margin"] = party_perf["avg_margin"].round(2)

        st.dataframe(
            party_perf,
            use_container_width=True,
            hide_index=True,
        )

        fig = px.scatter(
            party_perf,
            x="constituencies_led",
            y="avg_margin",
            size="constituencies_led",
            color="leading_party",
            color_discrete_map=PARTY_COLORS,
            hover_name="leading_party",
            title="Party Strength vs Average Margin",
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.65)",
            font=dict(color="#ffffff"),
            height=520,
            margin=dict(l=20, r=20, t=60, b=20),
        )

        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 5
# ============================================================

with tab5:
    st.markdown('<div class="section-title">Raw Candidate Data</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="info-box">
            This table shows the cleaned candidate-level dataset currently powering this page.
            It is useful for debugging, validation, and portfolio demonstration.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        filtered_candidate_df.sort_values(
            ["state", "constituency", "votes"],
            ascending=[True, True, False],
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv_data = filtered_candidate_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download filtered candidate data",
        data=csv_data,
        file_name="filtered_candidate_results.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# COVERAGE REPORT
# ============================================================

if not coverage_df.empty:
    with st.expander("Candidate Coverage Report"):
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)


st.markdown(
    """
    <div style="text-align:center; color:#64748b; padding:28px 0 10px 0;">
        Candidate intelligence layer for the Election Intelligence Platform.
    </div>
    """,
    unsafe_allow_html=True,
)