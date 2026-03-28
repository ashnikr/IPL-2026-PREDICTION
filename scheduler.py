"""
Automated Pipeline Orchestration.

Runs the prediction pipeline on schedule:
  - Every 6 hours: refresh data and update predictions
  - Every day at 2 PM: generate daily match predictions
  - After each match: update models with results

Uses APScheduler for scheduling (Prefect/Airflow optional).
"""

import sys
sys.path.insert(0, ".")

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime, date

from utils.logger import logger
from config.settings import settings


def refresh_data():
    """Refresh live data from web sources."""
    logger.info("=" * 50)
    logger.info("SCHEDULED: Refreshing data...")
    logger.info("=" * 50)

    try:
        from scrapers.live_data_scraper import LiveDataScraper
        scraper = LiveDataScraper()
        data = scraper.collect_all_live_data()
        logger.info(f"Data refreshed: season={data.get('season')}, "
                     f"schedule={len(data.get('schedule', []))} matches")
    except Exception as e:
        logger.error(f"Data refresh failed: {e}")


def daily_predictions():
    """Generate predictions for today's matches."""
    logger.info("=" * 50)
    logger.info(f"SCHEDULED: Daily predictions for {date.today()}")
    logger.info("=" * 50)

    try:
        from models.daily_predictor import DailyPredictor
        predictor = DailyPredictor()
        predictions = predictor.run_daily_pipeline()
        logger.info(f"Generated {len(predictions)} predictions")
    except Exception as e:
        logger.error(f"Daily prediction failed: {e}")


def update_rag_knowledge():
    """Update RAG knowledge base with latest info."""
    logger.info("SCHEDULED: Updating RAG knowledge base...")
    try:
        from rag.pipeline import IPLRAGPipeline
        rag = IPLRAGPipeline()
        rag.ingest_from_scrapers()
        logger.info("RAG knowledge base updated")
    except Exception as e:
        logger.error(f"RAG update failed: {e}")


def run_scheduler():
    """Start the automated scheduler."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BlockingScheduler()

        # Refresh data every 6 hours
        scheduler.add_job(
            refresh_data,
            IntervalTrigger(hours=6),
            id="refresh_data",
            name="Refresh live data",
        )

        # Daily predictions at 2 PM IST (8:30 UTC)
        scheduler.add_job(
            daily_predictions,
            CronTrigger(hour=8, minute=30),
            id="daily_predictions",
            name="Daily match predictions",
        )

        # Update RAG every 12 hours
        scheduler.add_job(
            update_rag_knowledge,
            IntervalTrigger(hours=12),
            id="update_rag",
            name="Update RAG knowledge",
        )

        logger.info("Scheduler started. Jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.name} ({job.trigger})")

        print("\nScheduler running. Press Ctrl+C to stop.\n")
        scheduler.start()

    except ImportError:
        logger.warning("APScheduler not installed. Running once...")
        refresh_data()
        daily_predictions()
        update_rag_knowledge()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IPL Prediction Scheduler")
    parser.add_argument("--once", action="store_true", help="Run pipeline once and exit")
    parser.add_argument("--predict", action="store_true", help="Run daily prediction only")
    parser.add_argument("--refresh", action="store_true", help="Refresh data only")
    args = parser.parse_args()

    if args.once:
        refresh_data()
        daily_predictions()
    elif args.predict:
        daily_predictions()
    elif args.refresh:
        refresh_data()
    else:
        run_scheduler()
