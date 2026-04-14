import os
import asyncio
import random
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

POST_INTERVAL     = int(os.getenv("POST_INTERVAL_MINUTES", 10))
FLOOD_SLEEP_MIN   = int(os.getenv("FLOOD_WAIT_SLEEP_MIN",  10))
FLOOD_SLEEP_MAX   = int(os.getenv("FLOOD_WAIT_SLEEP_MAX",  20))
COPYRIGHT_MINS    = int(os.getenv("COPYRIGHT_DELETE_MINUTES", 7))
MEGA_TIMES        = os.getenv("MEGA_BROADCAST_TIMES", "09:00,21:00")
DB_CHANNEL        = int(os.getenv("DATABASE_CHANNEL_ID", 0))
ADMIN_CHANNEL     = int(os.getenv("ADMIN_CHANNEL_ID", 0))

# Global bot client reference (set from main.py)
_bot_client = None
_is_sleeping = False


def set_client(client):
    global _bot_client
    _bot_client = client


def is_sleeping() -> bool:
    return _is_sleeping


# ═══════════════════════════════════════════════════════════════════
#  QUEUE PROCESSOR
# ═══════════════════════════════════════════════════════════════════

async def process_queue():
    """Pop one ad from queue and broadcast to all active users."""
    global _is_sleeping

    if _is_sleeping:
        log.info("Scheduler: Bot is in deep sleep, skipping.")
        return

    if not _bot_client:
        return

    from database import get_next_queued_ad, get_all_active_users, increment_ad_reach, mark_user_blocked
    from utils.broadcaster import send_ad_to_user

    ad = get_next_queued_ad()
    if not ad:
        return

    log.info(f"Broadcasting ad {ad['_id']} ...")
    users = get_all_active_users()
    sent = 0

    for u in users:
        try:
            await send_ad_to_user(_bot_client, u["user_id"], ad)
            sent += 1
            await asyncio.sleep(0.05)                     # Rate limiting: ~20 msgs/sec
        except Exception as e:
            err = str(e)
            if "FLOOD_WAIT" in err:
                wait_secs = _parse_flood_wait(err)
                sleep_mins = max(wait_secs // 60 + 1,
                                 random.randint(FLOOD_SLEEP_MIN, FLOOD_SLEEP_MAX))
                log.warning(f"FloodWait detected! Sleeping {sleep_mins} minutes.")
                await _deep_sleep(sleep_mins * 60)
                return                                    # Re-queue next cycle
            elif "USER_IS_BLOCKED" in err or "user is deactivated" in err.lower():
                mark_user_blocked(u["user_id"])
            else:
                log.warning(f"Failed to send to {u['user_id']}: {e}")

    increment_ad_reach(str(ad["_id"]), sent)
    log.info(f"Ad {ad['_id']} sent to {sent} users.")


def _parse_flood_wait(error_str: str) -> int:
    """Extract seconds from FloodWait error."""
    import re
    match = re.search(r"FLOOD_WAIT_(\d+)", error_str)
    return int(match.group(1)) if match else 60


async def _deep_sleep(seconds: int):
    global _is_sleeping
    _is_sleeping = True
    log.info(f"Deep sleep for {seconds}s ...")
    await asyncio.sleep(seconds)
    _is_sleeping = False
    log.info("Woke up from deep sleep.")


# ═══════════════════════════════════════════════════════════════════
#  MEGA-BROADCAST
# ═══════════════════════════════════════════════════════════════════

async def mega_broadcast():
    """Push ALL approved pending-queue ads at once (scheduled 2x daily)."""
    if _is_sleeping or not _bot_client:
        return
    from database import ads_col, queue_col
    from datetime import datetime, timezone

    # Re-queue all approved ads that haven't been sent today
    today = datetime.now(timezone.utc).date()
    already_queued_ids = {d["ad_id"] for d in queue_col.find({})}

    ads = list(ads_col.find({
        "status": "approved",
        "_id": {"$nin": list(already_queued_ids)}
    }))

    for ad in ads:
        queue_col.insert_one({
            "ad_id":     str(ad["_id"]),
            "queued_at": datetime.now(timezone.utc),
            "mega":      True,
        })

    log.info(f"Mega-broadcast: queued {len(ads)} ads.")


# ═══════════════════════════════════════════════════════════════════
#  COPYRIGHT AUTO-DELETE
# ═══════════════════════════════════════════════════════════════════

async def auto_delete_copyright():
    """Delete copyright-flagged posts after COPYRIGHT_MINS minutes."""
    if not _bot_client:
        return
    from database import ads_col
    from bson import ObjectId

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=COPYRIGHT_MINS)
    flagged = list(ads_col.find({
        "is_copyright": True,
        "status":       {"$ne": "deleted"},
        "created_at":   {"$lte": cutoff},
    }))

    for ad in flagged:
        try:
            # Delete from DB channel
            if ad.get("db_channel_msg_id"):
                await _bot_client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"Could not delete DB channel msg: {e}")

        ads_col.update_one({"_id": ad["_id"]}, {"$set": {"status": "deleted"}})
        log.info(f"Auto-deleted copyright ad {ad['_id']}")


# ═══════════════════════════════════════════════════════════════════
#  BLOCKED USER CLEANUP
# ═══════════════════════════════════════════════════════════════════

async def clean_blocked_users():
    """Remove users who blocked the bot (weekly cleanup)."""
    if not _bot_client:
        return
    from database import get_all_active_users, mark_user_blocked
    users = get_all_active_users()
    removed = 0
    for u in users:
        try:
            await _bot_client.send_chat_action(u["user_id"], "typing")
        except Exception as e:
            if "USER_IS_BLOCKED" in str(e) or "peer id invalid" in str(e).lower():
                mark_user_blocked(u["user_id"])
                removed += 1
        await asyncio.sleep(0.1)
    log.info(f"Cleanup: removed {removed} blocked users.")


# ═══════════════════════════════════════════════════════════════════
#  SCHEDULER SETUP
# ═══════════════════════════════════════════════════════════════════

def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Queue processor: every POST_INTERVAL minutes
    scheduler.add_job(
        process_queue,
        "interval",
        minutes=POST_INTERVAL,
        id="queue_processor",
        max_instances=1,
        coalesce=True,
    )

    # Mega-broadcast: 2x daily
    for t in MEGA_TIMES.split(","):
        h, m = t.strip().split(":")
        scheduler.add_job(
            mega_broadcast,
            CronTrigger(hour=int(h), minute=int(m)),
            id=f"mega_{h}_{m}",
            max_instances=1,
        )

    # Copyright auto-delete: every 3 minutes
    scheduler.add_job(
        auto_delete_copyright,
        "interval",
        minutes=3,
        id="copyright_cleaner",
        max_instances=1,
    )

    # Blocked user cleanup: every Sunday at 02:00
    scheduler.add_job(
        clean_blocked_users,
        CronTrigger(day_of_week="sun", hour=2),
        id="blocked_cleanup",
        max_instances=1,
    )

    return scheduler
