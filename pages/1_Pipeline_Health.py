import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from azure_data_loader import (
    load_party_results,
    load_candidate_results,
    load_candidate_coverage_report,
)

PARTY_DATA_PATH = "data/processed/latest_results.csv"
CANDIDATE_DATA_PATH = "data/processed/latest_candidate_results.csv"
DISCOVERY_DATA_PATH = "data/raw/eci_state_constituency_discovery.csv"


st.set_page_config(
    page_title="Pipeline Health",
    page_icon="PH",
    layout="wide",
)


st.markdown(
    """
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.15), transparent 30%),
            radial-gradient(circle at top right, rgba(249, 115, 22, 0.12), transparent 28%),
            linear-gradient(180deg, #070b14 0%, #08111f 50%, #070b14 100%);
        color: #f8fafc;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    .hero {
        padding: 1.1rem 1.4rem;
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(37, 99, 235, 0.26), rgba(15, 23, 42, 0.96)),
            linear-gradient(45deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(148, 163, 184, 0.20);
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.30);
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: -0.045em;
        margin-bottom: 0.35rem;
    }

    .hero-subtitle {
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.55;
    }

    .metric-card {
        padding: 0.9rem 1rem;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.16);
        min-height: 105px;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        color: #ffffff;
        font-size: 1.55rem;
        font-weight: 900;
        letter-spacing: -0.035em;
        word-break: break-word;
    }

    .metric-sub {
        color: #94a3b8;
        font-size: 0.76rem;
        margin-top: 0.25rem;
        line-height: 1.4;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 900;
        color: #f8fafc;
        margin-top: 1rem;
        margin-bottom: 0.7rem;
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
        margin-bottom: 0.9rem;
    }

    .warn-box {
        padding: 0.8rem 0.95rem;
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.28);
        border-radius: 16px;
        color: #fde68a;
        font-size: 0.88rem;
        line-height: 1.5;
        margin-bottom: 0.9rem;
    }

    .good-box {
        padding: 0.8rem 0.95rem;
        background: rgba(34, 197, 94, 0.10);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 16px;
        color: #bbf7d0;
        font-size: 0.88rem;
        line-height: 1.5;
        margin-bottom: 0.9rem;
    }
</style>
    """,
    unsafe_allow_html=True,
)


def file_exists(path):
    return os.path.exists(path)


def file_modified_time(path):
    if not os.path.exists(path):
        return "Missing"

    modified_timestamp = os.path.getmtime(path)
    return datetime.fromtimestamp(modified_timestamp).strftime("%d %b %Y, %I:%M %p")


def file_age_minutes(path):
    if not os.path.exists(path):
        return None

    modified_timestamp = os.path.getmtime(path)
    age_seconds = datetime.now().timestamp() - modified_timestamp
    return round(age_seconds / 60, 1)


def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def render_metric(label, value, subtext=""):
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">{label}</div>
    <div class="metric-value">{value}</div>
    <div class="metric-sub">{subtext}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def status_label(condition):
    return "Healthy" if condition else "Needs Attention"


def status_box(message, status="good"):
    if status == "good":
        class_name = "good-box"
    elif status == "warn":
        class_name = "warn-box"
    else:
        class_name = "note-box"

    st.markdown(
        f"""
<div class="{class_name}">
{message}
</div>
        """,
        unsafe_allow_html=True,
    )


