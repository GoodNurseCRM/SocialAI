"""
Good Nurse Marketing Agent — Daily Scheduler
Run this script in the background to enable automatic morning briefs.

Usage:
    python run_scheduler.py

Keeps running 24/7. Every morning at 7:00 AM it:
  1. Analyses Google Ads performance
  2. Reviews past activity
  3. Analyses goodnurse.com.au website
  4. Does live market research
  5. Generates 3-5 marketing suggestions with full plans
  6. Saves to SQLite — appears in the Strategy tab of the app

Also runs immediately on startup so you get a brief right away.
"""

import schedule
import time
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [SCHEDULER] %(levelname)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def run_brief():
    logger.info("=" * 60)
    logger.info(f"Starting morning brief — {datetime.now().strftime('%A %d %B %Y %H:%M')}")
    logger.info("=" * 60)
    try:
        from strategy_engine import run_morning_brief
        brief = run_morning_brief()
        logger.info("Morning brief complete.")
        logger.info(f"Preview:\n{brief[:500]}...")
    except Exception as e:
        logger.error(f"Morning brief failed: {e}", exc_info=True)


# Schedule daily at 7:00 AM
schedule.every().day.at("07:00").do(run_brief)

logger.info("Good Nurse Scheduler started.")
logger.info("Morning brief scheduled for 07:00 AM daily.")
logger.info("Running initial brief now...")

# Run immediately on startup
run_brief()

logger.info("Scheduler is now watching for 07:00 AM. Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(30)
