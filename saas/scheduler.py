"""
Post Scheduler — publishes scheduled posts via APScheduler.
Run as a background process alongside the Streamlit app.
"""
import os, json, logging
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval  import IntervalTrigger

import saas.db as db
from saas.publisher import publish_post

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler("scheduler.log"),
                               logging.StreamHandler()])
log = logging.getLogger("scheduler")

scheduler = BlockingScheduler(timezone="Australia/Sydney")

@scheduler.scheduled_job(IntervalTrigger(minutes=1))
def check_scheduled_posts():
    """Every minute: find due posts and publish them."""
    due = db.get_scheduled_posts()
    if not due:
        return
    log.info(f"Found {len(due)} post(s) due for publishing")
    for post in due:
        try:
            log.info(f"Publishing post {post['id']} → {post['platform']}")
            success, msg = publish_post(post)
            status = "published" if success else "failed"
            db.update_post(post["id"],
                           status=status,
                           error_message=None if success else msg,
                           published_at=datetime.now(timezone.utc).isoformat() if success else None,
                           platform_post_id=msg if success else None)
            log.info(f"Post {post['id']} → {status}: {msg}")
        except Exception as e:
            log.error(f"Post {post['id']} failed: {e}")
            db.update_post(post["id"], status="failed", error_message=str(e))

if __name__ == "__main__":
    log.info("Scheduler started — checking for due posts every 60s")
    scheduler.start()
