import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from transform import (
    load_results,
    clean_uploaded_results,
    get_party_summary,
    get_close_contests,
    get_state_summary,
    get_vote_share,
)

from ai_insights import generate_election_summary


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Election Intelligence Platform",
    page_icon="EI",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(interval=300000, key="election_dashboard_refresh")


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
    "CPI": "#DC2626",
    "CPI(M)": "#991B1B",
    "AINRC": "#14B8A6",
    "AGP": "#EAB308",
    "AIUDF": "#15803D",
    "TVK": "#7C3AED",
    "BOPF": "#A855F7",
    "UPPL": "#FACC15",
    "IUML": "#0EA5E9",
    "IUNL": "#0EA5E9",
    "IND": "#94A3B8",
    "RJRD": "#2DD4BF",
    "RJD": "#22C55E",
    "RSP": "#F59E0B",
    "KEC": "#FB7185",
    "KEC(J)": "#F43F5E",
    "PMK": "#F87171",
    "VCK": "#4ADE80",
    "BGPM": "#818CF8",
    "AISF": "#CBD5E1",
    "RMPOI": "#FCA5A5",
    "CMPKSC": "#FDBA74",
    "AMMKMNKZ": "#A3E635",
}

FALLBACK_COLORS = [
    "#60A5FA",
    "#FBBF24",
    "#34D399",
    "#F472B6",
    "#A78BFA",
    "#38BDF8",
    "#FB923C",
    "#2DD4BF",
    "#E879F9",
    "#94A3B8",
]


