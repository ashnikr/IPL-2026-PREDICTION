"""
Live Data Scraper.

Automatically detects current season, fetches schedules, squads, and live data.
Uses real IPL 2026 schedule with dates, times, and full squad details.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

from utils.logger import logger
from config.settings import settings


class LiveDataScraper:
    """Scrape live and current season IPL data."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.cache_dir = settings.cache_dir / "live"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._schedule = None
        self._squads = None

    def detect_current_season(self) -> int:
        """Detect current IPL season based on date."""
        now = datetime.now()
        if now.month >= 1 and now.month <= 6:
            return now.year
        return now.year + 1 if now.month >= 11 else now.year

    # ── Schedule ──────────────────────────────────────────────────────

    def get_current_schedule(self) -> list[dict]:
        """Get the current season's match schedule with dates and times."""
        if self._schedule:
            return self._schedule

        # Priority 1: Real IPL 2026 schedule file
        schedule_file = settings.data_dir / "ipl2026_schedule.json"
        if schedule_file.exists():
            self._schedule = json.loads(schedule_file.read_text())
            logger.info(f"Loaded IPL 2026 schedule: {len(self._schedule)} matches")
            return self._schedule

        # Priority 2: Cached schedule
        cache_file = self.cache_dir / f"schedule_{self.detect_current_season()}.json"
        if cache_file.exists():
            import os
            age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if age < 21600:  # 6 hours
                self._schedule = json.loads(cache_file.read_text())
                return self._schedule

        # Priority 3: Try web sources
        schedule = self._fetch_ipl_schedule()
        if not schedule:
            schedule = self._generate_expected_schedule()

        if schedule:
            cache_file.write_text(json.dumps(schedule, indent=2, default=str))

        self._schedule = schedule
        return schedule

    def get_today_matches(self) -> list[dict]:
        """Get matches scheduled for today with times."""
        schedule = self.get_current_schedule()
        today = date.today().isoformat()

        today_matches = [m for m in schedule if m.get("date") == today]

        if today_matches:
            logger.info(f"Found {len(today_matches)} match(es) today:")
            for m in today_matches:
                time_ist = m.get("time_ist", "19:30")
                logger.info(f"  {m['team1']} vs {m['team2']} at {time_ist} IST - {m.get('venue', 'TBD')}")
        else:
            logger.info(f"No matches scheduled for today ({today})")

        return today_matches

    def get_tomorrow_matches(self) -> list[dict]:
        """Get matches scheduled for tomorrow."""
        schedule = self.get_current_schedule()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        return [m for m in schedule if m.get("date") == tomorrow]

    def get_upcoming_matches(self, days: int = 7) -> list[dict]:
        """Get matches in the next N days."""
        schedule = self.get_current_schedule()
        today = date.today()
        end = today + timedelta(days=days)

        upcoming = []
        for m in schedule:
            match_date = m.get("date")
            if match_date:
                try:
                    md = date.fromisoformat(match_date)
                    if today <= md <= end:
                        upcoming.append(m)
                except (ValueError, TypeError):
                    continue

        return upcoming

    def get_match_by_number(self, match_number: int) -> dict:
        """Get a specific match by its number."""
        schedule = self.get_current_schedule()
        for m in schedule:
            if m.get("match_number") == match_number:
                return m
        return {}

    def get_completed_matches(self) -> list[dict]:
        """Get matches that have already been played (before today)."""
        schedule = self.get_current_schedule()
        today = date.today().isoformat()
        return [m for m in schedule if m.get("date", "9999") < today and m.get("team1") != "Qualifier 1"]

    def get_remaining_matches(self) -> list[dict]:
        """Get matches yet to be played."""
        schedule = self.get_current_schedule()
        today = date.today().isoformat()
        return [m for m in schedule if m.get("date", "0000") >= today
                and m.get("stage") is None]  # Exclude playoff placeholders

    def is_double_header_day(self, match_date: str = None) -> bool:
        """Check if a date has double-header matches."""
        schedule = self.get_current_schedule()
        check_date = match_date or date.today().isoformat()
        day_matches = [m for m in schedule if m.get("date") == check_date]
        return len(day_matches) >= 2

    # ── Squads ────────────────────────────────────────────────────────

    def get_team_squads(self) -> dict:
        """Get detailed squad info with player roles."""
        if self._squads:
            return self._squads

        # Priority 1: Detailed squads file
        squads_file = settings.data_dir / "ipl2026_squads.json"
        if squads_file.exists():
            self._squads = json.loads(squads_file.read_text())
            return self._squads

        # Priority 2: Cache
        cache_file = self.cache_dir / "squads_2026.json"
        if cache_file.exists():
            self._squads = json.loads(cache_file.read_text())
            return self._squads

        # Priority 3: Default squads
        self._squads = self._default_squads()
        cache_file.write_text(json.dumps(self._squads, indent=2))
        return self._squads

    def get_team_playing_xi(self, team: str) -> list[dict]:
        """Get likely playing XI for a team (first 11 from squad)."""
        squads = self.get_team_squads()
        team_data = squads.get(team, {})
        players = team_data.get("players", [])

        # Select playing XI: max 4 overseas, balanced composition
        xi = []
        overseas_count = 0
        for p in players:
            if len(xi) >= 11:
                break
            if p.get("overseas", False):
                if overseas_count >= 4:
                    continue
                overseas_count += 1
            xi.append(p)

        return xi

    def get_team_captain(self, team: str) -> str:
        """Get team captain."""
        squads = self.get_team_squads()
        team_data = squads.get(team, {})
        return team_data.get("captain", "Unknown")

    def get_squad_changes(self, team: str) -> list[dict]:
        """Check for any squad changes (injuries, replacements)."""
        changes = []
        # Try scraping latest news
        injuries = self.get_player_injuries()
        for injury in injuries:
            headline = injury.get("headline", "").lower()
            # Check if this injury is related to the team
            team_keywords = team.lower().split()
            if any(kw in headline for kw in team_keywords):
                changes.append({
                    "type": "injury",
                    "details": injury["headline"],
                })

        return changes

    # ── Points Table & Live ──────────────────────────────────────────

    def get_points_table(self) -> pd.DataFrame:
        """Get current IPL points table."""
        try:
            resp = self.session.get(
                "https://www.espncricinfo.com/series/indian-premier-league/points-table-standings",
                timeout=15,
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                table = soup.find("table")
                if table:
                    rows = table.find_all("tr")
                    data = []
                    for row in rows[1:]:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        if len(cols) >= 5:
                            data.append({
                                "team": cols[0],
                                "played": cols[1],
                                "won": cols[2],
                                "lost": cols[3],
                                "nrr": cols[4] if len(cols) > 4 else "0",
                                "points": cols[5] if len(cols) > 5 else "0",
                            })
                    return pd.DataFrame(data)
        except Exception as e:
            logger.warning(f"Failed to get points table: {e}")

        return pd.DataFrame()

    def get_player_injuries(self) -> list[dict]:
        """Get current player injury information."""
        injuries = []
        urls = [
            "https://www.espncricinfo.com/story/ipl-injuries",
            "https://www.cricbuzz.com/cricket-news/latest-news",
        ]

        for url in urls:
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    for article in soup.find_all("a"):
                        text = article.get_text(strip=True).lower()
                        if any(kw in text for kw in ["injury", "ruled out", "miss", "hamstring", "fitness"]):
                            if any(kw in text for kw in ["ipl", "premier league"]):
                                injuries.append({
                                    "headline": article.get_text(strip=True),
                                    "url": article.get("href", ""),
                                })
            except requests.RequestException:
                continue

        return injuries

    def get_match_info(self, team1: str, team2: str) -> dict:
        """Get comprehensive match info for a specific matchup."""
        schedule = self.get_current_schedule()
        squads = self.get_team_squads()

        # Find this match in schedule
        match = {}
        for m in schedule:
            if (m.get("team1") == team1 and m.get("team2") == team2) or \
               (m.get("team1") == team2 and m.get("team2") == team1):
                match = m
                break

        t1_data = squads.get(team1, {})
        t2_data = squads.get(team2, {})

        return {
            "match": match,
            "team1": {
                "name": team1,
                "captain": t1_data.get("captain", "Unknown"),
                "coach": t1_data.get("coach", "Unknown"),
                "squad_size": len(t1_data.get("players", [])),
                "playing_xi": self.get_team_playing_xi(team1),
                "overseas_count": len([p for p in t1_data.get("players", []) if p.get("overseas")]),
            },
            "team2": {
                "name": team2,
                "captain": t2_data.get("captain", "Unknown"),
                "coach": t2_data.get("coach", "Unknown"),
                "squad_size": len(t2_data.get("players", [])),
                "playing_xi": self.get_team_playing_xi(team2),
                "overseas_count": len([p for p in t2_data.get("players", []) if p.get("overseas")]),
            },
            "date": match.get("date"),
            "time_ist": match.get("time_ist", "19:30"),
            "venue": match.get("venue"),
            "city": match.get("city"),
            "is_double_header": match.get("is_double_header", False),
        }

    # ── Collect All ──────────────────────────────────────────────────

    def collect_all_live_data(self) -> dict:
        """Collect all live data in one call."""
        logger.info("Collecting all live data...")
        schedule = self.get_current_schedule()
        squads = self.get_team_squads()
        injuries = self.get_player_injuries()
        points = self.get_points_table()

        return {
            "season": self.detect_current_season(),
            "schedule": schedule,
            "total_matches": len(schedule),
            "today_matches": self.get_today_matches(),
            "tomorrow_matches": self.get_tomorrow_matches(),
            "upcoming_7days": self.get_upcoming_matches(7),
            "squads": squads,
            "injuries": injuries,
            "points_table": points.to_dict() if not points.empty else {},
        }

    # ── Private helpers ──────────────────────────────────────────────

    def _fetch_ipl_schedule(self) -> list[dict]:
        """Fetch schedule from IPL sources."""
        urls = [
            "https://www.iplt20.com/matches/schedule",
            "https://www.espncricinfo.com/series/indian-premier-league/match-schedule-fixtures",
        ]

        for url in urls:
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    return self._parse_schedule_html(resp.text)
            except requests.RequestException:
                continue

        return []

    def _parse_schedule_html(self, html: str) -> list[dict]:
        """Parse schedule from HTML."""
        soup = BeautifulSoup(html, "lxml")
        matches = []

        for match_block in soup.find_all(["div", "li"], class_=lambda c: c and any(
            kw in (c if isinstance(c, str) else " ".join(c))
            for kw in ["match", "fixture", "schedule"]
        )):
            text = match_block.get_text(separator=" ", strip=True)
            if "vs" in text.lower() or "v" in text:
                matches.append({
                    "raw_text": text[:200],
                    "source": "web",
                })

        return matches

    def _generate_expected_schedule(self) -> list[dict]:
        """Generate an expected schedule based on typical IPL format."""
        import itertools

        teams = settings.current_teams
        venues = {
            "Chennai Super Kings": {"venue": "MA Chidambaram Stadium", "city": "Chennai"},
            "Mumbai Indians": {"venue": "Wankhede Stadium", "city": "Mumbai"},
            "Royal Challengers Bengaluru": {"venue": "M Chinnaswamy Stadium", "city": "Bengaluru"},
            "Kolkata Knight Riders": {"venue": "Eden Gardens", "city": "Kolkata"},
            "Sunrisers Hyderabad": {"venue": "Rajiv Gandhi Intl Stadium", "city": "Hyderabad"},
            "Rajasthan Royals": {"venue": "Sawai Mansingh Stadium", "city": "Jaipur"},
            "Delhi Capitals": {"venue": "Arun Jaitley Stadium", "city": "Delhi"},
            "Punjab Kings": {"venue": "PCA Stadium", "city": "Mohali"},
            "Lucknow Super Giants": {"venue": "BRSABV Ekana Stadium", "city": "Lucknow"},
            "Gujarat Titans": {"venue": "Narendra Modi Stadium", "city": "Ahmedabad"},
        }

        schedule = []
        match_num = 1
        start_date = date(2026, 3, 28)
        current_date = start_date

        all_matchups = list(itertools.combinations(teams, 2))
        # Generate 70 matches (each team plays 14)
        for i, (t1, t2) in enumerate(all_matchups[:35]):
            # Home match
            for home, away in [(t1, t2), (t2, t1)]:
                venue_info = venues.get(home, {"venue": "TBD", "city": "TBD"})
                is_evening = match_num % 2 == 1
                time_ist = "19:30" if is_evening else "15:30"

                schedule.append({
                    "match_number": match_num,
                    "date": current_date.isoformat(),
                    "time_ist": time_ist,
                    "team1": home,
                    "team2": away,
                    "venue": venue_info["venue"],
                    "city": venue_info["city"],
                    "is_double_header": not is_evening,
                    "status": "scheduled",
                })
                match_num += 1
                if is_evening:
                    current_date += timedelta(days=1)

        return schedule

    def _default_squads(self) -> dict:
        """Fallback squads if detailed file not available."""
        return {
            "Chennai Super Kings": {"captain": "Ruturaj Gaikwad", "players": [
                {"name": "MS Dhoni", "role": "WK-Batsman", "overseas": False},
                {"name": "Ruturaj Gaikwad", "role": "Batsman", "overseas": False},
                {"name": "Devon Conway", "role": "Batsman", "overseas": True},
                {"name": "Ravindra Jadeja", "role": "All-rounder", "overseas": False},
                {"name": "Shivam Dube", "role": "All-rounder", "overseas": False},
                {"name": "Deepak Chahar", "role": "Bowler", "overseas": False},
                {"name": "Matheesha Pathirana", "role": "Bowler", "overseas": True},
                {"name": "Tushar Deshpande", "role": "Bowler", "overseas": False},
                {"name": "Maheesh Theekshana", "role": "Bowler", "overseas": True},
                {"name": "Shardul Thakur", "role": "All-rounder", "overseas": False},
                {"name": "Moeen Ali", "role": "All-rounder", "overseas": True},
            ]},
            "Mumbai Indians": {"captain": "Hardik Pandya", "players": [
                {"name": "Rohit Sharma", "role": "Batsman", "overseas": False},
                {"name": "Ishan Kishan", "role": "WK-Batsman", "overseas": False},
                {"name": "Suryakumar Yadav", "role": "Batsman", "overseas": False},
                {"name": "Hardik Pandya", "role": "All-rounder", "overseas": False},
                {"name": "Tim David", "role": "All-rounder", "overseas": True},
                {"name": "Jasprit Bumrah", "role": "Bowler", "overseas": False},
                {"name": "Jofra Archer", "role": "Bowler", "overseas": True},
                {"name": "Tilak Varma", "role": "Batsman", "overseas": False},
                {"name": "Piyush Chawla", "role": "Bowler", "overseas": False},
                {"name": "Kumar Kartikeya", "role": "Bowler", "overseas": False},
                {"name": "Dewald Brevis", "role": "All-rounder", "overseas": True},
            ]},
        }
