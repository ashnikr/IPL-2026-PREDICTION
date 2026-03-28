"""
ESPNcricinfo Scraper.

Scrapes match data, player profiles, and live scores from Cricinfo.
"""

import time
import json
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

from utils.logger import logger
from config.settings import settings


class CricinfoScraper:
    """Scrape IPL data from ESPNcricinfo."""

    BASE_URL = "https://www.espncricinfo.com"
    STATS_URL = "https://stats.espncricinfo.com/ci/engine/stats/index.html"
    API_URL = "https://hs-consumer-api.espncricinfo.com/v1/pages"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/html",
    }

    IPL_SERIES_IDS = {
        2008: 313494, 2009: 374163, 2010: 418064, 2011: 466304,
        2012: 520932, 2013: 586733, 2014: 695871, 2015: 791129,
        2016: 968923, 2017: 1078425, 2018: 1131611, 2019: 1165643,
        2020: 1210595, 2021: 1249214, 2022: 1298423, 2023: 1345038,
        2024: 1410320, 2025: 1449924, 2026: 1500000,  # placeholder
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.cache_dir = settings.cache_dir / "cricinfo"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, url: str, params: dict = None) -> requests.Response | None:
        """Make a GET request with rate limiting and error handling."""
        try:
            time.sleep(settings.scrape_delay)
            resp = self.session.get(url, params=params, timeout=settings.request_timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None

    def get_season_matches(self, season: int) -> list[dict]:
        """Get all matches for a specific IPL season."""
        series_id = self.IPL_SERIES_IDS.get(season)
        if not series_id:
            logger.warning(f"No series ID for season {season}")
            return []

        cache_file = self.cache_dir / f"matches_{season}.json"
        if cache_file.exists():
            logger.info(f"Loading cached matches for {season}")
            return json.loads(cache_file.read_text())

        url = f"{self.API_URL}/series/home"
        params = {"seriesId": series_id}
        resp = self._get(url, params)

        if resp is None:
            return []

        try:
            data = resp.json()
            matches = []
            for match_group in data.get("content", {}).get("matchGroups", []):
                for match in match_group.get("matches", []):
                    match_info = {
                        "match_id": match.get("objectId"),
                        "title": match.get("title"),
                        "status": match.get("statusText"),
                        "venue": match.get("ground", {}).get("name"),
                        "city": match.get("ground", {}).get("town", {}).get("name"),
                        "date": match.get("startDate"),
                        "team1": match.get("teams", [{}])[0].get("team", {}).get("name"),
                        "team2": match.get("teams", [{}])[1].get("team", {}).get("name") if len(match.get("teams", [])) > 1 else None,
                        "winner": match.get("winnerTeamId"),
                    }
                    matches.append(match_info)

            # Cache results
            cache_file.write_text(json.dumps(matches, indent=2))
            logger.info(f"Scraped {len(matches)} matches for season {season}")
            return matches

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse response for season {season}: {e}")
            return []

    def get_player_stats(self, season: int) -> pd.DataFrame:
        """Get batting and bowling stats for a season."""
        cache_file = self.cache_dir / f"player_stats_{season}.csv"
        if cache_file.exists():
            return pd.read_csv(cache_file)

        # Batting stats
        batting_params = {
            "class": 6,
            "template": "results",
            "type": "batting",
            "series": self.IPL_SERIES_IDS.get(season, 0),
        }
        batting_resp = self._get(self.STATS_URL, batting_params)

        # Bowling stats
        bowling_params = {**batting_params, "type": "bowling"}
        bowling_resp = self._get(self.STATS_URL, bowling_params)

        stats = []

        if batting_resp:
            try:
                soup = BeautifulSoup(batting_resp.text, "lxml")
                table = soup.find("table", {"class": "engineTable"})
                if table:
                    rows = table.find_all("tr", {"class": "data1"})
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 8:
                            stats.append({
                                "player": cols[0].get_text(strip=True),
                                "matches": cols[1].get_text(strip=True),
                                "innings": cols[2].get_text(strip=True),
                                "runs": cols[5].get_text(strip=True),
                                "batting_avg": cols[7].get_text(strip=True),
                                "strike_rate": cols[9].get_text(strip=True) if len(cols) > 9 else None,
                                "season": season,
                            })
            except Exception as e:
                logger.warning(f"Failed to parse batting stats for {season}: {e}")

        df = pd.DataFrame(stats) if stats else pd.DataFrame()
        if not df.empty:
            df.to_csv(cache_file, index=False)

        return df

    def get_live_scores(self) -> list[dict]:
        """Get current live IPL match scores."""
        url = f"{self.API_URL}/matches/live"
        params = {"lang": "en", "latest": "true"}
        resp = self._get(url, params)

        if resp is None:
            return []

        try:
            data = resp.json()
            live_matches = []

            for match in data.get("matches", []):
                if "Indian Premier League" in match.get("series", {}).get("name", ""):
                    live_matches.append({
                        "match_id": match.get("objectId"),
                        "title": match.get("title"),
                        "status": match.get("statusText"),
                        "team1": match.get("teams", [{}])[0].get("team", {}).get("name"),
                        "team2": match.get("teams", [{}])[1].get("team", {}).get("name") if len(match.get("teams", [])) > 1 else None,
                        "score1": match.get("teams", [{}])[0].get("score"),
                        "score2": match.get("teams", [{}])[1].get("score") if len(match.get("teams", [])) > 1 else None,
                    })

            return live_matches
        except Exception as e:
            logger.error(f"Failed to get live scores: {e}")
            return []

    def get_upcoming_matches(self) -> list[dict]:
        """Get upcoming IPL matches."""
        url = f"{self.BASE_URL}/cricket-fixtures"
        resp = self._get(url)

        if resp is None:
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            matches = []

            match_cards = soup.find_all("div", {"class": lambda c: c and "match-card" in c.lower()}) if soup else []
            for card in match_cards:
                title = card.find("span", {"class": "match-title"})
                venue = card.find("span", {"class": "match-venue"})
                if title:
                    matches.append({
                        "title": title.get_text(strip=True),
                        "venue": venue.get_text(strip=True) if venue else "Unknown",
                    })

            return matches
        except Exception as e:
            logger.error(f"Failed to get upcoming matches: {e}")
            return []

    def scrape_all_seasons(self) -> dict:
        """Scrape data for all IPL seasons."""
        all_data = {}
        for season in settings.ipl_seasons:
            logger.info(f"Scraping season {season}...")
            matches = self.get_season_matches(season)
            all_data[season] = matches
        return all_data
