"""
IPL 2026 Match Prediction System — Advanced AI Agent Engine.

Powered by: 10 AI Agents + 8 ML Models + LLM Analysis + Self-Learning

Usage:
  python main.py predict          Predict today's matches
  python main.py agents RCB SRH   Run 10-agent AI system with LLM
  python main.py match CSK MI     Quick ensemble prediction
  python main.py news CSK         Latest news & sentiment analysis
  python main.py form MI          Team form & momentum tracker
  python main.py result T1 T2 W   Record result (self-learning)
  python main.py accuracy         Prediction accuracy report
  python main.py schedule         Full IPL 2026 schedule
"""

import sys
import os
from datetime import date

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore")

from config.settings import settings
from utils.logger import logger


# Team abbreviation map
TEAM_ABBREV = {
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru",
    "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad",
    "RR": "Rajasthan Royals",
    "DC": "Delhi Capitals",
    "PBKS": "Punjab Kings",
    "LSG": "Lucknow Super Giants",
    "GT": "Gujarat Titans",
}


def resolve_team(name: str) -> str:
    """Resolve team abbreviation to full name."""
    return TEAM_ABBREV.get(name.upper(), name)


def cmd_train():
    """Train all models."""
    from train import main as train_main
    train_main()


def cmd_predict():
    """Predict today's matches."""
    from models.daily_predictor import DailyPredictor
    predictor = DailyPredictor()
    predictions = predictor.run_daily_pipeline()

    if not predictions:
        print("\nNo matches to predict today. Try: python main.py match CSK MI")


def cmd_match(team1_str: str, team2_str: str, venue: str = None,
              toss_winner: str = None, toss_decision: str = None):
    """Predict a specific match."""
    team1 = resolve_team(team1_str)
    team2 = resolve_team(team2_str)
    toss_winner_resolved = resolve_team(toss_winner) if toss_winner else None

    from models.daily_predictor import DailyPredictor
    predictor = DailyPredictor()
    pred = predictor.predict_specific_match(
        team1=team1, team2=team2,
        venue=venue, toss_winner=toss_winner_resolved,
        toss_decision=toss_decision,
    )
    predictor._print_prediction(pred)


def cmd_agents(team1_str: str, team2_str: str, venue: str = ""):
    """Run advanced 10-agent AI system for a match."""
    team1 = resolve_team(team1_str)
    team2 = resolve_team(team2_str)

    from agents.advanced_agents import AdvancedIPLAgentSystem
    agent_system = AdvancedIPLAgentSystem()
    result = agent_system.predict_match(team1, team2, venue=venue)

    print(result.get("explanation", "No explanation generated"))

    # Print LLM analysis if available
    if result.get("llm_analysis"):
        print("\n" + "=" * 70)
        print("  AI-POWERED MATCH ANALYSIS")
        print("=" * 70)
        print(result["llm_analysis"])
        print("=" * 70)


def cmd_agents_today():
    """Run advanced agents for today's matches."""
    from agents.advanced_agents import AdvancedIPLAgentSystem
    system = AdvancedIPLAgentSystem()
    results = system.predict_today()
    for r in results:
        print(r.get("explanation", ""))
        if r.get("llm_analysis"):
            print("\n" + r["llm_analysis"])


def cmd_record_result(team1_str: str, team2_str: str, winner_str: str):
    """Record a match result for self-learning."""
    team1 = resolve_team(team1_str)
    team2 = resolve_team(team2_str)
    winner = resolve_team(winner_str)

    from agents.advanced_agents import AdvancedIPLAgentSystem
    system = AdvancedIPLAgentSystem()
    system.record_result(team1, team2, winner)
    print(f"\nResult recorded: {winner} won ({team1} vs {team2})")

    report = system.get_accuracy_report()
    print(f"Overall accuracy: {report['overall_accuracy']:.1%} ({report['total_predictions']} predictions)")
    if report.get("model_leaderboard"):
        print("\nModel Leaderboard:")
        for m in report["model_leaderboard"]:
            print(f"  {m['model']:25s}  Accuracy: {m['accuracy']:.1%}  ({m['predictions']} predictions)")


