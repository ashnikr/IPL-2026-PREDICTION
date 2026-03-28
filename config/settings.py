"""Central configuration for the IPL Prediction System."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    cache_dir: Path = BASE_DIR / "data" / "cache"
    model_dir: Path = BASE_DIR / "models" / "trained"
    log_dir: Path = BASE_DIR / "logs"

    # Database
    database_url: str = Field(
        default="sqlite:///data/ipl.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # API Keys
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    weather_api_key: str = Field(default="", alias="WEATHER_API_KEY")

    # IPL Config
    ipl_seasons: list[int] = list(range(2008, 2027))
    current_season: int = 2026

    # Team name mappings (historical -> current)
    team_name_map: dict[str, str] = {
        "Delhi Daredevils": "Delhi Capitals",
        "Deccan Chargers": "Sunrisers Hyderabad",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiant": "Rising Pune Supergiants",
        "Rising Pune Supergiants": "Rising Pune Supergiants",
        "Pune Warriors": "Pune Warriors India",
        "Gujarat Lions": "Gujarat Lions",
    }

    current_teams: list[str] = [
        "Chennai Super Kings",
        "Mumbai Indians",
        "Royal Challengers Bengaluru",
        "Kolkata Knight Riders",
        "Sunrisers Hyderabad",
        "Rajasthan Royals",
        "Delhi Capitals",
        "Punjab Kings",
        "Lucknow Super Giants",
        "Gujarat Titans",
    ]

    # Model config
    random_state: int = 42
    test_size: float = 0.2
    n_monte_carlo_sims: int = 10000

    # Scraping
    request_timeout: int = 30
    scrape_delay: float = 2.0

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# Ensure directories exist
for dir_path in [
    settings.data_dir,
    settings.raw_data_dir,
    settings.processed_data_dir,
    settings.cache_dir,
    settings.model_dir,
    settings.log_dir,
]:
    dir_path.mkdir(parents=True, exist_ok=True)