def get_party_quality_checks(df):
    checks = []

    if df.empty:
        return pd.DataFrame(
            [
                {
                    "Check": "Party dataset loaded",
                    "Status": "Failed",
                    "Details": "latest_results.csv is missing or empty.",
                }
            ]
        )

    required_cols = [
        "state",
        "constituency",
        "candidate",
        "party",
        "votes",
        "status",
        "margin",
        "last_updated",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    checks.append(
        {
            "Check": "Required columns present",
            "Status": "Passed" if not missing_cols else "Failed",
            "Details": "All required columns found." if not missing_cols else f"Missing: {missing_cols}",
        }
    )

    duplicate_count = df.duplicated().sum()

    checks.append(
        {
            "Check": "Duplicate rows",
            "Status": "Passed" if duplicate_count == 0 else "Warning",
            "Details": f"{duplicate_count} duplicate rows found.",
        }
    )

    null_party_count = df["party"].isna().sum() if "party" in df.columns else len(df)

    checks.append(
        {
            "Check": "Party values populated",
            "Status": "Passed" if null_party_count == 0 else "Warning",
            "Details": f"{null_party_count} missing party values.",
        }
    )

    negative_votes = 0

    if "votes" in df.columns:
        votes = pd.to_numeric(df["votes"], errors="coerce").fillna(0)
        negative_votes = int((votes < 0).sum())

    checks.append(
        {
            "Check": "Seat trend values valid",
            "Status": "Passed" if negative_votes == 0 else "Failed",
            "Details": f"{negative_votes} negative vote/trend values found.",
        }
    )

    return pd.DataFrame(checks)


def get_candidate_quality_checks(df):
    checks = []

    if df.empty:
        return pd.DataFrame(
            [
                {
                    "Check": "Candidate dataset loaded",
                    "Status": "Failed",
                    "Details": "latest_candidate_results.csv is missing or empty.",
                }
            ]
        )

    required_cols = [
        "constituency",
        "constituency_no",
        "candidate",
        "party",
        "votes",
        "vote_rank",
        "derived_status",
        "vote_margin",
        "runner_up_votes",
        "eci_code",
        "source_url",
        "scraped_at",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    checks.append(
        {
            "Check": "Required columns present",
            "Status": "Passed" if not missing_cols else "Failed",
            "Details": "All required columns found." if not missing_cols else f"Missing: {missing_cols}",
        }
    )

    duplicate_keys = 0

    if all(col in df.columns for col in ["constituency", "candidate", "party"]):
        duplicate_keys = df.duplicated(
            subset=["constituency", "candidate", "party"]
        ).sum()

    checks.append(
        {
            "Check": "Duplicate candidate keys",
            "Status": "Passed" if duplicate_keys == 0 else "Warning",
            "Details": f"{duplicate_keys} duplicate candidate keys found.",
        }
    )

    if "vote_rank" in df.columns and "constituency" in df.columns:
        top_rank_count = df[df["vote_rank"] == 1].groupby("constituency").size()
        bad_top_rank = int((top_rank_count != 1).sum())
    else:
        bad_top_rank = len(df)

    checks.append(
        {
            "Check": "One top candidate per constituency",
            "Status": "Passed" if bad_top_rank == 0 else "Warning",
            "Details": f"{bad_top_rank} constituencies do not have exactly one rank-1 candidate.",
        }
    )

    negative_votes = 0

    if "votes" in df.columns:
        votes = pd.to_numeric(df["votes"], errors="coerce").fillna(0)
        negative_votes = int((votes < 0).sum())

    checks.append(
        {
            "Check": "Candidate vote values valid",
            "Status": "Passed" if negative_votes == 0 else "Failed",
            "Details": f"{negative_votes} negative vote values found.",
        }
    )

    if "vote_margin" in df.columns:
        margin = pd.to_numeric(df["vote_margin"], errors="coerce").fillna(0)
        negative_margin = int((margin < 0).sum())
    else:
        negative_margin = len(df)

    checks.append(
        {
            "Check": "Vote margin values valid",
            "Status": "Passed" if negative_margin == 0 else "Warning",
            "Details": f"{negative_margin} negative margin values found.",
        }
    )

    return pd.DataFrame(checks)


def plotly_layout(fig, height=420):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.56)",
        font=dict(color="#e5e7eb", size=13),
        margin=dict(l=10, r=10, t=52, b=28),
        height=height,
    )
    return fig


party_df = load_party_results()
candidate_df = load_candidate_results()
coverage_df = load_candidate_coverage_report()
discovery_df = load_csv(DISCOVERY_DATA_PATH)


st.markdown(
    """
<div class="hero">
    <div class="hero-title">Pipeline Health Monitor</div>
    <div class="hero-subtitle">
        Data freshness, file availability, coverage checks, and quality validation for the Election Intelligence Platform.
    </div>
</div>
    """,
    unsafe_allow_html=True,
)


party_file_ok = file_exists(PARTY_DATA_PATH) and not party_df.empty
candidate_file_ok = file_exists(CANDIDATE_DATA_PATH) and not candidate_df.empty
discovery_file_ok = file_exists(DISCOVERY_DATA_PATH) and not discovery_df.empty

overall_healthy = party_file_ok and candidate_file_ok


