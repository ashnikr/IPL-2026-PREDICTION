"""
Auto-Fetch Playing XI from Live Sources.

Priority chain:
  1. CricAPI (free, 100K requests/day) — structured JSON
  2. Cricbuzz unofficial API — free, fast
  3. ESPNCricinfo scraping — fallback
  4. Squad-based prediction — last resort (likely XI from squad)

After toss is done, Playing XI is announced ~30 min before match.
This scraper auto-fetches those 11 names per team.
"""

import os
import re
import json
import time
import requests
from pathlib import Path
from datetime import datetime, date

from utils.logger import logger
from config.settings import settings

CACHE_DIR = settings.cache_dir / "playing_xi"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Free API key from https://www.cricapi.com/ (100K requests/day free)
CRICAPI_KEY = os.getenv("CRICAPI_KEY", "")

# Team name normalization for matching across sources
TEAM_ALIASES = {
    "chennai super kings": "Chennai Super Kings",
    "csk": "Chennai Super Kings",
    "chennai": "Chennai Super Kings",
    "mumbai indians": "Mumbai Indians",
    "mi": "Mumbai Indians",
    "mumbai": "Mumbai Indians",
    "royal challengers bengaluru": "Royal Challengers Bengaluru",
    "royal challengers bangalore": "Royal Challengers Bengaluru",
    "rcb": "Royal Challengers Bengaluru",
    "kolkata knight riders": "Kolkata Knight Riders",
    "kkr": "Kolkata Knight Riders",
    "kolkata": "Kolkata Knight Riders",
    "sunrisers hyderabad": "Sunrisers Hyderabad",
    "srh": "Sunrisers Hyderabad",
    "hyderabad": "Sunrisers Hyderabad",
    "delhi capitals": "Delhi Capitals",
    "dc": "Delhi Capitals",
    "delhi": "Delhi Capitals",
    "rajasthan royals": "Rajasthan Royals",
    "rr": "Rajasthan Royals",
    "rajasthan": "Rajasthan Royals",
    "punjab kings": "Punjab Kings",
    "pbks": "Punjab Kings",
    "punjab": "Punjab Kings",
    "lucknow super giants": "Lucknow Super Giants",
    "lsg": "Lucknow Super Giants",
    "lucknow": "Lucknow Super Giants",
    "gujarat titans": "Gujarat Titans",
    "gt": "Gujarat Titans",
    "gujarat": "Gujarat Titans",
}


def normalize_team(name: str) -> str:
    """Normalize team name to standard format."""
    return TEAM_ALIASES.get(name.lower().strip(), name.strip())


