import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from transform import (
    clean_uploaded_results,
    get_party_summary,
    get_close_contests,
    get_state_summary,
    get_vote_share,
)

from ai_insights import generate_election_summary
from azure_data_loader import load_party_results


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Election Intelligence Platform",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit page refresh every 5 minutes.
# scheduler.py separately updates latest_results.csv every 5 minutes.
st_autorefresh(interval=300000, key="election_dashboard_refresh")


# ============================================================
# PARTY COLOR MAP
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
    "IUNL": "#0EA5E9",
    "IUML": "#0EA5E9",
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
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.16), transparent 28%),
            radial-gradient(circle at top right, rgba(249, 115, 22, 0.13), transparent 25%),
            #070b14;
        color: #f8fafc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1480px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    .hero {
        padding: 1.4rem 1.8rem;
        border-radius: 28px;
        background:
            linear-gradient(135deg, rgba(37, 99, 235, 0.26), rgba(15, 23, 42, 0.94)),
            linear-gradient(45deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(148, 163, 184, 0.20);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
        margin-bottom: 1.3rem;
    }

    .hero-title {
        font-size: 2.45rem;
        line-height: 1.05;
        font-weight: 900;
        letter-spacing: -0.055em;
        color: #ffffff;
        margin-bottom: 0.75rem;
    }

    .hero-subtitle {
        color: #cbd5e1;
        font-size: 1.03rem;
        line-height: 1.65;
        max-width: 1000px;
    }

    .pill-row {
        display: flex;
        gap: 0.7rem;
        flex-wrap: wrap;
        margin-top: 1.2rem;
    }

    .pill {
        padding: 0.45rem 0.78rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.78);
        color: #dbeafe;
        border: 1px solid rgba(96, 165, 250, 0.25);
        font-size: 0.85rem;
        font-weight: 750;
    }

    .status-strip {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.9rem;
        margin-bottom: 1.4rem;
    }

    .status-card {
        padding: 0.85rem 0.9rem;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.84);
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 14px 38px rgba(0, 0, 0, 0.18);
        min-height: 78px;
    }

    .status-label {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .status-value {
        color: #ffffff;
        font-size: 1.02rem;
        font-weight: 850;
        line-height: 1.25;
        word-break: break-word;
    }

    .section-title {
        font-size: 1.55rem;
        font-weight: 900;
        color: #f8fafc;
        margin-top: 0.8rem;
        margin-bottom: 0.9rem;
        letter-spacing: -0.025em;
    }

    .note-box {
        padding: 0.95rem 1.05rem;
        background: rgba(37, 99, 235, 0.11);
        border: 1px solid rgba(96, 165, 250, 0.22);
        border-radius: 18px;
        color: #dbeafe;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 1rem;
    }

    .warn-box {
        padding: 0.95rem 1.05rem;
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.28);
        border-radius: 18px;
        color: #fde68a;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 1rem;
    }

    .metric-box {
        padding: 0.95rem 1rem;
        border-radius: 22px;
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 14px 38px rgba(0, 0, 0, 0.18);
        height: 100%;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.86rem;
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 900;
        letter-spacing: -0.045em;
    }

    .metric-sub {
        color: #94a3b8;
        font-size: 0.78rem;
        margin-top: 0.25rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.55rem;
        background: rgba(15, 23, 42, 0.62);
        border-radius: 20px;
        padding: 0.45rem;
        border: 1px solid rgba(148, 163, 184, 0.16);
        margin-bottom: 1.1rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 46px;
        border-radius: 15px;
        padding: 0 1.15rem;
        color: #cbd5e1;
        font-weight: 800;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.14);
    }

    .stButton > button {
        border-radius: 16px;
        border: 1px solid rgba(96, 165, 250, 0.45);
        background: linear-gradient(135deg, #2563eb, #1e40af);
        color: white;
        font-weight: 850;
        padding: 0.68rem 1.1rem;
        box-shadow: 0 12px 32px rgba(37, 99, 235, 0.24);
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
        padding-top: 2rem;
    }

    @media (max-width: 900px) {
        .status-strip {
            grid-template-columns: repeat(1, minmax(0, 1fr));
        }

        .hero-title {
            font-size: 2.1rem;
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
    html = (
        f'<div class="metric-box">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{subtext}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_status_card(label, value):
    return (
        f'<div class="status-card">'
        f'<div class="status-label">{label}</div>'
        f'<div class="status-value">{value}</div>'
        f'</div>'
    )


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
        margin=dict(l=10, r=10, t=58, b=30),
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
        others_row = pd.DataFrame(
            [{party_col: "Others", value_col: others[value_col].sum()}]
        )
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
    df = load_party_results()
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
<b>Source:</b> ECI Automated Feed<br>
<b>Refresh Cycle:</b> 5 minutes<br>
<b>Last Synced:</b> {latest_sync}<br>
<b>Mode:</b> Party Trend Analytics
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

    with st.expander("Manual Override"):
        st.caption("Use only if automated ingestion fails or for testing a custom CSV.")
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
        st.caption(
            "Major parties use fixed colors. Smaller or less common parties use fallback colors for readability."
        )


# ============================================================
# DERIVED DATA
# ============================================================

all_parties = sorted(df["party"].dropna().unique().tolist())
color_map = get_color_map(all_parties + ["Others"])

party_summary = get_party_summary(filtered_df)
state_summary = get_state_summary(filtered_df)
vote_share_df = get_vote_share(filtered_df)

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
        Automated election trend ingestion, party-wise analytics, state-level monitoring,
        close-trend detection, and AI-assisted summaries built as a data engineering portfolio project.
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
    f'{render_status_card("Total Seat Trends", total_trend_count)}'
    f'{render_status_card("Last Synced", latest_update)}'
    '</div>'
)

st.markdown(status_html, unsafe_allow_html=True)

st.markdown(
    """
<div class="note-box">
This dashboard tracks party-wise live trends from ECI result pages.
Values represent seat trend counts, not vote counts. Final certified results should be verified from official ECI reports.
</div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4 = st.columns(4)

with k1:
    render_metric("Reporting Rows", total_rows, "Party-state rows after filters")

with k2:
    render_metric("Seat Trends", total_trend_count, "Total seats represented in trend feed")

with k3:
    render_metric("Leading Count", leading_count, "Seat trends currently marked leading")

with k4:
    render_metric("Won Count", won_count, "Seat trends marked won")


# ============================================================
# TABS
# ============================================================

overview_tab, state_tab, close_tab, party_tab, ai_tab, raw_tab = st.tabs(
    [
        "Overview",
        "State Monitor",
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

    left, right = st.columns([1.35, 1])

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
            fig = plotly_layout(fig, height=480)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No party trend data available.")

    with right:
        if not top_party_df.empty:
            fig_donut = px.pie(
                top_party_df,
                names="party",
                values="votes",
                hole=0.58,
                color="party",
                color_discrete_map=color_map,
                title="Trend Share: Top Parties + Others",
            )

            fig_donut.update_traces(
                textposition="inside",
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Seat Trends: %{value}<br>Share: %{percent}<extra></extra>",
            )

            fig_donut = plotly_layout(fig_donut, height=480)
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
        safe_dataframe(share_table, height=360)

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

    safe_dataframe(state_display, height=310)


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

        fig_state = plotly_layout(fig_state, height=540)
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

        safe_dataframe(state_detail, height=480)
    else:
        st.info("No state-level data available.")


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
In party-trend mode, this section does not represent candidate victory margins.
It highlights smaller party trend counts and low-volume competitive signals.
Candidate-level close contests will be added after constituency-wise scraping is implemented.
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
            "States with low-volume trend rows",
        )

    with c3:
        render_metric(
            "Parties Affected",
            low_trend_df["party"].nunique() if not low_trend_df.empty else 0,
            "Parties in low-volume trend rows",
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

        fig_low = plotly_layout(fig_low, height=560)
        st.plotly_chart(fig_low, use_container_width=True)

        safe_dataframe(prepare_display_df(low_trend_df), height=440)
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

        c1, c2 = st.columns([1.1, 1])

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

            fig_lead = plotly_layout(fig_lead, height=520)
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
            fig_rank = plotly_layout(fig_rank, height=520)
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

        safe_dataframe(party_table, height=460)

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

        fig_dist = plotly_layout(fig_dist, height=520)
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
It should be treated as an explanatory layer, not as a prediction engine or official result source.
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
        leading/won status, and top-party movement. Candidate-level constituency margins
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

    st.markdown(
        """
<div class="note-box">
This is the cleaned dataset powering the dashboard. The automated scraper overwrites this data on each scheduled refresh.
</div>
        """,
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