def cmd_accuracy():
    """Show prediction accuracy report."""
    from models.calibration import PredictionCalibrator
    calibrator = PredictionCalibrator()
    report = calibrator.get_calibration_report()

    print(f"\n{'='*50}")
    print(f"  PREDICTION ACCURACY REPORT")
    print(f"{'='*50}")
    print(f"  Overall accuracy: {report['overall_accuracy']:.1%}")
    print(f"  Total predictions: {report['total_predictions']}")
    print(f"  Correct: {report['correct_predictions']}")
    print(f"  Last updated: {report.get('last_updated', 'Never')}")

    if report.get("model_leaderboard"):
        print(f"\n  Model Leaderboard:")
        print(f"  {'Model':25s} {'Accuracy':>10} {'Brier':>8} {'#Preds':>8}")
        print(f"  {'-'*55}")
        for m in report["model_leaderboard"]:
            print(f"  {m['model']:25s} {m['accuracy']:>9.1%} {m['brier_score']:>8.4f} {m['predictions']:>8}")

    if report.get("adjusted_weights"):
        print(f"\n  Calibrated Weights:")
        for model, weight in report["adjusted_weights"].items():
            print(f"    {model}: {weight:.4f}")
    print(f"{'='*50}")


def cmd_news(team_str: str = None):
    """Show latest cricket news and sentiment."""
    from scrapers.news_scraper import CricketNewsScraper
    scraper = CricketNewsScraper()

    if team_str:
        team = resolve_team(team_str)
        news = scraper.get_team_news(team)
        sentiment = scraper.analyze_sentiment(team, news)

        print(f"\n{'='*50}")
        print(f"  {team} — News & Sentiment")
        print(f"{'='*50}")
        print(f"  Sentiment: {sentiment['sentiment_label'].upper()} (score: {sentiment['sentiment_score']:.2f})")
        print(f"  Articles found: {sentiment['news_count']}")
        if sentiment['positive_signals']:
            print(f"\n  Positive:")
            for s in sentiment['positive_signals'][:3]:
                print(f"    + {s[:80]}")
        if sentiment['negative_signals']:
            print(f"\n  Negative:")
            for s in sentiment['negative_signals'][:3]:
                print(f"    - {s[:80]}")
        print(f"\n  Latest headlines:")
        for a in news[:5]:
            print(f"    > {a['title'][:85]}")
    else:
        news = scraper.get_latest_news()
        print(f"\n  Latest IPL Cricket News ({len(news)} articles):\n")
        for a in news[:15]:
            print(f"  [{a['source']:12s}] {a['title'][:90]}")


def cmd_form(team_str: str = None):
    """Show team form and momentum."""
    from models.form_tracker import FormTracker
    tracker = FormTracker()

    if team_str:
        team = resolve_team(team_str)
        form = tracker.get_team_form(team)
        players = tracker.get_key_players_form(team)

        print(f"\n{'='*50}")
        print(f"  {team} — Form & Momentum")
        print(f"{'='*50}")
        print(f"  Matches: {form['matches_played']} | W: {form['wins']} L: {form['losses']}")
        print(f"  Form: {form['form_string']} | Streak: {form['streak']}")
        print(f"  Momentum: {form['momentum'].upper()} ({form['momentum_score']:.2f})")
        print(f"  Rating: {form['form_rating']:.3f}")

        if players:
            print(f"\n  Key Players:")
            print(f"  {'Name':25s} {'Form':12s} {'Impact':>8}")
            print(f"  {'-'*48}")
            for p in players[:6]:
                print(f"  {p['name']:25s} {p.get('recent_form', '?'):12s} {p.get('impact_score', 0):>8.0f}")
    else:
        print(f"\n{'='*60}")
        print(f"  IPL 2026 — All Teams Form & Momentum")
        print(f"{'='*60}")
        print(f"  {'Team':40s} {'Rating':>8} {'Momentum':>10} {'Form':>8}")
        print(f"  {'-'*68}")
        for team in settings.current_teams:
            form = tracker.get_team_form(team)
            print(f"  {team:40s} {form['form_rating']:>7.3f} {form['momentum']:>10s} {form['form_string']:>8s}")
        print(f"{'='*60}")


