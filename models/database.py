"""Database models and connection management."""

from datetime import date, datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    Boolean, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config.settings import settings

Base = declarative_base()


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, unique=True, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=True)
    venue = Column(String(256), nullable=True)
    city = Column(String(128), nullable=True)
    team1 = Column(String(128), nullable=False)
    team2 = Column(String(128), nullable=False)
    toss_winner = Column(String(128), nullable=True)
    toss_decision = Column(String(16), nullable=True)
    winner = Column(String(128), nullable=True)
    result = Column(String(32), nullable=True)
    result_margin = Column(Float, nullable=True)
    player_of_match = Column(String(128), nullable=True)
    umpire1 = Column(String(128), nullable=True)
    umpire2 = Column(String(128), nullable=True)
    match_type = Column(String(32), default="League")
    dl_applied = Column(Boolean, default=False)

    # Relationships
    deliveries = relationship("Delivery", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_match_season_teams", "season", "team1", "team2"),
    )


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.match_id"), nullable=False, index=True)
    inning = Column(Integer, nullable=False)
    over = Column(Integer, nullable=False)
    ball = Column(Integer, nullable=False)
    batter = Column(String(128), nullable=False)
    bowler = Column(String(128), nullable=False)
    non_striker = Column(String(128), nullable=True)
    batsman_runs = Column(Integer, default=0)
    extra_runs = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    extras_type = Column(String(32), nullable=True)
    is_wicket = Column(Boolean, default=False)
    dismissal_kind = Column(String(64), nullable=True)
    player_dismissed = Column(String(128), nullable=True)
    fielder = Column(String(128), nullable=True)

    match = relationship("Match", back_populates="deliveries")

    __table_args__ = (
        Index("idx_delivery_match_inning", "match_id", "inning"),
        Index("idx_delivery_batter", "batter"),
        Index("idx_delivery_bowler", "bowler"),
    )


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    normalized_name = Column(String(128), nullable=True, unique=True)
    role = Column(String(32), nullable=True)  # batsman, bowler, all-rounder, wicket-keeper
    batting_style = Column(String(64), nullable=True)
    bowling_style = Column(String(64), nullable=True)
    nationality = Column(String(64), nullable=True)
    current_team = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True)
    city = Column(String(128), nullable=True)
    country = Column(String(64), default="India")
    pitch_type = Column(String(32), nullable=True)  # batting, bowling, balanced
    avg_first_innings_score = Column(Float, nullable=True)
    avg_second_innings_score = Column(Float, nullable=True)
    chase_win_pct = Column(Float, nullable=True)
    boundary_size = Column(String(32), nullable=True)
    pace_advantage = Column(Float, nullable=True)
    spin_advantage = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String(128), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    matches = Column(Integer, default=0)
    runs_scored = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    batting_avg = Column(Float, nullable=True)
    strike_rate = Column(Float, nullable=True)
    fifties = Column(Integer, default=0)
    hundreds = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    wickets = Column(Integer, default=0)
    balls_bowled = Column(Integer, default=0)
    runs_conceded = Column(Integer, default=0)
    bowling_avg = Column(Float, nullable=True)
    economy = Column(Float, nullable=True)
    bowling_sr = Column(Float, nullable=True)
    catches = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("player_name", "season", name="uq_player_season"),
    )


class TeamStats(Base):
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team = Column(String(128), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    no_results = Column(Integer, default=0)
    win_pct = Column(Float, nullable=True)
    avg_score = Column(Float, nullable=True)
    avg_score_conceded = Column(Float, nullable=True)
    powerplay_avg = Column(Float, nullable=True)
    death_overs_avg = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("team", "season", name="uq_team_season"),
    )


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.match_id"), nullable=True)
    city = Column(String(128), nullable=False)
    date = Column(Date, nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    dew_probability = Column(Float, nullable=True)
    rain_probability = Column(Float, nullable=True)
    condition = Column(String(64), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=True)
    team1 = Column(String(128), nullable=False)
    team2 = Column(String(128), nullable=False)
    venue = Column(String(256), nullable=True)
    team1_win_prob = Column(Float, nullable=False)
    team2_win_prob = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    predicted_winner = Column(String(128), nullable=True)
    actual_winner = Column(String(128), nullable=True)
    model_version = Column(String(64), nullable=True)
    key_factors = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database engine and session
def get_engine(url: str = None):
    db_url = url or settings.database_url
    return create_engine(db_url, echo=False)


def create_tables(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
