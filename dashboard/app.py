"""
IPL Match Prediction Dashboard.

Streamlit-based interactive dashboard showing:
  - Match predictions with probabilities
  - Team strength rankings
  - Player form analysis
  - Venue statistics
  - Head-to-head records
  - Model performance
"""

import sys
sys.path.insert(0, ".")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from config.settings import settings
from models.ensemble import EnsemblePrediction
from models.bayesian_model import BayesianPredictor
from models.daily_predictor import DailyPredictor

# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="IPL Match Prediction AI",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏏 IPL Match Prediction AI")
st.markdown("*AI-powered predictions using ensemble ML, Bayesian inference & Monte Carlo simulation*")


# ── Cached Loaders ───────────────────────────────────────────────────

@st.cache_resource
def load_ensemble():
    ens = EnsemblePrediction()
    ens.load_all_models()
    return ens


@st.cache_data
def load_matches():
    path = settings.processed_data_dir / "matches_processed.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_player_stats():
    path = settings.processed_data_dir / "player_stats.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


# ── Sidebar ──────────────────────────────────────────────────────────

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Match Prediction", "Team Rankings", "Head to Head", "Venue Analysis",
     "Player Stats", "Season Overview"],
)

# Load data
ensemble = load_ensemble()
matches = load_matches()
player_stats = load_player_stats()


# ── Page: Match Prediction ───────────────────────────────────────────