def cmd_dream11(team1_str: str, team2_str: str, contest: str = "mega"):
    """Generate Dream11/MPL fantasy team."""
    team1 = resolve_team(team1_str)
    team2 = resolve_team(team2_str)

    from models.fantasy_team import FantasyTeamGenerator
    generator = FantasyTeamGenerator()

    # Get weather for venue
    weather = None
    try:
        from scrapers.live_data_scraper import LiveDataScraper
        from scrapers.weather_scraper import WeatherCollector
        scraper = LiveDataScraper()
        schedule = scraper.get_current_schedule()
        venue = ""
        for m in schedule:
            if (m.get("team1") == team1 and m.get("team2") == team2) or \
               (m.get("team1") == team2 and m.get("team2") == team1):
                venue = m.get("venue", "")
                break
        if venue:
            collector = WeatherCollector()
            weather = collector.get_weather(
                venue.split(",")[0] if "," in venue else venue[:20],
                str(date.today())
            )
    except Exception:
        venue = ""

    if contest == "all":
        teams = generator.generate_multiple_teams(team1, team2, venue, weather)
        for t in teams:
            generator.print_fantasy_team(t)
    else:
        result = generator.generate_team(team1, team2, venue, weather, contest)
        generator.print_fantasy_team(result)


def cmd_live(batting_str: str, bowling_str: str, score: int, wickets: int,
             overs: float = 20.0):
    """Predict match after 1st innings."""
    batting = resolve_team(batting_str)
    bowling = resolve_team(bowling_str)

    from models.live_predictor import LiveMatchPredictor
    predictor = LiveMatchPredictor()

    # Get venue and weather
    venue = ""
    weather = None
    try:
        from scrapers.live_data_scraper import LiveDataScraper
        from scrapers.weather_scraper import WeatherCollector
        scraper = LiveDataScraper()
        schedule = scraper.get_current_schedule()
        for m in schedule:
            teams = [m.get("team1", ""), m.get("team2", "")]
            if batting in teams and bowling in teams:
                venue = m.get("venue", "")
                break
        if venue:
            collector = WeatherCollector()
            city_map = {
                "Wankhede": "Mumbai", "Chinnaswamy": "Bengaluru",
                "Eden": "Kolkata", "Chidambaram": "Chennai",
                "Jaitley": "Delhi", "Rajiv Gandhi": "Hyderabad",
                "Ekana": "Lucknow", "Narendra Modi": "Ahmedabad",
            }
            city = ""
            for key, c in city_map.items():
                if key.lower() in venue.lower():
                    city = c
                    break
            if city:
                weather = collector.get_weather(city, str(date.today()))
    except Exception:
        pass

    result = predictor.predict_after_first_innings(
        batting_team=batting,
        bowling_team=bowling,
        score=score,
        wickets=wickets,
        overs=overs,
        venue=venue,
        weather=weather,
    )
    predictor.print_prediction(result)


def cmd_api():
    """Start FastAPI server."""
    import uvicorn
    print("Starting IPL Prediction API on http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)


def cmd_dashboard():
    """Start Streamlit dashboard."""
    import subprocess
    print("Starting IPL Prediction Dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
                    "--server.port", "8501"])


def cmd_schedule_auto():
    """Start automated scheduler."""
    from scheduler import run_scheduler
    run_scheduler()


def cmd_rag():
    """Update RAG knowledge base."""
    from rag.pipeline import IPLRAGPipeline
    rag = IPLRAGPipeline()
    rag.ingest_from_scrapers()
    print(f"RAG knowledge base updated: {len(rag.documents)} documents")


def cmd_tomorrow():
    """Predict tomorrow's matches."""
    from models.daily_predictor import DailyPredictor
    predictor = DailyPredictor()
    predictions = predictor.predict_tomorrow()
    if not predictions:
        print("\nNo matches tomorrow.")