def get_color_map(parties):
    color_map = {}
    fallback_index = 0

    for party in parties:
        party_clean = str(party).strip().upper()

        if party_clean in PARTY_COLORS:
            color_map[party_clean] = PARTY_COLORS[party_clean]
        else:
            color_map[party_clean] = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
            fallback_index += 1

    color_map["OTHERS"] = "#64748B"
    color_map["Others"] = "#64748B"
    return color_map


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>
    html {
        scroll-behavior: smooth;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(249, 115, 22, 0.12), transparent 26%),
            linear-gradient(180deg, #070b14 0%, #08111f 48%, #070b14 100%);
        color: #f8fafc;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 1480px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #101827 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    div[data-testid="stToolbar"] {
        background: rgba(7, 11, 20, 0.88);
    }

    .hero {
        padding: 1.15rem 1.5rem;
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(37, 99, 235, 0.28), rgba(15, 23, 42, 0.96)),
            linear-gradient(45deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(148, 163, 184, 0.20);
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.34);
        margin-bottom: 0.85rem;
    }

    .hero-title {
        font-size: 2.15rem;
        line-height: 1.05;
        font-weight: 900;
        letter-spacing: -0.055em;
        color: #ffffff;
        margin-bottom: 0.55rem;
    }

    .hero-subtitle {
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.55;
        max-width: 1080px;
    }

    .pill-row {
        display: flex;
        gap: 0.55rem;
        flex-wrap: wrap;
        margin-top: 0.85rem;
    }

    .pill {
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.78);
        color: #dbeafe;
        border: 1px solid rgba(96, 165, 250, 0.25);
        font-size: 0.78rem;
        font-weight: 750;
    }

    .status-strip {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.85rem;
    }

    .status-card {
        padding: 0.78rem 0.85rem;
        border-radius: 18px;
        background: rgba(15, 23, 42, 0.84);
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.16);
        min-height: 72px;
    }

    .status-label {
        color: #94a3b8;
        font-size: 0.78rem;
        font-weight: 750;
        margin-bottom: 0.28rem;
    }

    .status-value {
        color: #ffffff;
        font-size: 0.98rem;
        font-weight: 850;
        line-height: 1.22;
        word-break: break-word;
    }

    .metric-box {
        padding: 0.9rem 1rem;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.17);
        height: 100%;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 750;
        margin-bottom: 0.28rem;
    }

    .metric-value {
        color: #ffffff;
        font-size: 1.85rem;
        font-weight: 900;
        letter-spacing: -0.045em;
    }

    .metric-sub {
        color: #94a3b8;
        font-size: 0.76rem;
        margin-top: 0.2rem;
    }

    .section-title {
        font-size: 1.45rem;
        font-weight: 900;
        color: #f8fafc;
        margin-top: 0.6rem;
        margin-bottom: 0.75rem;
        letter-spacing: -0.025em;
    }

    .note-box {
        padding: 0.8rem 0.95rem;
        background: rgba(37, 99, 235, 0.11);
        border: 1px solid rgba(96, 165, 250, 0.22);
        border-radius: 16px;
        color: #dbeafe;
        font-size: 0.88rem;
        line-height: 1.5;
        margin-bottom: 0.85rem;
    }

    .warn-box {
        padding: 0.8rem 0.95rem;
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.28);
        border-radius: 16px;
        color: #fde68a;
        font-size: 0.88rem;
        line-height: 1.5;
        margin-bottom: 0.85rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(15, 23, 42, 0.62);
        border-radius: 18px;
        padding: 0.38rem;
        border: 1px solid rgba(148, 163, 184, 0.16);
        margin-bottom: 0.85rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 14px;
        padding: 0 1rem;
        color: #cbd5e1;
        font-weight: 800;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.14);
    }

    .stButton > button {
        border-radius: 15px;
        border: 1px solid rgba(96, 165, 250, 0.45);
        background: linear-gradient(135deg, #2563eb, #1e40af);
        color: white;
        font-weight: 850;
        padding: 0.62rem 1rem;
        box-shadow: 0 12px 30px rgba(37, 99, 235, 0.24);
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        border: 1px solid rgba(147, 197, 253, 0.75);
        box-shadow: 0 18px 42px rgba(37, 99, 235, 0.34);
    }

    .small-muted {
        color: #94a3b8;
        font-size: 0.84rem;
        line-height: 1.5;
    }

    .footer-note {
        color: #64748b;
        text-align: center;
        font-size: 0.82rem;
        padding-top: 1.5rem;
    }

    @media (max-width: 900px) {
        .status-strip {
            grid-template-columns: repeat(1, minmax(0, 1fr));
        }

        .hero-title {
            font-size: 1.9rem;
        }
    }
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def safe_datetime(value):
    try:
        if pd.isna(value):
            return "N/A"
        return pd.to_datetime(value).strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(value)


def render_metric(label, value, subtext=""):
    st.markdown(
        f"""
<div class="metric-box">
    <div class="metric-label">{label}</div>
    <div class="metric-value">{value}</div>
    <div class="metric-sub">{subtext}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(label, value):
    return f"""
<div class="status-card">
    <div class="status-label">{label}</div>
    <div class="status-value">{value}</div>
</div>
"""


def safe_dataframe(dataframe, height=420):
    st.dataframe(
        dataframe,
        use_container_width=True,
        height=height,
        hide_index=True,
    )


def plotly_layout(fig, height=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.56)",
        font=dict(color="#e5e7eb", size=13),
        margin=dict(l=10, r=10, t=52, b=28),
        legend=dict(
            bgcolor="rgba(15,23,42,0)",
            bordercolor="rgba(148,163,184,0)",
            font=dict(size=12),
        ),
        hoverlabel=dict(
            bgcolor="#111827",
            font_size=13,
            font_family="Arial",
        ),
    )

    if height is not None:
        fig.update_layout(height=height)

    return fig


def group_small_parties(df, party_col="party", value_col="votes", top_n=8):
    if df.empty:
        return df

    grouped = df.groupby(party_col, as_index=False)[value_col].sum()
    grouped = grouped.sort_values(value_col, ascending=False)

    top = grouped.head(top_n).copy()
    others = grouped.iloc[top_n:].copy()

    if not others.empty:
        others_row = pd.DataFrame([{party_col: "Others", value_col: others[value_col].sum()}])
        final_df = pd.concat([top, others_row], ignore_index=True)
    else:
        final_df = top

    total = final_df[value_col].sum()

    if total > 0:
        final_df["share_percent"] = (final_df[value_col] / total * 100).round(2)
    else:
        final_df["share_percent"] = 0

    return final_df


def prepare_display_df(df):
    display_df = df.copy()

    rename_map = {
        "state": "State",
        "constituency": "Reporting Unit",
        "candidate": "Party Full Name",
        "party": "Party",
        "votes": "Seat Trend Count",
        "status": "Trend Status",
        "margin": "Current Lead Count",
        "last_updated": "Last Synced",
    }

    display_df = display_df.rename(columns=rename_map)

    wanted_cols = [
        "State",
        "Reporting Unit",
        "Party Full Name",
        "Party",
        "Seat Trend Count",
        "Trend Status",
        "Current Lead Count",
        "Last Synced",
    ]

    available_cols = [col for col in wanted_cols if col in display_df.columns]
    return display_df[available_cols]

def get_government_tracker(df):
    if df.empty:
        return pd.DataFrame()

    tracker_rows = []

    for state, state_df in df.groupby("state"):
        party_totals = (
            state_df.groupby("party", as_index=False)["votes"]
            .sum()
            .sort_values("votes", ascending=False)
        )

        if party_totals.empty:
            continue

        total_seats_tracked = int(party_totals["votes"].sum())
        majority_mark = (total_seats_tracked // 2) + 1

        leading_party = party_totals.iloc[0]["party"]
        leading_party_total = int(party_totals.iloc[0]["votes"])

        second_party = party_totals.iloc[1]["party"] if len(party_totals) > 1 else "N/A"
        second_party_total = int(party_totals.iloc[1]["votes"]) if len(party_totals) > 1 else 0

        others_total = int(party_totals.iloc[2:]["votes"].sum()) if len(party_totals) > 2 else 0

        shortfall = max(majority_mark - leading_party_total, 0)

        if leading_party_total >= majority_mark:
            formation_status = "Can form government alone"
            others_required = "No"
            others_impact = "Low"
        elif leading_party_total + others_total >= majority_mark:
            formation_status = "Needs alliance/support"
            others_required = "Yes"
            others_impact = "High"
        else:
            formation_status = "Majority not visible yet"
            others_required = "Yes"
            others_impact = "Medium"

        tracker_rows.append(
            {
                "State": state,
                "Total Seats Tracked": total_seats_tracked,
                "Majority Mark": majority_mark,
                "Leading Party": leading_party,
                "Leading Party Trends": leading_party_total,
                "Second Party": second_party,
                "Second Party Trends": second_party_total,
                "Others / Smaller Parties": others_total,
                "Shortfall": shortfall,
                "Alliance Needed": others_required,
                "Others Impact": others_impact,
                "Formation Status": formation_status,
            }
        )

    return pd.DataFrame(tracker_rows)

def is_party_trend_data(df):
    if df.empty:
        return True

    match_ratio = (
        df["constituency"]
        .astype(str)
        .str.contains("Party Trend", case=False, na=False)
        .mean()
    )

    return match_ratio > 0.7


# ============================================================
# DATA LOAD
# ============================================================

try:
    df = load_results()
    source_mode = "ECI Automated Feed"
except Exception as e:
    st.error(f"Failed to load processed election data: {e}")
    st.stop()

required_columns = [
    "state",
    "constituency",
    "candidate",
    "party",
    "votes",
    "status",
    "margin",
    "last_updated",
]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error(f"Missing required columns in latest_results.csv: {missing_columns}")
    st.stop()

df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
df["margin"] = pd.to_numeric(df["margin"], errors="coerce").fillna(0).astype(int)
df["state"] = df["state"].astype(str)
df["party"] = df["party"].astype(str).str.strip().str.upper()
df["status"] = df["status"].astype(str)

party_trend_mode = is_party_trend_data(df)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## Live Control Panel")

    latest_sync = safe_datetime(df["last_updated"].max())

    st.markdown(
        f"""
<div class="note-box">
<b>ECI Automated Feed</b><br>
Refresh: 5 min<br>
Synced: {latest_sync}<br>
Mode: Party Trends
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## Filters")

    states = ["All"] + sorted(df["state"].dropna().unique().tolist())
    selected_state = st.selectbox("State", states)

    filtered_df = df.copy()

    if selected_state != "All":
        filtered_df = filtered_df[filtered_df["state"] == selected_state]

    parties = ["All"] + sorted(filtered_df["party"].dropna().unique().tolist())
    selected_party = st.selectbox("Party", parties)

    if selected_party != "All":
        filtered_df = filtered_df[filtered_df["party"] == selected_party]

    statuses = ["All"] + sorted(filtered_df["status"].dropna().unique().tolist())
    selected_status = st.selectbox("Trend Status", statuses)

    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    st.markdown("---")

    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()

    with st.expander("Manual CSV Override"):
        st.caption("Use this only if automated ingestion fails.")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        if uploaded_file is not None:
            try:
                uploaded_df = clean_uploaded_results(uploaded_file)
                uploaded_df["party"] = uploaded_df["party"].astype(str).str.strip().str.upper()
                filtered_df = uploaded_df.copy()
                df = uploaded_df.copy()
                source_mode = "Manual CSV Override"
                st.success("Manual CSV loaded for this session.")
            except Exception as e:
                st.error(f"Manual CSV failed: {e}")

    with st.expander("Color Logic"):
        st.caption("Major parties use fixed colors. Smaller parties use fallback colors.")


# ============================================================
# DERIVED DATA
# ============================================================

all_parties = sorted(df["party"].dropna().unique().tolist())
color_map = get_color_map(all_parties + ["Others"])

party_summary = get_party_summary(filtered_df)
state_summary = get_state_summary(filtered_df)
vote_share_df = get_vote_share(filtered_df)
government_tracker_df = get_government_tracker(filtered_df)

total_rows = len(filtered_df)
total_states = filtered_df["state"].nunique()
total_parties = filtered_df["party"].nunique()
total_trend_count = int(filtered_df["votes"].sum()) if not filtered_df.empty else 0

leading_count = (
    int(filtered_df[filtered_df["status"].str.lower() == "leading"]["votes"].sum())
    if not filtered_df.empty
    else 0
)

won_count = (
    int(filtered_df[filtered_df["status"].str.lower() == "won"]["votes"].sum())
    if not filtered_df.empty
    else 0
)

latest_update = safe_datetime(filtered_df["last_updated"].max()) if not filtered_df.empty else "N/A"


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-title">Election Intelligence Platform</div>
    <div class="hero-subtitle">
        Live election trend ingestion, automated refresh, party-wise analytics, state-level monitoring,
        competitive trend detection, and AI-assisted summaries built as a data engineering portfolio project.
    </div>
    <div class="pill-row">
        <div class="pill">Automated ECI Scraper</div>
        <div class="pill">5-Minute Scheduler</div>
        <div class="pill">Python</div>
        <div class="pill">Streamlit</div>
        <div class="pill">Plotly</div>
        <div class="pill">Groq AI Ready</div>
    </div>
</div>
    """,
    unsafe_allow_html=True,
)

status_html = (
    '<div class="status-strip">'
    f'{render_status_card("Live Source", source_mode)}'
    f'{render_status_card("States Covered", total_states)}'
    f'{render_status_card("Parties Tracked", total_parties)}'
    f'{render_status_card("Seat Trends", total_trend_count)}'
    f'{render_status_card("Last Synced", latest_update)}'
    '</div>'
)

st.markdown(status_html, unsafe_allow_html=True)


# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4 = st.columns(4)

with k1:
    render_metric("Reporting Rows", total_rows, "Party-state rows after filters")

with k2:
    render_metric("Seat Trends", total_trend_count, "Total seats represented in feed")

with k3:
    render_metric("Leading", leading_count, "Seat trends currently leading")

with k4:
    render_metric("Won", won_count, "Seat trends marked won")


# ============================================================
# TABS
# ============================================================

overview_tab, state_tab, govt_tab, close_tab, party_tab, ai_tab, raw_tab = st.tabs(
    [
        "Overview",
        "State Monitor",
        "Government Tracker",
        "Close Watch",
        "Party Analytics",
        "AI Analyst",
        "Data Table",
    ]
)


# ============================================================
# OVERVIEW TAB
# ============================================================

with overview_tab:
    st.markdown(
        '<div class="section-title">National Party Trend Snapshot</div>',
        unsafe_allow_html=True,
    )

    top_party_df = group_small_parties(
        filtered_df,
        party_col="party",
        value_col="votes",
        top_n=10,
    )

    left, right = st.columns([1.45, 0.95])

    with left:
        if not top_party_df.empty:
            fig = px.bar(
                top_party_df.sort_values("votes", ascending=True),
                x="votes",
                y="party",
                orientation="h",
                color="party",
                color_discrete_map=color_map,
                text="votes",
                title="Top Party Seat Trends",
                labels={
                    "votes": "Seat Trend Count",
                    "party": "Party",
                },
            )

            fig.update_traces(textposition="outside", cliponaxis=False)
            fig = plotly_layout(fig, height=430)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No party trend data available.")

    with right:
        if not top_party_df.empty:
            fig_donut = px.pie(
                top_party_df,
                names="party",
                values="votes",
                hole=0.62,
                color="party",
                color_discrete_map=color_map,
                title="Trend Share",
            )

            fig_donut.update_traces(
                textposition="inside",
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Seat Trends: %{value}<br>Share: %{percent}<extra></extra>",
            )

            fig_donut = plotly_layout(fig_donut, height=430)
            st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown(
        '<div class="section-title">Trend Share Table</div>',
        unsafe_allow_html=True,
    )

    if not top_party_df.empty:
        share_table = top_party_df.rename(
            columns={
                "party": "Party",
                "votes": "Seat Trend Count",
                "share_percent": "Share %",
            }
        )
        safe_dataframe(share_table, height=300)

    st.markdown(
        '<div class="section-title">State Summary</div>',
        unsafe_allow_html=True,
    )

    state_display = state_summary.copy()
    state_display = state_display.rename(
        columns={
            "state": "State",
            "total_constituencies": "Reporting Units",
            "total_parties": "Parties Tracked",
            "last_updated": "Last Synced",
        }
    )

    safe_dataframe(state_display, height=280)


# ============================================================
# STATE MONITOR TAB
# ============================================================

with state_tab:
    st.markdown(
        '<div class="section-title">State-wise Party Strength</div>',
        unsafe_allow_html=True,
    )

    if not filtered_df.empty:
        state_party = (
            filtered_df.groupby(["state", "party"], as_index=False)["votes"]
            .sum()
            .sort_values(["state", "votes"], ascending=[True, False])
        )

        fig_state = px.bar(
            state_party,
            x="state",
            y="votes",
            color="party",
            color_discrete_map=color_map,
            title="State-wise Seat Trend Distribution",
            labels={
                "state": "State",
                "votes": "Seat Trend Count",
                "party": "Party",
            },
            hover_data=["party", "votes"],
        )

        fig_state = plotly_layout(fig_state, height=500)
        st.plotly_chart(fig_state, use_container_width=True)

        st.markdown(
            '<div class="section-title">State Detail Table</div>',
            unsafe_allow_html=True,
        )

        state_detail = state_party.rename(
            columns={
                "state": "State",
                "party": "Party",
                "votes": "Seat Trend Count",
            }
        )

        safe_dataframe(state_detail, height=430)
    else:
        st.info("No state-level data available.")
        
# ============================================================
# GOVERNMENT TRACKER TAB
# ============================================================

with govt_tab:
    st.markdown(
        '<div class="section-title">Trend-based Government Formation Tracker</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="note-box">
This section estimates government formation possibilities using party-wise seat trend counts.
It is not a final result prediction. Final government formation depends on certified constituency results, alliances, and official declarations.
</div>
        """,
        unsafe_allow_html=True,
    )

    if government_tracker_df.empty:
        st.info("No government formation data available for the current filters.")
    else:
        total_states_in_tracker = government_tracker_df["State"].nunique()
        alone_count = int(
            (government_tracker_df["Formation Status"] == "Can form government alone").sum()
        )
        alliance_count = int(
            (government_tracker_df["Formation Status"] == "Needs alliance/support").sum()
        )
        unclear_count = int(
            (government_tracker_df["Formation Status"] == "Majority not visible yet").sum()
        )

        g1, g2, g3, g4 = st.columns(4)

        with g1:
            render_metric(
                "States Analysed",
                total_states_in_tracker,
                "States in current filter"
            )

        with g2:
            render_metric(
                "Clear Majority",
                alone_count,
                "Trend majority visible"
            )

        with g3:
            render_metric(
                "Alliance Needed",
                alliance_count,
                "Support may be required"
            )

        with g4:
            render_metric(
                "Unclear",
                unclear_count,
                "Majority not visible yet"
            )

        st.markdown(
            '<div class="section-title">State-wise Majority Position</div>',
            unsafe_allow_html=True,
        )

        safe_dataframe(government_tracker_df, height=360)

        st.markdown(
            '<div class="section-title">Leading Party vs Majority Mark</div>',
            unsafe_allow_html=True,
        )

        plot_df = government_tracker_df.copy()

        fig_govt = px.bar(
            plot_df,
            x="State",
            y=["Leading Party Trends", "Shortfall"],
            barmode="stack",
            title="Leading Party Position Against Majority Requirement",
            labels={
                "value": "Seat Trend Count",
                "variable": "Metric",
                "State": "State",
            },
        )

        fig_govt = plotly_layout(fig_govt, height=480)
        st.plotly_chart(fig_govt, use_container_width=True)

        st.markdown(
            '<div class="section-title">Others / Smaller Parties Impact</div>',
            unsafe_allow_html=True,
        )

        impact_df = government_tracker_df[
            [
                "State",
                "Leading Party",
                "Leading Party Trends",
                "Majority Mark",
                "Others / Smaller Parties",
                "Alliance Needed",
                "Others Impact",
                "Formation Status",
            ]
        ].copy()

        safe_dataframe(impact_df, height=340)

        impact_chart_df = government_tracker_df.copy()

        fig_others = px.bar(
            impact_chart_df,
            x="State",
            y="Others / Smaller Parties",
            color="Others Impact",
            title="Potential Influence of Smaller Parties / Others",
            labels={
                "Others / Smaller Parties": "Seat Trend Count",
                "State": "State",
                "Others Impact": "Impact Level",
            },
        )

        fig_others = plotly_layout(fig_others, height=430)
        st.plotly_chart(fig_others, use_container_width=True)

# ============================================================
# CLOSE WATCH TAB
# ============================================================

with close_tab:
    st.markdown(
        '<div class="section-title">Competitive Trend Watch</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="warn-box">
Current feed is party-trend level, not candidate-level constituency margin data.
This section tracks low-volume party trend rows. Candidate-level close contests require the next scraping layer.
</div>
        """,
        unsafe_allow_html=True,
    )

    max_value = int(filtered_df["votes"].max()) if not filtered_df.empty else 1
    threshold_default = min(10, max_value)

    low_trend_limit = st.slider(
        "Low trend count threshold",
        min_value=1,
        max_value=max(2, max_value),
        value=max(1, threshold_default),
        step=1,
    )

    low_trend_df = filtered_df[filtered_df["votes"] <= low_trend_limit].sort_values(
        "votes",
        ascending=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        render_metric(
            "Low Trend Rows",
            len(low_trend_df),
            f"Rows with trend count <= {low_trend_limit}",
        )

    with c2:
        render_metric(
            "States Affected",
            low_trend_df["state"].nunique() if not low_trend_df.empty else 0,
            "States with low-volume rows",
        )

    with c3:
        render_metric(
            "Parties Affected",
            low_trend_df["party"].nunique() if not low_trend_df.empty else 0,
            "Parties in low-volume rows",
        )

    if not low_trend_df.empty:
        fig_low = px.bar(
            low_trend_df,
            x="votes",
            y="party",
            color="party",
            color_discrete_map=color_map,
            orientation="h",
            facet_col="state",
            title=f"Low-volume Party Trends <= {low_trend_limit}",
            labels={
                "votes": "Seat Trend Count",
                "party": "Party",
            },
            hover_data=["state", "candidate", "status"],
        )

        fig_low = plotly_layout(fig_low, height=520)
        st.plotly_chart(fig_low, use_container_width=True)

        safe_dataframe(prepare_display_df(low_trend_df), height=400)
    else:
        st.info("No low-volume trend rows for this threshold.")


# ============================================================
# PARTY ANALYTICS TAB
# ============================================================

with party_tab:
    st.markdown(
        '<div class="section-title">Party Analytics</div>',
        unsafe_allow_html=True,
    )

    if not party_summary.empty:
        party_summary_display = party_summary.copy()

        c1, c2 = st.columns([1.05, 1])

        with c1:
            fig_lead = px.bar(
                party_summary_display,
                x="party",
                y=["Leading", "Won"],
                title="Leading vs Won by Party",
                barmode="group",
                labels={
                    "value": "Seat Trend Count",
                    "party": "Party",
                    "variable": "Status",
                },
            )

            fig_lead = plotly_layout(fig_lead, height=490)
            st.plotly_chart(fig_lead, use_container_width=True)

        with c2:
            party_total = (
                filtered_df.groupby("party", as_index=False)["votes"]
                .sum()
                .sort_values("votes", ascending=False)
                .head(15)
            )

            fig_rank = px.bar(
                party_total.sort_values("votes", ascending=True),
                x="votes",
                y="party",
                orientation="h",
                color="party",
                color_discrete_map=color_map,
                text="votes",
                title="Top 15 Parties by Seat Trend Count",
                labels={
                    "votes": "Seat Trend Count",
                    "party": "Party",
                },
            )

            fig_rank.update_traces(textposition="outside", cliponaxis=False)
            fig_rank = plotly_layout(fig_rank, height=490)
            st.plotly_chart(fig_rank, use_container_width=True)

        st.markdown(
            '<div class="section-title">Party Summary Table</div>',
            unsafe_allow_html=True,
        )

        party_table = party_summary_display.rename(
            columns={
                "state": "State",
                "party": "Party",
                "Leading": "Leading",
                "Won": "Won",
                "total": "Total Seat Trends",
            }
        )

        safe_dataframe(party_table, height=430)

    st.markdown(
        '<div class="section-title">Trend Count Distribution</div>',
        unsafe_allow_html=True,
    )

    if not filtered_df.empty:
        fig_dist = px.histogram(
            filtered_df,
            x="votes",
            color="party",
            color_discrete_map=color_map,
            nbins=18,
            title="Distribution of Party Seat Trend Counts",
            labels={
                "votes": "Seat Trend Count",
                "count": "Rows",
                "party": "Party",
            },
        )

        fig_dist = plotly_layout(fig_dist, height=490)
        st.plotly_chart(fig_dist, use_container_width=True)


# ============================================================
# AI ANALYST TAB
# ============================================================

with ai_tab:
    st.markdown(
        '<div class="section-title">AI Election Analyst</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="note-box">
The AI analyst summarizes only the structured dashboard data currently loaded.
It is an explanatory layer, not a prediction engine or official result source.
</div>
        """,
        unsafe_allow_html=True,
    )

    ai_left, ai_right = st.columns([1, 1.2])

    with ai_left:
        st.markdown("#### Analysis Scope")
        st.markdown(
            """
<div class="metric-box">
    <div class="small-muted">
        Current scope includes party-wise seat trend counts, state coverage,
        leading and won status, and top-party movement. Candidate-level constituency margins
        will require the next scraping layer.
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with ai_right:
        st.markdown("#### Generate Structured Summary")

        if st.button("Generate AI Summary", use_container_width=True):
            with st.spinner("Generating AI summary from current dashboard data..."):
                try:
                    close_df_for_ai = get_close_contests(filtered_df, 1000)
                    summary_text = generate_election_summary(
                        filtered_df,
                        close_df_for_ai,
                        party_summary,
                    )
                    st.markdown(summary_text)
                except Exception as e:
                    st.error(f"AI summary failed: {e}")
                    st.info("Check your Groq API key inside the .env file.")


# ============================================================
# DATA TABLE TAB
# ============================================================

with raw_tab:
    st.markdown(
        '<div class="section-title">Cleaned Election Trend Data</div>',
        unsafe_allow_html=True,
    )

    safe_dataframe(prepare_display_df(filtered_df), height=560)

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Current Filtered Dataset",
        data=csv_data,
        file_name="election_trend_data_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer-note">
Automated election data engineering and analytics platform.
</div>
    """,
    unsafe_allow_html=True,
)