if page == "Match Prediction":
    st.header("Match Prediction")

    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("Team 1", settings.current_teams, index=0)
    with col2:
        team2 = st.selectbox("Team 2", settings.current_teams, index=1)

    col3, col4 = st.columns(2)
    with col3:
        venues = matches["venue"].dropna().unique().tolist() if not matches.empty else ["Unknown"]
        venue = st.selectbox("Venue", ["Auto-detect"] + sorted(venues))
    with col4:
        toss_winner = st.selectbox("Toss Winner", ["Unknown", team1, team2])
        toss_decision = st.selectbox("Toss Decision", ["Unknown", "bat", "field"])

    if st.button("Predict Match", type="primary", use_container_width=True):
        if team1 == team2:
            st.error("Please select two different teams!")
        else:
            with st.spinner("Running prediction models..."):
                pred = ensemble.predict_match(
                    team1=team1,
                    team2=team2,
                    venue=venue if venue != "Auto-detect" else None,
                    toss_winner=toss_winner if toss_winner != "Unknown" else None,
                    toss_decision=toss_decision if toss_decision != "Unknown" else None,
                )

            # Display results
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(team1, f"{pred['team1_win_prob']*100:.1f}%")
            with c2:
                st.metric(team2, f"{pred['team2_win_prob']*100:.1f}%")
            with c3:
                st.metric("Confidence", f"{pred['confidence']*100:.1f}%")

            st.success(f"**Predicted Winner: {pred['predicted_winner']}**")

            # Probability bar
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=["Prediction"],
                x=[pred["team1_win_prob"] * 100],
                name=team1,
                orientation="h",
                marker_color="#1f77b4",
                text=f"{pred['team1_win_prob']*100:.1f}%",
                textposition="inside",
            ))
            fig.add_trace(go.Bar(
                y=["Prediction"],
                x=[pred["team2_win_prob"] * 100],
                name=team2,
                orientation="h",
                marker_color="#ff7f0e",
                text=f"{pred['team2_win_prob']*100:.1f}%",
                textposition="inside",
            ))
            fig.update_layout(barmode="stack", height=120, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

            # Model-wise predictions
            st.subheader("Model-wise Predictions")
            model_df = pd.DataFrame([
                {"Model": k, f"{team1} Win %": v * 100, f"{team2} Win %": (1 - v) * 100}
                for k, v in pred["model_predictions"].items()
            ])
            st.dataframe(model_df, use_container_width=True, hide_index=True)

            # Key factors
            st.subheader("Key Factors")
            for f in pred.get("key_factors", []):
                st.markdown(f"- {f}")


# ── Page: Team Rankings ──────────────────────────────────────────────

elif page == "Team Rankings":
    st.header("Bayesian Team Strength Rankings")

    if ensemble.bayesian.team_strengths:
        strengths = ensemble.bayesian.team_strengths
        ranking_data = sorted(
            [
                {
                    "Team": team,
                    "Strength": stats.get("mean_strength", 0.5),
                    "Wins": stats.get("wins", 0),
                    "Losses": stats.get("losses", 0),
                    "Win Rate": stats.get("wins", 0) / max(stats.get("wins", 0) + stats.get("losses", 0), 1),
                }
                for team, stats in strengths.items()
            ],
            key=lambda x: x["Strength"],
            reverse=True,
        )
        df = pd.DataFrame(ranking_data)
        df.index = range(1, len(df) + 1)
        df.index.name = "Rank"

        st.dataframe(df, use_container_width=True)

        # Chart
        fig = px.bar(
            df, x="Team", y="Strength",
            color="Win Rate", color_continuous_scale="RdYlGn",
            title="Team Strength (Bayesian)",
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No team strength data available. Run training first.")


# ── Page: Head to Head ───────────────────────────────────────────────

elif page == "Head to Head":
    st.header("Head-to-Head Records")

    if not matches.empty:
        c1, c2 = st.columns(2)
        with c1:
            h2h_team1 = st.selectbox("Team A", settings.current_teams, key="h2h1")
        with c2:
            h2h_team2 = st.selectbox("Team B", settings.current_teams, index=1, key="h2h2")

        h2h = matches[
            ((matches["team1"] == h2h_team1) & (matches["team2"] == h2h_team2)) |
            ((matches["team1"] == h2h_team2) & (matches["team2"] == h2h_team1))
        ]

        if not h2h.empty:
            t1_wins = len(h2h[h2h["winner"] == h2h_team1])
            t2_wins = len(h2h[h2h["winner"] == h2h_team2])
            nr = len(h2h) - t1_wins - t2_wins

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Matches", len(h2h))
            c2.metric(f"{h2h_team1} Wins", t1_wins)
            c3.metric(f"{h2h_team2} Wins", t2_wins)
            c4.metric("No Result", nr)

            fig = px.pie(
                names=[h2h_team1, h2h_team2, "No Result"],
                values=[t1_wins, t2_wins, nr],
                title=f"{h2h_team1} vs {h2h_team2}",
                color_discrete_sequence=["#1f77b4", "#ff7f0e", "#999999"],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No head-to-head matches found.")
    else:
        st.warning("No match data loaded.")


# ── Page: Venue Analysis ─────────────────────────────────────────────

elif page == "Venue Analysis":
    st.header("Venue Analysis")

    if not matches.empty:
        venues = matches["venue"].dropna().value_counts()
        top_venues = venues.head(20).index.tolist()
        selected_venue = st.selectbox("Select Venue", top_venues)

        vm = matches[matches["venue"] == selected_venue]

        c1, c2, c3 = st.columns(3)
        c1.metric("Matches Played", len(vm))

        if "inn1_total_runs" in vm.columns:
            avg_score = vm["inn1_total_runs"].mean()
            c2.metric("Avg 1st Innings Score", f"{avg_score:.0f}")

        # Win batting/fielding first
        bat_first_wins = 0
        for _, row in vm.iterrows():
            if pd.notna(row.get("winner")) and pd.notna(row.get("toss_decision")):
                if row["toss_decision"] == "bat" and row.get("toss_winner") == row.get("winner"):
                    bat_first_wins += 1
                elif row["toss_decision"] == "field" and row.get("toss_winner") != row.get("winner"):
                    bat_first_wins += 1
        chase_wins = len(vm[vm["winner"].notna()]) - bat_first_wins
        c3.metric("Chase Win %", f"{chase_wins / max(len(vm[vm['winner'].notna()]), 1) * 100:.0f}%")

        # Score distribution
        if "inn1_total_runs" in vm.columns:
            fig = px.histogram(
                vm, x="inn1_total_runs", nbins=20,
                title=f"Score Distribution at {selected_venue}",
                labels={"inn1_total_runs": "1st Innings Total"},
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Page: Player Stats ───────────────────────────────────────────────

elif page == "Player Stats":
    st.header("Player Statistics")

    if not player_stats.empty:
        # Top batsmen
        st.subheader("Top Run Scorers (Career)")
        top_bat = player_stats.groupby("player_name").agg(
            total_runs=("runs_scored", "sum"),
            avg_sr=("strike_rate", "mean"),
            seasons=("season", "nunique"),
        ).sort_values("total_runs", ascending=False).head(20).reset_index()
        st.dataframe(top_bat, use_container_width=True, hide_index=True)

        # Top bowlers
        st.subheader("Top Wicket Takers (Career)")
        top_bowl = player_stats.groupby("player_name").agg(
            total_wickets=("wickets", "sum"),
            avg_economy=("economy", "mean"),
            seasons=("season", "nunique"),
        ).sort_values("total_wickets", ascending=False).head(20).reset_index()
        top_bowl = top_bowl[top_bowl["total_wickets"] > 0]
        st.dataframe(top_bowl, use_container_width=True, hide_index=True)
    else:
        st.warning("No player stats available.")


# ── Page: Season Overview ────────────────────────────────────────────

elif page == "Season Overview":
    st.header("Season Overview")

    if not matches.empty and "season" in matches.columns:
        selected_season = st.selectbox("Season", sorted(matches["season"].unique(), reverse=True))
        sm = matches[matches["season"] == selected_season]

        st.metric("Matches in Season", len(sm))

        # Wins per team
        if "winner" in sm.columns:
            wins = sm["winner"].dropna().value_counts().reset_index()
            wins.columns = ["Team", "Wins"]

            fig = px.bar(wins, x="Team", y="Wins", title=f"Wins per Team - IPL {selected_season}",
                         color="Wins", color_continuous_scale="Blues")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        # Matches per venue
        venue_counts = sm["venue"].value_counts().head(10).reset_index()
        venue_counts.columns = ["Venue", "Matches"]
        fig2 = px.bar(venue_counts, x="Venue", y="Matches", title=f"Matches per Venue - {selected_season}")
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)


# ── Footer ───────────────────────────────────────────────────────────

st.markdown("---")
st.caption(f"IPL Match Prediction AI v2.0 | Data: 2008-2024 | Generated: {date.today()}")
