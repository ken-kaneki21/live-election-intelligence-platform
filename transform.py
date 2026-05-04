import os
import pandas as pd


REQUIRED_COLUMNS = [
    "state",
    "constituency",
    "candidate",
    "party",
    "votes",
    "status",
    "margin",
    "last_updated",
]


def clean_results_df(df):
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df[REQUIRED_COLUMNS].copy()

    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["margin"] = pd.to_numeric(df["margin"], errors="coerce").fillna(0).astype(int)
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")

    text_cols = ["state", "constituency", "candidate", "party", "status"]

    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df


def load_results():
    processed_path = "data/processed/latest_results.csv"
    sample_path = "data/sample/election_sample.csv"

    if os.path.exists(processed_path):
        df = pd.read_csv(processed_path)
        return clean_results_df(df)

    df = pd.read_csv(sample_path)
    return clean_results_df(df)


def clean_uploaded_results(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return clean_results_df(df)


def get_party_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["state", "party", "Leading", "Won", "total"])

    summary = (
        df.groupby(["state", "party", "status"])
        .size()
        .reset_index(name="seat_count")
    )

    pivot = summary.pivot_table(
        index=["state", "party"],
        columns="status",
        values="seat_count",
        fill_value=0,
    ).reset_index()

    if "Leading" not in pivot.columns:
        pivot["Leading"] = 0

    if "Won" not in pivot.columns:
        pivot["Won"] = 0

    pivot["total"] = pivot["Leading"] + pivot["Won"]

    return pivot.sort_values(["state", "total"], ascending=[True, False])


def get_close_contests(df, margin_limit=1000):
    if df.empty:
        return df

    return df[df["margin"] <= margin_limit].sort_values("margin")


def get_state_summary(df):
    if df.empty:
        return pd.DataFrame(
            columns=["state", "total_constituencies", "total_parties", "last_updated"]
        )

    return (
        df.groupby("state")
        .agg(
            total_constituencies=("constituency", "nunique"),
            total_parties=("party", "nunique"),
            last_updated=("last_updated", "max"),
        )
        .reset_index()
    )


def get_vote_share(df):
    if df.empty:
        return pd.DataFrame(columns=["party", "votes", "vote_share"])

    vote_df = (
        df.groupby("party")["votes"]
        .sum()
        .reset_index()
        .sort_values("votes", ascending=False)
    )

    total_votes = vote_df["votes"].sum()

    if total_votes == 0:
        vote_df["vote_share"] = 0
    else:
        vote_df["vote_share"] = (vote_df["votes"] / total_votes) * 100

    return vote_df