"""
Project Glass X - Background posting scheduler.

Runs inside the FastAPI process using APScheduler.
"""

import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_pending_posts, update_post_status
from app.x_client import post_tweet
import logging

logger = logging.getLogger("glassx.scheduler")

_scheduler: BackgroundScheduler | None = None


def check_and_post_due_items() -> None:
    """Check for posts that are due and attempt to publish them."""
    now = datetime.utcnow().isoformat()
    due = get_pending_posts(limit=10)

    if not due:
        return

    for post in due:
        try:
            contents = json.loads(post["content_json"])
            media = json.loads(post["media_paths_json"] or "[]")

            # For now we only support single posts in MVP.
            # Thread support coming next.
            if isinstance(contents, list) and len(contents) > 0:
                text = contents[0].get("text", "") if isinstance(contents[0], dict) else str(contents[0])
            else:
                text = str(contents)

            result = post_tweet(text=text, media_paths=media)

            update_post_status(
                post["id"],
                "posted",
                posted_tweet_ids=json.dumps([result["id"]]),
            )

            logger.info(f"Posted scheduled item #{post['id']} → {result['url']}")

        except Exception as e:
            logger.exception(f"Failed to post scheduled item #{post['id']}: {e}")
            update_post_status(
                post["id"],
                "failed",
                error_message=str(e)[:500],
            )


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler (idempotent)."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        check_and_post_due_items,
        trigger=IntervalTrigger(seconds=45),
        id="glassx_poster",
        name="Glass X Poster",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Glass X background scheduler started (checking every 45s)")
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