def cmd_upcoming(days: int = 7):
    """Show upcoming matches."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    upcoming = scraper.get_upcoming_matches(days)

    if not upcoming:
        print(f"\nNo matches in the next {days} days.")
        return

    print(f"\nUpcoming IPL 2026 Matches (next {days} days):\n")
    print(f"{'#':<4} {'Date':<12} {'Time':<6} {'Match':<55} {'Venue'}")
    print("-" * 105)

    for m in upcoming:
        num = m.get("match_number", "?")
        dt = m.get("date", "TBD")
        time = m.get("time_ist", "19:30")
        match_str = f"{m['team1']} vs {m['team2']}"
        venue = m.get("venue", "TBD")
        dh = " (DH)" if m.get("is_double_header") else ""
        print(f"{num:<4} {dt:<12} {time:<6} {match_str:<55} {venue}{dh}")


def cmd_schedule():
    """Show full IPL 2026 schedule."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    schedule = scraper.get_current_schedule()

    print(f"\nIPL 2026 Full Schedule ({len(schedule)} matches):\n")
    print(f"{'#':<4} {'Date':<12} {'Time':<6} {'Match':<55} {'Venue'}")
    print("-" * 105)

    for m in schedule:
        num = m.get("match_number", "?")
        dt = m.get("date", "TBD")
        time = m.get("time_ist", "19:30")
        t1 = m.get("team1", "TBD")
        t2 = m.get("team2", "TBD")
        match_str = f"{t1} vs {t2}"
        venue = m.get("venue", "TBD")
        dh = " *" if m.get("is_double_header") else ""
        stage = f" [{m['stage'].upper()}]" if m.get("stage") else ""
        print(f"{num:<4} {dt:<12} {time:<6} {match_str:<55} {venue}{dh}{stage}")

    print(f"\n* = Double Header | Total: {len(schedule)} matches")


