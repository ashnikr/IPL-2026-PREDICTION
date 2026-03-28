"""
Cricbuzz Scraper.

Scrapes squad information, playing XI, injury updates, and pitch reports.
"""

import time
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

from utils.logger import logger
from config.settings import settings


class CricbuzzScraper:
    """Scrape IPL data from Cricbuzz."""

    BASE_URL = "https://www.cricbuzz.com"
    API_URL = "https://www.cricbuzz.com/api/cricket-match"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    # Cricbuzz IPL series IDs (approximate)
    IPL_TEAM_IDS = {
        "Chennai Super Kings": 9,
        "Mumbai Indians": 6,
        "Royal Challengers Bengaluru": 11,
        "Kolkata Knight Riders": 5,
        "Sunrisers Hyderabad": 255,
        "Rajasthan Royals": 7,
        "Delhi Capitals": 4,
        "Punjab Kings": 8,
        "Lucknow Super Giants": 6903,
        "Gujarat Titans": 6904,
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.cache_dir = settings.cache_dir / "cricbuzz"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, url: str) -> requests.Response | None:
        try:
            time.sleep(settings.scrape_delay)
            resp = self.session.get(url, timeout=settings.request_timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning(f"Cricbuzz request failed: {url} - {e}")
            return None

    def get_ipl_schedule(self) -> list[dict]:
        """Get current IPL season schedule."""
        cache_file = self.cache_dir / "schedule_2026.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{self.BASE_URL}/cricket-series/indian-premier-league/matches"
        resp = self._get(url)
        if not resp:
            return []

        matches = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            match_divs = soup.find_all("div", {"class": "cb-col-100"})

            for div in match_divs:
                title_tag = div.find("a", {"class": "text-hvr-underline"})
                venue_tag = div.find("div", {"class": "text-gray"})

                if title_tag:
                    match_text = title_tag.get_text(strip=True)
                    href = title_tag.get("href", "")

                    matches.append({
                        "title": match_text,
                        "venue": venue_tag.get_text(strip=True) if venue_tag else "",
                        "url": f"{self.BASE_URL}{href}",
                    })

            cache_file.write_text(json.dumps(matches, indent=2))
            logger.info(f"Scraped {len(matches)} scheduled matches")
        except Exception as e:
            logger.error(f"Failed to parse schedule: {e}")

        return matches

    def get_squad(self, team_name: str) -> list[dict]:
        """Get current squad for a team."""
        team_id = self.IPL_TEAM_IDS.get(team_name)
        if not team_id:
            logger.warning(f"Unknown team: {team_name}")
            return []

        cache_file = self.cache_dir / f"squad_{team_name.replace(' ', '_')}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{self.BASE_URL}/cricket-team/{team_name.lower().replace(' ', '-')}/{team_id}/players"
        resp = self._get(url)
        if not resp:
            return []

        players = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            player_links = soup.find_all("a", {"class": "cb-font-16"})

            for link in player_links:
                name = link.get_text(strip=True)
                href = link.get("href", "")
                role_tag = link.find_next("div", {"class": "cb-font-12"})
                role = role_tag.get_text(strip=True) if role_tag else "Unknown"

                players.append({
                    "name": name,
                    "role": role,
                    "team": team_name,
                    "url": f"{self.BASE_URL}{href}",
                })

            cache_file.write_text(json.dumps(players, indent=2))
            logger.info(f"Scraped {len(players)} players for {team_name}")
        except Exception as e:
            logger.error(f"Failed to parse squad for {team_name}: {e}")

        return players

    def get_all_squads(self) -> dict[str, list[dict]]:
        """Get squads for all current IPL teams."""
        squads = {}
        for team in settings.current_teams:
            squads[team] = self.get_squad(team)
        return squads

    def get_pitch_report(self, match_url: str) -> dict:
        """Get pitch report for a specific match."""
        resp = self._get(match_url)
        if not resp:
            return {}

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            pitch_div = soup.find("div", {"class": "cb-col-100"}, string=lambda t: t and "pitch" in t.lower())

            if pitch_div:
                return {
                    "pitch_report": pitch_div.get_text(strip=True),
                    "source": "cricbuzz",
                }
        except Exception as e:
            logger.warning(f"Failed to get pitch report: {e}")

        return {}

    def get_injury_updates(self) -> list[dict]:
        """Get latest injury updates for IPL players."""
        url = f"{self.BASE_URL}/cricket-news/latest-news"
        resp = self._get(url)
        if not resp:
            return []

        injuries = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            news_items = soup.find_all("a", {"class": "cb-nws-hdln-ancr"})

            keywords = ["injury", "injured", "ruled out", "hamstring", "shoulder", "fitness"]
            for item in news_items:
                text = item.get_text(strip=True).lower()
                if any(kw in text for kw in keywords) and "ipl" in text:
                    injuries.append({
                        "headline": item.get_text(strip=True),
                        "url": f"{self.BASE_URL}{item.get('href', '')}",
                        "source": "cricbuzz",
                    })

            logger.info(f"Found {len(injuries)} injury-related news items")
        except Exception as e:
            logger.error(f"Failed to get injury updates: {e}")

        return injuries

    def get_playing_xi(self, match_url: str) -> dict:
        """Attempt to get playing XI for a match."""
        resp = self._get(match_url)
        if not resp:
            return {}

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            teams = {}

            lineup_divs = soup.find_all("div", {"class": "cb-minfo-tm-nm"})
            player_divs = soup.find_all("div", {"class": "cb-col-100 cb-font-14"})

            for i, team_div in enumerate(lineup_divs[:2]):
                team_name = team_div.get_text(strip=True)
                teams[team_name] = []

            return teams
        except Exception as e:
            logger.warning(f"Failed to get playing XI: {e}")
            return {}