if overall_healthy:
    status_box(
        "Pipeline health is good. Party-level and candidate-level processed datasets are available.",
        status="good",
    )
else:
    status_box(
        "Pipeline needs attention. One or more processed datasets are missing or empty.",
        status="warn",
    )


m1, m2, m3, m4 = st.columns(4)

with m1:
    render_metric(
        "Party Dataset",
        status_label(party_file_ok),
        f"Modified: {file_modified_time(PARTY_DATA_PATH)}",
    )

with m2:
    render_metric(
        "Candidate Dataset",
        status_label(candidate_file_ok),
        f"Modified: {file_modified_time(CANDIDATE_DATA_PATH)}",
    )

with m3:
    render_metric(
        "Party Rows",
        len(party_df),
        "Rows in latest_results.csv",
    )

with m4:
    render_metric(
        "Candidate Rows",
        len(candidate_df),
        "Rows in latest_candidate_results.csv",
    )


st.markdown('<div class="section-title">Coverage Summary</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

party_states = party_df["state"].nunique() if "state" in party_df.columns and not party_df.empty else 0
party_count = party_df["party"].nunique() if "party" in party_df.columns and not party_df.empty else 0
candidate_constituencies = candidate_df["constituency"].nunique() if "constituency" in candidate_df.columns and not candidate_df.empty else 0
candidate_parties = candidate_df["party"].nunique() if "party" in candidate_df.columns and not candidate_df.empty else 0

with c1:
    render_metric("Party States Covered", party_states, "Party-level configured states")

with c2:
    render_metric("Party Count", party_count, "Parties in party-level feed")

with c3:
    render_metric("Candidate Constituencies", candidate_constituencies, "Candidate-level constituency coverage")

with c4:
    render_metric("Candidate Parties", candidate_parties, "Parties in candidate-level feed")


st.markdown(
    """
<div class="warn-box">
Candidate-level constituency coverage is currently Tamil Nadu only because the active ECI result path exposes S22 constituency pages.
Party-level trend monitoring covers the configured states: Assam, Kerala, Tamil Nadu, West Bengal, and Puducherry.
</div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="section-title">Data Quality Checks</div>', unsafe_allow_html=True)

party_checks = get_party_quality_checks(party_df)
candidate_checks = get_candidate_quality_checks(candidate_df)

q1, q2 = st.columns(2)

with q1:
    st.markdown("#### Party-Level Dataset Checks")
    st.dataframe(party_checks, use_container_width=True, hide_index=True, height=250)

with q2:
    st.markdown("#### Candidate-Level Dataset Checks")
    st.dataframe(candidate_checks, use_container_width=True, hide_index=True, height=250)


st.markdown('<div class="section-title">Pipeline Freshness</div>', unsafe_allow_html=True)

freshness_rows = [
    {
        "Dataset": "Party Trend Layer",
        "Path": PARTY_DATA_PATH,
        "Exists": file_exists(PARTY_DATA_PATH),
        "Rows": len(party_df),
        "Last Modified": file_modified_time(PARTY_DATA_PATH),
        "Age Minutes": file_age_minutes(PARTY_DATA_PATH),
    },
    {
        "Dataset": "Candidate Constituency Layer",
        "Path": CANDIDATE_DATA_PATH,
        "Exists": file_exists(CANDIDATE_DATA_PATH),
        "Rows": len(candidate_df),
        "Last Modified": file_modified_time(CANDIDATE_DATA_PATH),
        "Age Minutes": file_age_minutes(CANDIDATE_DATA_PATH),
    },
    {
        "Dataset": "Discovery Layer",
        "Path": DISCOVERY_DATA_PATH,
        "Exists": file_exists(DISCOVERY_DATA_PATH),
        "Rows": len(discovery_df),
        "Last Modified": file_modified_time(DISCOVERY_DATA_PATH),
        "Age Minutes": file_age_minutes(DISCOVERY_DATA_PATH),
    },
]

freshness_df = pd.DataFrame(freshness_rows)
st.dataframe(freshness_df, use_container_width=True, hide_index=True, height=180)


st.markdown('<div class="section-title">Candidate Coverage Diagnostics</div>', unsafe_allow_html=True)

if not discovery_df.empty and "state_code" in discovery_df.columns:
    discovery_summary = (
        discovery_df.groupby("state_code", as_index=False)
        .agg(
            discovered_constituencies=("eci_code", "count"),
            first_code=("eci_code", "first"),
        )
        .sort_values("state_code")
    )

    fig_discovery = px.bar(
        discovery_summary,
        x="state_code",
        y="discovered_constituencies",
        text="discovered_constituencies",
        title="Discovered Constituency Pages by ECI State Code",
        labels={
            "state_code": "ECI State Code",
            "discovered_constituencies": "Discovered Constituencies",
        },
    )
    fig_discovery.update_traces(textposition="outside", cliponaxis=False)
    fig_discovery = plotly_layout(fig_discovery, height=380)
    st.plotly_chart(fig_discovery, use_container_width=True)

    st.dataframe(discovery_summary, use_container_width=True, hide_index=True)
else:
    st.info("Discovery data is not available yet. Run discover_eci_state_constituencies.py to generate it.")


st.markdown('<div class="section-title">Party-Level State Coverage</div>', unsafe_allow_html=True)

if not party_df.empty and all(col in party_df.columns for col in ["state", "votes"]):
    party_state_summary = (
        party_df.groupby("state", as_index=False)
        .agg(
            rows=("state", "count"),
            seat_trends=("votes", "sum"),
            parties=("party", "nunique"),
        )
        .sort_values("seat_trends", ascending=False)
    )

    fig_party_state = px.bar(
        party_state_summary,
        x="state",
        y="seat_trends",
        text="seat_trends",
        title="Party-Level Seat Trends by State",
        labels={
            "state": "State",
            "seat_trends": "Seat Trend Count",
        },
    )
    fig_party_state.update_traces(textposition="outside", cliponaxis=False)
    fig_party_state = plotly_layout(fig_party_state, height=420)
    st.plotly_chart(fig_party_state, use_container_width=True)

    st.dataframe(party_state_summary, use_container_width=True, hide_index=True)
else:
    st.info("Party-level state coverage data is not available.")


st.markdown('<div class="section-title">Candidate-Level Party Coverage</div>', unsafe_allow_html=True)

if not candidate_df.empty and all(col in candidate_df.columns for col in ["party", "constituency", "vote_rank"]):
    top_candidate_df = candidate_df[candidate_df["vote_rank"] == 1].copy()

    candidate_party_summary = (
        top_candidate_df.groupby("party", as_index=False)
        .agg(
            constituencies_led=("constituency", "count"),
        )
        .sort_values("constituencies_led", ascending=False)
        .head(20)
    )

    fig_candidate_party = px.bar(
        candidate_party_summary,
        x="party",
        y="constituencies_led",
        text="constituencies_led",
        title="Top Candidate Count by Party",
        labels={
            "party": "Party",
            "constituencies_led": "Constituencies Led",
        },
    )
    fig_candidate_party.update_traces(textposition="outside", cliponaxis=False)
    fig_candidate_party = plotly_layout(fig_candidate_party, height=450)
    st.plotly_chart(fig_candidate_party, use_container_width=True)

    st.dataframe(candidate_party_summary, use_container_width=True, hide_index=True)
else:
    st.info("Candidate-level party coverage data is not available.")


st.markdown('<div class="section-title">Recommended Refresh Policy</div>', unsafe_allow_html=True)

policy_df = pd.DataFrame(
    [
        {
            "Layer": "Party Trend Layer",
            "Recommended Refresh": "Every 5 minutes",
            "Reason": "Small summary tables; fast to refresh.",
            "Script": "master_scheduler.py / eci_party_auto_ingest.py",
        },
        {
            "Layer": "Candidate Constituency Layer",
            "Recommended Refresh": "Manual batch / 30-60 minutes",
            "Reason": "Opens constituency pages one by one; heavier and more likely to be rate-limited.",
            "Script": "eci_candidate_auto_ingest_v2.py",
        },
        {
            "Layer": "Discovery Layer",
            "Recommended Refresh": "Manual when ECI page structure changes",
            "Reason": "Used to detect available constituency pages and state codes.",
            "Script": "discover_eci_state_constituencies.py",
        },
    ]
)

st.dataframe(policy_df, use_container_width=True, hide_index=True, height=180)


st.markdown(
    """
<div class="note-box">
This page is designed for pipeline observability. It helps explain data freshness, quality checks,
coverage boundaries, and refresh strategy directly inside the deployed project.
</div>
    """,
    unsafe_allow_html=True,
)