def cmd_squads(team: str = None):
    """Show team squads."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    squads = scraper.get_team_squads()

    teams_to_show = [resolve_team(team)] if team else list(squads.keys())

    for team_name in teams_to_show:
        data = squads.get(team_name, {})
        if not data:
            print(f"\nTeam not found: {team_name}")
            continue

        players = data.get("players", [])
        print(f"\n{'='*50}")
        print(f"  {team_name}")
        print(f"  Captain: {data.get('captain', 'Unknown')}")
        print(f"  Coach: {data.get('coach', 'Unknown')}")
        print(f"  Players: {len(players)}")
        print(f"{'='*50}")
        print(f"  {'Name':<25} {'Role':<20} {'Type'}")
        print(f"  {'-'*60}")
        for p in players:
            flag = "OVERSEAS" if p.get("overseas") else "Indian"
            print(f"  {p['name']:<25} {p.get('role', '?'):<20} {flag}")


def cmd_all_predictions():
    """Predict all possible matchups for the current season."""
    from itertools import combinations
    from models.ensemble import EnsemblePrediction

    ensemble = EnsemblePrediction()
    ensemble.load_all_models()

    teams = settings.current_teams
    print(f"\nPredicting all {len(list(combinations(teams, 2)))} possible matchups:\n")
    print(f"{'Match':<55} {'Team1 %':>8} {'Team2 %':>8} {'Winner'}")
    print("-" * 90)

    for t1, t2 in combinations(teams, 2):
        pred = ensemble.predict_match(team1=t1, team2=t2)
        winner = pred["predicted_winner"]
        p1 = pred["team1_win_prob"] * 100
        p2 = pred["team2_win_prob"] * 100
        match_str = f"{t1} vs {t2}"
        print(f"{match_str:<55} {p1:>7.1f}% {p2:>7.1f}%  {winner}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Available commands:")
        print("")
        print("  PREDICTIONS:")
        print("  predict         - Predict today's IPL matches (ensemble)")
        print("  tomorrow        - Predict tomorrow's matches")
        print("  match T1 T2     - Predict a specific match (e.g., match CSK MI)")
        print("  all             - Predict all possible matchups")
        print("")
        print("  AI AGENTS (Advanced):")
        print("  agents T1 T2    - Run 10-agent AI system with LLM (e.g., agents RCB SRH)")
        print("  agents-today    - Run AI agents for all today's matches")
        print("")
        print("  FANTASY CRICKET:")
        print("  dream11 T1 T2   - Best Fantasy XI with C/VC picks (e.g., dream11 RCB SRH)")
        print("  dream11 T1 T2 all - Generate 3 teams (Mega, H2H, Small league)")
        print("")
        print("  LIVE MID-MATCH:")
        print("  live BAT BOWL SCORE WKTS [OVERS] - Predict after 1st innings")
        print("    Example: python main.py live RCB SRH 185 4 20")
        print("")
        print("  SELF-LEARNING:")
        print("  result T1 T2 W  - Record match result for learning (e.g., result RCB SRH RCB)")
        print("  accuracy        - Show prediction accuracy & model leaderboard")
        print("")
        print("  INTELLIGENCE:")
        print("  news [TEAM]     - Latest cricket news & sentiment (e.g., news CSK)")
        print("  form [TEAM]     - Team form & momentum tracker (e.g., form MI)")
        print("")
        print("  DATA:")
        print("  upcoming [N]    - Show upcoming matches (next N days, default 7)")
        print("  schedule        - Show full IPL 2026 schedule")
        print("  squads [TEAM]   - Show team squads (e.g., squads CSK)")
        print("")
        print("  SYSTEM:")
        print("  train           - Train all prediction models")
        print("  api             - Start prediction API server")
        print("  dashboard       - Start visualization dashboard")
        print("  scheduler       - Start automated scheduler")
        print("  rag             - Update RAG knowledge base")
        print(f"\n  Team codes: {', '.join(TEAM_ABBREV.keys())}")
        return

    cmd = sys.argv[1].lower()

    if cmd == "train":
        cmd_train()
    elif cmd == "predict":
        cmd_predict()
    elif cmd == "tomorrow":
        cmd_tomorrow()
    elif cmd == "match":
        if len(sys.argv) < 4:
            print("Usage: python main.py match <team1> <team2> [venue] [toss_winner] [toss_decision]")
            return
        venue = sys.argv[4] if len(sys.argv) > 4 else None
        toss_w = sys.argv[5] if len(sys.argv) > 5 else None
        toss_d = sys.argv[6] if len(sys.argv) > 6 else None
        cmd_match(sys.argv[2], sys.argv[3], venue, toss_w, toss_d)
    elif cmd == "all":
        cmd_all_predictions()
    elif cmd == "agents":
        if len(sys.argv) < 4:
            print("Usage: python main.py agents <team1> <team2> [venue]")
            return
        venue = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_agents(sys.argv[2], sys.argv[3], venue)
    elif cmd == "agents-today":
        cmd_agents_today()
    elif cmd == "dream11" or cmd == "fantasy":
        if len(sys.argv) < 4:
            print("Usage: python main.py dream11 <team1> <team2> [mega|h2h|small|all]")
            return
        contest = sys.argv[4] if len(sys.argv) > 4 else "mega"
        cmd_dream11(sys.argv[2], sys.argv[3], contest)
    elif cmd == "live":
        if len(sys.argv) < 5:
            print("Usage: python main.py live <batting_team> <bowling_team> <score> <wickets> [overs]")
            print("  Example: python main.py live RCB SRH 185 4 20")
            return
        overs = float(sys.argv[6]) if len(sys.argv) > 6 else 20.0
        cmd_live(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), overs)
    elif cmd == "result":
        if len(sys.argv) < 5:
            print("Usage: python main.py result <team1> <team2> <winner>")
            print("  Example: python main.py result RCB SRH RCB")
            return
        cmd_record_result(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "accuracy":
        cmd_accuracy()
    elif cmd == "news":
        team = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_news(team)
    elif cmd == "form":
        team = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_form(team)
    elif cmd == "upcoming":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        cmd_upcoming(days)
    elif cmd == "schedule":
        cmd_schedule()
    elif cmd == "squads":
        team = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_squads(team)
    elif cmd == "api":
        cmd_api()
    elif cmd == "dashboard":
        cmd_dashboard()
    elif cmd == "scheduler":
        cmd_schedule_auto()
    elif cmd == "rag":
        cmd_rag()
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'python main.py' for usage info.")


if __name__ == "__main__":
    main()