class PlayingXIScraper:
    """Auto-fetch Playing XI from multiple live sources."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_playing_xi(self, team1: str, team2: str) -> dict:
        """
        Get Playing XI for both teams. Tries multiple sources.

        Returns:
            {
                "team1": {"name": "CSK", "playing_xi": [...], "source": "cricbuzz"},
                "team2": {"name": "MI", "playing_xi": [...], "source": "cricbuzz"},
                "toss": "CSK won toss, chose to bat",
                "match_status": "playing_xi_announced" | "likely_xi"
            }
        """
        team1 = normalize_team(team1)
        team2 = normalize_team(team2)

        # Check cache first (valid for 2 hours)
        cached = self._check_cache(team1, team2)
        if cached:
            logger.info(f"Playing XI from cache: {team1} vs {team2}")
            return cached

        # Try sources in order
        result = None

        # Source 1: CricAPI (free tier)
        if CRICAPI_KEY:
            result = self._fetch_from_cricapi(team1, team2)
            if result:
                logger.info(f"Playing XI from CricAPI: {team1} vs {team2}")

        # Source 2: Cricbuzz unofficial
        if not result:
            result = self._fetch_from_cricbuzz(team1, team2)
            if result:
                logger.info(f"Playing XI from Cricbuzz: {team1} vs {team2}")

        # Source 3: ESPNCricinfo
        if not result:
            result = self._fetch_from_espn(team1, team2)
            if result:
                logger.info(f"Playing XI from ESPN: {team1} vs {team2}")

        # Source 4: Fallback to likely XI from squad data
        if not result:
            result = self._get_likely_xi(team1, team2)
            logger.info(f"Using likely XI from squads: {team1} vs {team2}")

        # Cache result
        if result:
            self._save_cache(team1, team2, result)

        return result

    # ── Source 1: CricAPI ────────────────────────────────────────────

    def _fetch_from_cricapi(self, team1: str, team2: str) -> dict | None:
        """Fetch from CricAPI free tier."""
        try:
            # Get current/recent matches
            resp = self.session.get(
                "https://api.cricapi.com/v1/currentMatches",
                params={"apikey": CRICAPI_KEY, "offset": 0},
                timeout=15,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            matches = data.get("data", [])

            # Find our match
            for match in matches:
                match_name = (match.get("name", "") + " " + match.get("matchType", "")).lower()
                t1_found = any(alias in match_name for alias in self._get_aliases(team1))
                t2_found = any(alias in match_name for alias in self._get_aliases(team2))

                if t1_found and t2_found:
                    # Try to get match info with squads
                    match_id = match.get("id")
                    if match_id:
                        squad_resp = self.session.get(
                            "https://api.cricapi.com/v1/match_squad",
                            params={"apikey": CRICAPI_KEY, "id": match_id},
                            timeout=15,
                        )
                        if squad_resp.status_code == 200:
                            squad_data = squad_resp.json().get("data", [])
                            return self._parse_cricapi_squads(squad_data, team1, team2)

        except Exception as e:
            logger.warning(f"CricAPI fetch failed: {e}")
        return None

    def _parse_cricapi_squads(self, squad_data: list, team1: str, team2: str) -> dict | None:
        """Parse CricAPI squad response."""
        result = {
            "team1": {"name": team1, "playing_xi": [], "source": "cricapi"},
            "team2": {"name": team2, "playing_xi": [], "source": "cricapi"},
            "match_status": "playing_xi_announced",
        }

        for team_data in squad_data:
            team_name = normalize_team(team_data.get("teamName", ""))
            players = team_data.get("players", [])

            xi = []
            for p in players[:11]:  # First 11 are playing XI
                xi.append({
                    "name": p.get("name", p.get("playerName", "Unknown")),
                    "role": self._map_role(p.get("role", p.get("battingStyle", ""))),
                    "playing": True,
                })

            if team_name == team1:
                result["team1"]["playing_xi"] = xi
            elif team_name == team2:
                result["team2"]["playing_xi"] = xi

        if result["team1"]["playing_xi"] and result["team2"]["playing_xi"]:
            return result
        return None

    # ── Source 2: Cricbuzz Unofficial ─────────────────────────────────

    def _fetch_from_cricbuzz(self, team1: str, team2: str) -> dict | None:
        """Fetch from Cricbuzz live scores page."""
        try:
            from bs4 import BeautifulSoup

            # Get Cricbuzz live scores to find match URL
            resp = self.session.get("https://www.cricbuzz.com/cricket-match/live-scores", timeout=15)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Find match links that contain both team names
            match_link = None
            for a_tag in soup.find_all("a", href=True):
                text = a_tag.get_text(strip=True).lower()
                href = a_tag["href"]
                t1_match = any(alias in text for alias in self._get_aliases(team1))
                t2_match = any(alias in text for alias in self._get_aliases(team2))
                if t1_match and t2_match and "/cricket-scores/" in href:
                    match_link = href
                    break

            if not match_link:
                # Try cricket-match/live-scores pattern
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "/live-cricket-scores/" in href or "/cricket-scores/" in href:
                        text = a_tag.get_text(strip=True).lower()
                        if any(alias in text for alias in self._get_aliases(team1)):
                            if any(alias in text for alias in self._get_aliases(team2)):
                                match_link = href
                                break

            if not match_link:
                return None

            # Fetch match page for playing XI
            match_url = f"https://www.cricbuzz.com{match_link}" if match_link.startswith("/") else match_link
            match_resp = self.session.get(match_url, timeout=15)
            if match_resp.status_code != 200:
                return None

            return self._parse_cricbuzz_match(match_resp.text, team1, team2)

        except Exception as e:
            logger.warning(f"Cricbuzz fetch failed: {e}")
        return None

    def _parse_cricbuzz_match(self, html: str, team1: str, team2: str) -> dict | None:
        """Parse Cricbuzz match page for Playing XI."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "team1": {"name": team1, "playing_xi": [], "source": "cricbuzz"},
            "team2": {"name": team2, "playing_xi": [], "source": "cricbuzz"},
            "match_status": "playing_xi_announced",
        }

        # Try to find playing XI section
        # Cricbuzz uses various class patterns for player names
        player_sections = soup.find_all("div", class_=re.compile(r"cb-col.*cb-col-100"))

        # Look for player name patterns in scorecard
        all_player_names = []
        for elem in soup.find_all(["a", "div", "span"]):
            classes = " ".join(elem.get("class", []))
            # Cricbuzz player name classes
            if any(c in classes for c in ["cb-player", "cb-text-link", "cb-plyr"]):
                name = elem.get_text(strip=True)
                if name and len(name) > 2 and not name.isdigit():
                    all_player_names.append(name)

        # Also look for batting/bowling tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if cells:
                    first_cell = cells[0].get_text(strip=True)
                    # Player names are typically in the first cell
                    if first_cell and len(first_cell) > 2 and not first_cell.replace(".", "").isdigit():
                        # Clean up name (remove (c), (wk), etc.)
                        clean = re.sub(r"\s*\(.*?\)", "", first_cell).strip()
                        if clean:
                            all_player_names.append(clean)

        # Deduplicate while preserving order
        seen = set()
        unique_names = []
        for n in all_player_names:
            clean = n.strip()
            if clean and clean.lower() not in seen and len(clean) > 2:
                seen.add(clean.lower())
                unique_names.append(clean)

        # Split players into teams (first 11 = team that batted first, next 11 = other team)
        if len(unique_names) >= 22:
            # Try to determine which team batted first from toss info
            toss_text = ""
            for elem in soup.find_all(["div", "span", "p"]):
                text = elem.get_text(strip=True).lower()
                if "toss" in text and ("won" in text or "elected" in text or "chose" in text):
                    toss_text = text
                    break

            t1_batted = any(alias in toss_text for alias in self._get_aliases(team1)) and "bat" in toss_text

            if t1_batted:
                result["team1"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique_names[:11]]
                result["team2"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique_names[11:22]]
            else:
                result["team2"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique_names[:11]]
                result["team1"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique_names[11:22]]

            result["toss"] = toss_text
            return result

        return None

    # ── Source 3: ESPNCricinfo ────────────────────────────────────────

    def _fetch_from_espn(self, team1: str, team2: str) -> dict | None:
        """Fetch from ESPNCricinfo."""
        try:
            from bs4 import BeautifulSoup

            # Search for the match
            resp = self.session.get(
                "https://www.espncricinfo.com/live-cricket-score",
                timeout=15,
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Find match link
            match_link = None
            for a_tag in soup.find_all("a", href=True):
                text = a_tag.get_text(strip=True).lower()
                href = a_tag["href"]
                t1_found = any(alias in text for alias in self._get_aliases(team1))
                t2_found = any(alias in text for alias in self._get_aliases(team2))
                if t1_found and t2_found and "/live-cricket-score" in href:
                    match_link = href
                    break

            if not match_link:
                return None

            # Try to get playing XI page
            xi_url = match_link.replace("/live-cricket-score", "/match-playing-xi")
            xi_url = f"https://www.espncricinfo.com{xi_url}" if xi_url.startswith("/") else xi_url

            xi_resp = self.session.get(xi_url, timeout=15)
            if xi_resp.status_code == 200:
                return self._parse_espn_playing_xi(xi_resp.text, team1, team2)

        except Exception as e:
            logger.warning(f"ESPN fetch failed: {e}")
        return None

    def _parse_espn_playing_xi(self, html: str, team1: str, team2: str) -> dict | None:
        """Parse ESPN Playing XI page."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "team1": {"name": team1, "playing_xi": [], "source": "espn"},
            "team2": {"name": team2, "playing_xi": [], "source": "espn"},
            "match_status": "playing_xi_announced",
        }

        # ESPN uses specific div patterns for playing XI
        player_names = []
        for elem in soup.find_all(["a", "span", "div"]):
            text = elem.get_text(strip=True)
            classes = " ".join(elem.get("class", []))
            # ESPN player elements often have specific class patterns
            if ("player" in classes.lower() or elem.name == "a") and text and len(text) > 2:
                # Check if this looks like a player name (has at least a space, no numbers)
                clean = re.sub(r"\s*\(.*?\)", "", text).strip()
                if clean and " " in clean and not any(c.isdigit() for c in clean[:3]):
                    player_names.append(clean)

        # Deduplicate
        seen = set()
        unique = []
        for n in player_names:
            if n.lower() not in seen:
                seen.add(n.lower())
                unique.append(n)

        if len(unique) >= 22:
            result["team1"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique[:11]]
            result["team2"]["playing_xi"] = [{"name": n, "role": "ALL", "playing": True} for n in unique[11:22]]
            return result

        return None

    # ── Source 4: Likely XI from Squad ────────────────────────────────

    def _get_likely_xi(self, team1: str, team2: str) -> dict:
        """Predict likely Playing XI from squad data."""
        from scrapers.live_data_scraper import LiveDataScraper
        scraper = LiveDataScraper()

        ROLE_MAP = {"Batsman": "BAT", "WK-Batsman": "WK", "All-rounder": "ALL", "Bowler": "BOWL"}

        result = {
            "team1": {"name": team1, "playing_xi": [], "source": "squad_prediction"},
            "team2": {"name": team2, "playing_xi": [], "source": "squad_prediction"},
            "match_status": "likely_xi",
        }

        for key, team in [("team1", team1), ("team2", team2)]:
            xi = scraper.get_team_playing_xi(team)
            result[key]["playing_xi"] = [
                {
                    "name": p["name"],
                    "role": ROLE_MAP.get(p.get("role", ""), "ALL"),
                    "overseas": p.get("overseas", False),
                    "playing": True,
                }
                for p in xi[:11]
            ]

        return result

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_aliases(self, team: str) -> list[str]:
        """Get lowercase search aliases for a team."""
        aliases = [team.lower()]
        # Add short forms
        short_map = {
            "Chennai Super Kings": ["csk", "chennai"],
            "Mumbai Indians": ["mi", "mumbai"],
            "Royal Challengers Bengaluru": ["rcb", "bangalore", "bengaluru"],
            "Kolkata Knight Riders": ["kkr", "kolkata"],
            "Sunrisers Hyderabad": ["srh", "hyderabad", "sunrisers"],
            "Delhi Capitals": ["dc", "delhi"],
            "Rajasthan Royals": ["rr", "rajasthan"],
            "Punjab Kings": ["pbks", "punjab"],
            "Lucknow Super Giants": ["lsg", "lucknow"],
            "Gujarat Titans": ["gt", "gujarat"],
        }
        aliases.extend(short_map.get(team, []))
        return aliases

    def _map_role(self, role_str: str) -> str:
        """Map various role strings to standard codes."""
        role = role_str.lower()
        if "keep" in role or "wk" in role:
            return "WK"
        elif "all" in role:
            return "ALL"
        elif "bowl" in role:
            return "BOWL"
        else:
            return "BAT"

    def _check_cache(self, team1: str, team2: str) -> dict | None:
        """Check if we have recent cached Playing XI."""
        cache_key = f"{team1}_vs_{team2}_{date.today().isoformat()}"
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 7200:  # 2 hours cache
                return json.loads(cache_file.read_text())
        return None

    def _save_cache(self, team1: str, team2: str, data: dict):
        """Cache the Playing XI data."""
        cache_key = f"{team1}_vs_{team2}_{date.today().isoformat()}"
        cache_file = CACHE_DIR / f"{cache_key}.json"
        cache_file.write_text(json.dumps(data, indent=2, default=str))


# ── Convenience function ─────────────────────────────────────────────

def fetch_playing_xi(team1: str, team2: str) -> dict:
    """Quick function to get Playing XI for a match."""
    scraper = PlayingXIScraper()
    return scraper.get_playing_xi(team1, team2)
