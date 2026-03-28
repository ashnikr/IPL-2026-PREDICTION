"""
Fantasy Cricket Team Generator — Dream11 / MPL / My11Circle.

Generates optimal fantasy XI with captain & vice-captain picks
based on form, venue stats, matchups, weather, and value analysis.

Constraints:
  - Exactly 11 players
  - Max 7 from one team
  - 1-4 Wicketkeepers, 1-6 Batsmen, 1-6 All-rounders, 1-6 Bowlers
  - 100 credit budget (Dream11 style)
  - Captain gets 2x points, Vice-Captain gets 1.5x
"""

import json
from datetime import date
from pathlib import Path

import numpy as np

from utils.logger import logger
from config.settings import settings


class FantasyTeamGenerator:
    """Generate optimal Dream11/MPL fantasy teams for IPL matches."""

    # Default credit values by role and tier
    CREDIT_TIERS = {
        "elite": 10.0,      # Top 5 players
        "premium": 9.0,     # Star players
        "mid_premium": 8.5, # Good performers
        "mid": 8.0,         # Solid picks
        "budget": 7.5,      # Value picks
        "economy": 7.0,     # Budget picks
    }

    # Player fantasy ratings (key IPL players - points potential per match)
    PLAYER_FANTASY_DATA = {
        # CSK
        "Ruturaj Gaikwad": {"role": "BAT", "credit": 9.5, "avg_pts": 42, "ceiling": 120, "floor": 8, "team": "Chennai Super Kings"},
        "Sanju Samson": {"role": "WK", "credit": 9.0, "avg_pts": 38, "ceiling": 110, "floor": 5, "team": "Chennai Super Kings"},
        "Ravindra Jadeja": {"role": "ALL", "credit": 9.0, "avg_pts": 45, "ceiling": 130, "floor": 15, "team": "Chennai Super Kings"},
        "Devon Conway": {"role": "BAT", "credit": 8.5, "avg_pts": 35, "ceiling": 100, "floor": 5, "team": "Chennai Super Kings"},
        "Rachin Ravindra": {"role": "ALL", "credit": 8.5, "avg_pts": 36, "ceiling": 95, "floor": 10, "team": "Chennai Super Kings"},

        # MI
        "Rohit Sharma": {"role": "BAT", "credit": 9.5, "avg_pts": 38, "ceiling": 110, "floor": 5, "team": "Mumbai Indians"},
        "Suryakumar Yadav": {"role": "BAT", "credit": 9.5, "avg_pts": 40, "ceiling": 115, "floor": 5, "team": "Mumbai Indians"},
        "Jasprit Bumrah": {"role": "BOWL", "credit": 9.5, "avg_pts": 35, "ceiling": 95, "floor": 10, "team": "Mumbai Indians"},
        "Hardik Pandya": {"role": "ALL", "credit": 9.5, "avg_pts": 42, "ceiling": 120, "floor": 8, "team": "Mumbai Indians"},
        "Trent Boult": {"role": "BOWL", "credit": 9.0, "avg_pts": 32, "ceiling": 85, "floor": 8, "team": "Mumbai Indians"},
        "Tim David": {"role": "BAT", "credit": 8.5, "avg_pts": 28, "ceiling": 90, "floor": 0, "team": "Mumbai Indians"},

        # RCB
        "Virat Kohli": {"role": "BAT", "credit": 10.0, "avg_pts": 42, "ceiling": 130, "floor": 5, "team": "Royal Challengers Bengaluru"},
        "Rajat Patidar": {"role": "BAT", "credit": 8.5, "avg_pts": 32, "ceiling": 100, "floor": 5, "team": "Royal Challengers Bengaluru"},
        "Phil Salt": {"role": "WK", "credit": 9.5, "avg_pts": 40, "ceiling": 120, "floor": 5, "team": "Royal Challengers Bengaluru"},
        "Josh Hazlewood": {"role": "BOWL", "credit": 9.0, "avg_pts": 33, "ceiling": 85, "floor": 10, "team": "Royal Challengers Bengaluru"},
        "Jacob Bethell": {"role": "ALL", "credit": 8.0, "avg_pts": 30, "ceiling": 90, "floor": 5, "team": "Royal Challengers Bengaluru"},
        "Krunal Pandya": {"role": "ALL", "credit": 8.0, "avg_pts": 28, "ceiling": 80, "floor": 8, "team": "Royal Challengers Bengaluru"},
        "Bhuvneshwar Kumar": {"role": "BOWL", "credit": 8.5, "avg_pts": 30, "ceiling": 80, "floor": 8, "team": "Royal Challengers Bengaluru"},
        "Yash Dayal": {"role": "BOWL", "credit": 7.5, "avg_pts": 25, "ceiling": 70, "floor": 5, "team": "Royal Challengers Bengaluru"},

        # KKR
        "Ajinkya Rahane": {"role": "BAT", "credit": 8.0, "avg_pts": 30, "ceiling": 90, "floor": 5, "team": "Kolkata Knight Riders"},
        "Sunil Narine": {"role": "ALL", "credit": 9.5, "avg_pts": 45, "ceiling": 140, "floor": 10, "team": "Kolkata Knight Riders"},
        "Andre Russell": {"role": "ALL", "credit": 9.5, "avg_pts": 42, "ceiling": 130, "floor": 5, "team": "Kolkata Knight Riders"},
        "Rinku Singh": {"role": "BAT", "credit": 8.5, "avg_pts": 32, "ceiling": 95, "floor": 5, "team": "Kolkata Knight Riders"},
        "Varun Chakravarthy": {"role": "BOWL", "credit": 8.5, "avg_pts": 32, "ceiling": 85, "floor": 8, "team": "Kolkata Knight Riders"},
        "Venkatesh Iyer": {"role": "ALL", "credit": 8.5, "avg_pts": 30, "ceiling": 85, "floor": 5, "team": "Kolkata Knight Riders"},

        # SRH
        "Travis Head": {"role": "BAT", "credit": 10.0, "avg_pts": 44, "ceiling": 135, "floor": 5, "team": "Sunrisers Hyderabad"},
        "Heinrich Klaasen": {"role": "WK", "credit": 9.5, "avg_pts": 40, "ceiling": 125, "floor": 5, "team": "Sunrisers Hyderabad"},
        "Pat Cummins": {"role": "BOWL", "credit": 9.5, "avg_pts": 38, "ceiling": 100, "floor": 10, "team": "Sunrisers Hyderabad"},
        "Abhishek Sharma": {"role": "ALL", "credit": 9.0, "avg_pts": 36, "ceiling": 110, "floor": 5, "team": "Sunrisers Hyderabad"},
        "Ishan Kishan": {"role": "WK", "credit": 8.5, "avg_pts": 30, "ceiling": 95, "floor": 5, "team": "Sunrisers Hyderabad"},
        "Liam Livingstone": {"role": "ALL", "credit": 8.5, "avg_pts": 30, "ceiling": 95, "floor": 5, "team": "Sunrisers Hyderabad"},
        "Brydon Carse": {"role": "BOWL", "credit": 8.0, "avg_pts": 28, "ceiling": 75, "floor": 8, "team": "Sunrisers Hyderabad"},

        # RR
        "Yashasvi Jaiswal": {"role": "BAT", "credit": 9.5, "avg_pts": 40, "ceiling": 120, "floor": 5, "team": "Rajasthan Royals"},
        "Riyan Parag": {"role": "ALL", "credit": 8.5, "avg_pts": 30, "ceiling": 85, "floor": 5, "team": "Rajasthan Royals"},
        "Jofra Archer": {"role": "BOWL", "credit": 9.0, "avg_pts": 33, "ceiling": 90, "floor": 8, "team": "Rajasthan Royals"},
        "Sam Curran": {"role": "ALL", "credit": 8.5, "avg_pts": 35, "ceiling": 100, "floor": 8, "team": "Rajasthan Royals"},
        "Yuzvendra Chahal": {"role": "BOWL", "credit": 8.5, "avg_pts": 30, "ceiling": 85, "floor": 5, "team": "Rajasthan Royals"},
        "Ravi Bishnoi": {"role": "BOWL", "credit": 8.0, "avg_pts": 28, "ceiling": 75, "floor": 5, "team": "Rajasthan Royals"},

        # DC
        "KL Rahul": {"role": "WK", "credit": 9.5, "avg_pts": 38, "ceiling": 115, "floor": 5, "team": "Delhi Capitals"},
        "Mitchell Starc": {"role": "BOWL", "credit": 9.5, "avg_pts": 35, "ceiling": 95, "floor": 10, "team": "Delhi Capitals"},
        "David Miller": {"role": "BAT", "credit": 8.5, "avg_pts": 28, "ceiling": 85, "floor": 0, "team": "Delhi Capitals"},
        "Axar Patel": {"role": "ALL", "credit": 8.5, "avg_pts": 32, "ceiling": 90, "floor": 8, "team": "Delhi Capitals"},
        "Jake Fraser-McGurk": {"role": "BAT", "credit": 8.0, "avg_pts": 28, "ceiling": 95, "floor": 0, "team": "Delhi Capitals"},

        # PBKS
        "Shreyas Iyer": {"role": "BAT", "credit": 9.0, "avg_pts": 35, "ceiling": 105, "floor": 5, "team": "Punjab Kings"},
        "Marcus Stoinis": {"role": "ALL", "credit": 9.0, "avg_pts": 35, "ceiling": 100, "floor": 5, "team": "Punjab Kings"},
        "Marco Jansen": {"role": "ALL", "credit": 8.5, "avg_pts": 30, "ceiling": 85, "floor": 8, "team": "Punjab Kings"},
        "Lockie Ferguson": {"role": "BOWL", "credit": 8.5, "avg_pts": 30, "ceiling": 80, "floor": 8, "team": "Punjab Kings"},
        "Arshdeep Singh": {"role": "BOWL", "credit": 8.5, "avg_pts": 28, "ceiling": 78, "floor": 8, "team": "Punjab Kings"},

        # LSG
        "Rishabh Pant": {"role": "WK", "credit": 10.0, "avg_pts": 42, "ceiling": 125, "floor": 5, "team": "Lucknow Super Giants"},
        "Nicholas Pooran": {"role": "WK", "credit": 9.0, "avg_pts": 35, "ceiling": 110, "floor": 5, "team": "Lucknow Super Giants"},
        "Mitchell Marsh": {"role": "ALL", "credit": 8.5, "avg_pts": 30, "ceiling": 90, "floor": 5, "team": "Lucknow Super Giants"},
        "Mohammed Shami": {"role": "BOWL", "credit": 9.0, "avg_pts": 32, "ceiling": 85, "floor": 8, "team": "Lucknow Super Giants"},
        "Avesh Khan": {"role": "BOWL", "credit": 8.0, "avg_pts": 26, "ceiling": 70, "floor": 5, "team": "Lucknow Super Giants"},

        # GT
        "Shubman Gill": {"role": "BAT", "credit": 9.5, "avg_pts": 40, "ceiling": 120, "floor": 5, "team": "Gujarat Titans"},
        "Jos Buttler": {"role": "WK", "credit": 9.5, "avg_pts": 38, "ceiling": 125, "floor": 5, "team": "Gujarat Titans"},
        "Rashid Khan": {"role": "ALL", "credit": 9.5, "avg_pts": 38, "ceiling": 100, "floor": 10, "team": "Gujarat Titans"},
        "Kagiso Rabada": {"role": "BOWL", "credit": 9.0, "avg_pts": 33, "ceiling": 85, "floor": 10, "team": "Gujarat Titans"},
        "Glenn Phillips": {"role": "WK", "credit": 8.0, "avg_pts": 28, "ceiling": 85, "floor": 5, "team": "Gujarat Titans"},
    }

    ROLE_MAP = {"WK": "Wicketkeeper", "BAT": "Batsman", "ALL": "All-rounder", "BOWL": "Bowler"}

    def __init__(self):
        self.llm = None
        try:
            from agents.llm_provider import LLMChain
            self.llm = LLMChain()
        except Exception:
            pass

    def generate_team(self, team1: str, team2: str, venue: str = "",
                      weather: dict = None, contest_type: str = "mega") -> dict:
        """
        Generate optimal fantasy XI for a match.

        contest_type: 'mega' (safe picks), 'h2h' (high ceiling), 'small' (balanced)
        """
        logger.info(f"Generating Fantasy XI: {team1} vs {team2} ({contest_type} contest)")

        # Get all eligible players
        t1_players = self._get_team_players(team1)
        t2_players = self._get_team_players(team2)
        all_players = t1_players + t2_players

        if len(all_players) < 11:
            logger.warning("Not enough players in database, using squad data")
            all_players = self._fill_from_squads(team1, team2, all_players)

        # Score each player
        scored = []
        for p in all_players:
            score = self._calculate_fantasy_score(p, venue, weather, contest_type)
            p["fantasy_score"] = score
            scored.append(p)

        # Select optimal 11
        team = self._select_optimal_11(scored, team1, team2, contest_type)

        # Pick Captain & Vice-Captain
        team = self._pick_captain_vc(team, contest_type)

        # Calculate total credits
        total_credits = sum(p["credit"] for p in team)

        # Generate LLM insights
        llm_insight = ""
        if self.llm:
            try:
                llm_insight = self.llm.generate(
                    f"""You are a Dream11 fantasy cricket expert. For the IPL match {team1} vs {team2} at {venue},
                    I've selected this fantasy XI:
                    Captain: {team[0]['name']} ({team[0]['role']})
                    Vice-Captain: {team[1]['name']} ({team[1]['role']})
                    Team: {', '.join(p['name'] for p in team)}

                    In 100 words, explain why this is a winning fantasy team.
                    Mention key differential picks and captain choice reasoning.""",
                    max_tokens=300, temperature=0.7,
                )
            except Exception:
                pass

        result = {
            "match": f"{team1} vs {team2}",
            "venue": venue,
            "contest_type": contest_type,
            "team": team,
            "captain": team[0]["name"],
            "vice_captain": team[1]["name"],
            "total_credits": round(total_credits, 1),
            "team_composition": self._get_composition(team),
            "team1_count": sum(1 for p in team if p["team"] == team1),
            "team2_count": sum(1 for p in team if p["team"] == team2),
            "expected_points": sum(p.get("expected_pts", p["avg_pts"]) for p in team),
            "llm_insight": llm_insight,
        }

        return result

    def _get_team_players(self, team: str) -> list[dict]:
        """Get all known players for a team."""
        return [
            {**data, "name": name}
            for name, data in self.PLAYER_FANTASY_DATA.items()
            if data["team"] == team
        ]

    def _fill_from_squads(self, team1: str, team2: str, existing: list) -> list:
        """Fill missing players from squad data."""
        try:
            from scrapers.live_data_scraper import LiveDataScraper
            scraper = LiveDataScraper()
            squads = scraper.get_team_squads()

            existing_names = {p["name"] for p in existing}

            for team in [team1, team2]:
                squad = squads.get(team, {}).get("players", [])
                for player in squad:
                    if player["name"] not in existing_names:
                        role_map = {
                            "Batsman": "BAT", "WK-Batsman": "WK",
                            "All-rounder": "ALL", "Bowler": "BOWL",
                        }
                        existing.append({
                            "name": player["name"],
                            "role": role_map.get(player.get("role", ""), "ALL"),
                            "credit": 7.5 if player.get("overseas") else 7.0,
                            "avg_pts": 20,
                            "ceiling": 60,
                            "floor": 2,
                            "team": team,
                        })
        except Exception:
            pass
        return existing

    def _calculate_fantasy_score(self, player: dict, venue: str,
                                  weather: dict, contest_type: str) -> float:
        """Calculate fantasy selection score for a player."""
        base = player["avg_pts"]

        # Venue boost for batsmen at high-scoring grounds
        venue_boost = 0
        high_scoring = ["Chinnaswamy", "Wankhede", "Jaitley", "Eden"]
        low_scoring = ["Chidambaram", "Ekana", "Rajiv Gandhi"]
        if venue:
            if any(v in venue for v in high_scoring):
                if player["role"] in ("BAT", "WK"):
                    venue_boost = 5
                elif player["role"] == "ALL":
                    venue_boost = 3
            elif any(v in venue for v in low_scoring):
                if player["role"] == "BOWL":
                    venue_boost = 5
                elif player["role"] == "ALL":
                    venue_boost = 2

        # Weather boost
        weather_boost = 0
        if weather:
            dew = weather.get("dew_probability", 0)
            if dew > 0.6 and player["role"] in ("BAT", "WK"):
                weather_boost = 3  # Dew helps batsmen in 2nd innings

        # Contest type strategy
        contest_boost = 0
        if contest_type == "h2h":
            # High ceiling players for head-to-head
            contest_boost = (player["ceiling"] - player["avg_pts"]) * 0.15
        elif contest_type == "mega":
            # Consistent players for mega contests
            consistency = 1 - (player["ceiling"] - player["floor"]) / max(player["ceiling"], 1)
            contest_boost = consistency * 5
        else:
            contest_boost = base * 0.05

        # Value score (points per credit)
        value = base / max(player["credit"], 6.0)

        score = base + venue_boost + weather_boost + contest_boost + value * 2

        player["expected_pts"] = round(base + venue_boost + weather_boost, 1)
        return round(score, 2)

    def _select_optimal_11(self, players: list, team1: str, team2: str,
                            contest_type: str) -> list:
        """Select optimal 11 with constraints."""
        # Sort by fantasy score
        players.sort(key=lambda x: x["fantasy_score"], reverse=True)

        selected = []
        role_counts = {"WK": 0, "BAT": 0, "ALL": 0, "BOWL": 0}
        team_counts = {team1: 0, team2: 0}
        total_credits = 0
        credit_budget = 100.0

        # Role constraints
        role_min = {"WK": 1, "BAT": 1, "ALL": 1, "BOWL": 1}
        role_max = {"WK": 4, "BAT": 6, "ALL": 6, "BOWL": 6}

        # First pass: ensure minimum roles
        for role in ["WK", "BAT", "ALL", "BOWL"]:
            role_players = [p for p in players if p["role"] == role and p["name"] not in {s["name"] for s in selected}]
            for p in role_players[:role_min[role]]:
                team = p["team"]
                if team_counts.get(team, 0) < 7 and total_credits + p["credit"] <= credit_budget:
                    selected.append(p)
                    role_counts[role] += 1
                    team_counts[team] = team_counts.get(team, 0) + 1
                    total_credits += p["credit"]

        # Second pass: fill remaining spots with best available
        remaining = 11 - len(selected)
        selected_names = {p["name"] for p in selected}

        for p in players:
            if remaining <= 0:
                break
            if p["name"] in selected_names:
                continue

            role = p["role"]
            team = p["team"]

            if role_counts[role] >= role_max[role]:
                continue
            if team_counts.get(team, 0) >= 7:
                continue
            if total_credits + p["credit"] > credit_budget:
                continue

            selected.append(p)
            selected_names.add(p["name"])
            role_counts[role] += 1
            team_counts[team] = team_counts.get(team, 0) + 1
            total_credits += p["credit"]
            remaining -= 1

        return selected[:11]

    def _pick_captain_vc(self, team: list, contest_type: str) -> list:
        """Pick captain and vice-captain."""
        if not team:
            return team

        if contest_type == "h2h":
            # Highest ceiling for H2H
            team.sort(key=lambda x: x.get("ceiling", 0), reverse=True)
        else:
            # Highest average for mega/small
            team.sort(key=lambda x: x.get("fantasy_score", 0), reverse=True)

        if len(team) >= 2:
            team[0]["is_captain"] = True
            team[0]["multiplier"] = 2.0
            team[1]["is_vice_captain"] = True
            team[1]["multiplier"] = 1.5

        return team

    def _get_composition(self, team: list) -> dict:
        """Get team role composition."""
        comp = {"WK": 0, "BAT": 0, "ALL": 0, "BOWL": 0}
        for p in team:
            comp[p["role"]] = comp.get(p["role"], 0) + 1
        return comp

    def print_fantasy_team(self, result: dict):
        """Print formatted fantasy team."""
        team = result["team"]
        comp = result["team_composition"]

        print(f"\n{'='*70}")
        print(f"   DREAM11 FANTASY XI — {result['match']}")
        print(f"   Contest: {result['contest_type'].upper()} | Credits: {result['total_credits']}/100")
        print(f"   Venue: {result.get('venue', 'TBD')}")
        print(f"{'='*70}")

        print(f"\n   CAPTAIN (2x):      {result['captain']}")
        print(f"   VICE-CAPTAIN (1.5x): {result['vice_captain']}")

        print(f"\n   {'Player':25s} {'Role':6s} {'Team':8s} {'Cr':>5s} {'Exp.Pts':>8s}")
        print(f"   {'-'*58}")

        # Group by role
        for role_code, role_name in [("WK", "KEEPER"), ("BAT", "BATSMAN"), ("ALL", "ALL-RND"), ("BOWL", "BOWLER")]:
            role_players = [p for p in team if p["role"] == role_code]
            if role_players:
                for p in role_players:
                    cap_marker = " (C)" if p.get("is_captain") else " (VC)" if p.get("is_vice_captain") else ""
                    team_abbr = p["team"][:3].upper()
                    mult = p.get("multiplier", 1.0)
                    exp = p.get("expected_pts", p["avg_pts"]) * mult
                    print(f"   {p['name']+cap_marker:25s} {role_name:6s} {team_abbr:8s} {p['credit']:>5.1f} {exp:>7.0f}")

        total_exp = sum(
            p.get("expected_pts", p["avg_pts"]) * p.get("multiplier", 1.0)
            for p in team
        )

        print(f"\n   {'─'*58}")
        print(f"   Composition: {comp.get('WK', 0)} WK | {comp.get('BAT', 0)} BAT | "
              f"{comp.get('ALL', 0)} ALL | {comp.get('BOWL', 0)} BOWL")
        print(f"   Players: {result['team1_count']} from Team 1 | {result['team2_count']} from Team 2")
        print(f"   Expected Points (with C/VC): ~{total_exp:.0f}")

        if result.get("llm_insight"):
            print(f"\n   AI INSIGHT:")
            for line in result["llm_insight"].split("\n"):
                print(f"   {line.strip()}")

        print(f"{'='*70}")

    def generate_multiple_teams(self, team1: str, team2: str, venue: str = "",
                                 weather: dict = None, count: int = 3) -> list[dict]:
        """Generate multiple fantasy teams for different contest types."""
        teams = []
        for ctype in ["mega", "h2h", "small"][:count]:
            result = self.generate_team(team1, team2, venue, weather, ctype)
            teams.append(result)
        return teams
