# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

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

POST_INTERVAL    = int(os.getenv("POST_INTERVAL_MINUTES", 30))
FLOOD_SLEEP_MIN  = int(os.getenv("FLOOD_WAIT_SLEEP_MIN",  10))
FLOOD_SLEEP_MAX  = int(os.getenv("FLOOD_WAIT_SLEEP_MAX",  20))
COPYRIGHT_MINS   = int(os.getenv("COPYRIGHT_DELETE_MINUTES", 120))   # 2 hours = 120 min
ADULT_DELETE_MINS = int(os.getenv("ADULT_DELETE_MINUTES", 30))        # 18+ = 30 min
MEGA_TIMES       = os.getenv("MEGA_BROADCAST_TIMES", "09:00,21:00")
DB_CHANNEL       = int(os.getenv("DATABASE_CHANNEL_ID", 0))
ROUND2_AFTER_HRS = int(os.getenv("ROUND2_AFTER_HOURS", 24))

_bot_client  = None
_is_sleeping = False

# ad_id → {user_id: msg_id} — broadcasted messages track karne ke liye auto-delete
_broadcast_msg_map: dict[str, dict[int, int]] = {}


def set_client(client):
    global _bot_client
    _bot_client = client


def is_sleeping() -> bool:
    return _is_sleeping


def record_sent_msg(ad_id: str, user_id: int, msg_id: int):
    """Sent message track karo — baad mein delete ke liye."""
    if ad_id not in _broadcast_msg_map:
        _broadcast_msg_map[ad_id] = {}
    _broadcast_msg_map[ad_id][user_id] = msg_id


# ═══════════════════════════════════════════════════════════════════
#  QUEUE PROCESSOR
# ═══════════════════════════════════════════════════════════════════

async def process_queue():
    global _is_sleeping
    if _is_sleeping or not _bot_client:
        return

    from database import (get_next_queued_ad, get_all_active_users,
                          increment_ad_reach, mark_user_blocked, get_ad, ads_col)
    from utils.broadcaster import send_ad_to_user
    from bson import ObjectId

    ad = get_next_queued_ad()
    if not ad:
        return

    round_num = ad.get("_queue_round", 1)
    ad_id     = str(ad["_id"])
    log.info(f"Broadcasting ad {ad_id} — Round {round_num} ...")

    users = get_all_active_users()
    sent  = 0

    for u in users:
        uid = u["user_id"]
        try:
            msg_id = await send_ad_to_user(_bot_client, uid, ad)
            if msg_id:
                record_sent_msg(ad_id, uid, msg_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            err = str(e)
            if "FLOOD_WAIT" in err:
                wait_secs  = _parse_flood_wait(err)
                sleep_mins = max(wait_secs // 60 + 1,
                                 random.randint(FLOOD_SLEEP_MIN, FLOOD_SLEEP_MAX))
                log.warning(f"FloodWait! Sleeping {sleep_mins} min.")
                await _deep_sleep(sleep_mins * 60)
                return
            elif "USER_IS_BLOCKED" in err or "user is deactivated" in err.lower() \
                    or "peer id invalid" in err.lower():
                mark_user_blocked(uid)
            else:
                log.warning(f"Failed to send to {uid}: {e}")

    increment_ad_reach(ad_id, sent, round_num=round_num)
    log.info(f"Ad {ad_id} Round {round_num} sent to {sent} users.")

    # Owner notify
    try:
        updated   = get_ad(ad_id)
        round_msg = (
            f"Round {round_num} broadcast complete!\n"
            f"Sent to: {sent} users\n"
            f"Total reach so far: {updated.get('reach', sent)}\n\n"
        )
        if round_num == 1:
            round_msg += (
                f"Round 2 agle din ({ROUND2_AFTER_HRS} ghante baad) jaayega —\n"
                f"tab aur naye users bhi cover honge!"
            )
        else:
            round_msg += "Dono rounds complete! Post ab archive ho gayi.\nNaya ad: /createad"

        await _bot_client.send_message(
            ad["owner_id"],
            f"📊 Ad Update!\n\nAd ID: `{ad_id}`\n{round_msg}",
        )
    except Exception:
        pass

    if round_num == 2:
        try:
            if ad.get("db_channel_msg_id"):
                await _bot_client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"Could not delete DB msg: {e}")
        ads_col.update_one(
            {"_id": ObjectId(ad_id)},
            {"$set": {"status": "completed"}}
        )
        log.info(f"Ad {ad_id} completed both rounds. Archived.")


def _parse_flood_wait(error_str: str) -> int:
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
#  ROUND 2 SCHEDULER
# ═══════════════════════════════════════════════════════════════════

async def schedule_round2():
    if _is_sleeping or not _bot_client:
        return
    from database import queue_round2_ads
    count = queue_round2_ads()
    if count > 0:
        log.info(f"Round 2: {count} ads queued for day-2 broadcast.")


# ═══════════════════════════════════════════════════════════════════
#  MEGA-BROADCAST
# ═══════════════════════════════════════════════════════════════════

async def mega_broadcast():
    if _is_sleeping or not _bot_client:
        return
    from database import ads_col, queue_col

    already_queued = {d["ad_id"] for d in queue_col.find({})}
    fresh_ads = list(ads_col.find({
        "status":       "approved",
        "posted_count": 0,
        "_id":          {"$nin": list(already_queued)},
    }))

    count = 0
    for ad in fresh_ads:
        queue_col.insert_one({
            "ad_id":     str(ad["_id"]),
            "round":     1,
            "queued_at": datetime.now(timezone.utc),
            "mega":      True,
        })
        count += 1

    log.info(f"Mega-broadcast: {count} fresh ads queued for Round 1.")


# ═══════════════════════════════════════════════════════════════════
#  COPYRIGHT AUTO-DELETE — 2 GHANTE BAAD (users ke messages bhi)
# ═══════════════════════════════════════════════════════════════════

async def auto_delete_copyright():
    if not _bot_client:
        return
    from database import ads_col
    from bson import ObjectId

    cutoff  = datetime.now(timezone.utc) - timedelta(minutes=COPYRIGHT_MINS)
    flagged = list(ads_col.find({
        "is_copyright": True,
        "status":       {"$ne": "deleted"},
        "copyright_flagged_at": {"$lte": cutoff},
    }))

    for ad in flagged:
        ad_id = str(ad["_id"])

        # DB channel se delete karo
        try:
            if ad.get("db_channel_msg_id"):
                await _bot_client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"DB msg delete failed: {e}")

        # Sabhi users ke paas se delete karo
        sent_map = _broadcast_msg_map.get(ad_id, {})
        deleted_count = 0
        for uid, msg_id in sent_map.items():
            try:
                await _bot_client.delete_messages(uid, msg_id)
                deleted_count += 1
                await asyncio.sleep(0.03)
            except Exception:
                pass
        if sent_map:
            _broadcast_msg_map.pop(ad_id, None)
            log.info(f"Copyright ad {ad_id}: deleted from {deleted_count} users.")

        ads_col.update_one({"_id": ad["_id"]}, {"$set": {"status": "deleted"}})

        # Owner ko batao
        try:
            await _bot_client.send_message(
                ad["owner_id"],
                f"🚫 <b>Copyright Ad Auto-Delete Ho Gaya!</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                f"Tumhara content copyright violate karta tha isliye "
                f"sabhi users ke paas se {COPYRIGHT_MINS} minute baad delete ho gaya.\n"
                f"⚠️ Ek strike tumhare account par lag gayi hai.",
                parse_mode="html"
            )
        except Exception:
            pass

        log.info(f"Auto-deleted copyright ad {ad_id}")


# ═══════════════════════════════════════════════════════════════════
#  18+ AUTO-DELETE — 30 MINUTE BAAD (users ke messages bhi)
# ═══════════════════════════════════════════════════════════════════

async def auto_delete_18plus():
    if not _bot_client:
        return
    from database import ads_col
    from bson import ObjectId

    cutoff  = datetime.now(timezone.utc) - timedelta(minutes=ADULT_DELETE_MINS)
    flagged = list(ads_col.find({
        "is_18plus":         True,
        "status":            {"$ne": "deleted"},
        "flagged_18plus_at": {"$lte": cutoff},
    }))

    for ad in flagged:
        ad_id = str(ad["_id"])

        # DB channel se delete
        try:
            if ad.get("db_channel_msg_id"):
                await _bot_client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"18+ DB msg delete failed: {e}")

        # Sabhi users ke paas se delete
        sent_map = _broadcast_msg_map.get(ad_id, {})
        deleted_count = 0
        for uid, msg_id in sent_map.items():
            try:
                await _bot_client.delete_messages(uid, msg_id)
                deleted_count += 1
                await asyncio.sleep(0.03)
            except Exception:
                pass
        if sent_map:
            _broadcast_msg_map.pop(ad_id, None)
            log.info(f"18+ ad {ad_id}: deleted from {deleted_count} users.")

        ads_col.update_one({"_id": ad["_id"]}, {"$set": {"status": "deleted"}})

        # Owner ko batao
        try:
            await _bot_client.send_message(
                ad["owner_id"],
                f"🔞 <b>18+ Ad Auto-Delete Ho Gaya!</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                f"Tumhara 18+ content {ADULT_DELETE_MINS} minute baad sabhi users ke paas se "
                f"automatically delete ho gaya.\n"
                f"⚠️ Ek strike tumhare account par lag gayi hai.",
                parse_mode="html"
            )
        except Exception:
            pass

        log.info(f"Auto-deleted 18+ ad {ad_id}")


# ═══════════════════════════════════════════════════════════════════
#  BLOCKED USER CLEANUP
# ═══════════════════════════════════════════════════════════════════

async def clean_blocked_users():
    if not _bot_client:
        return
    from database import get_all_active_users, mark_user_blocked
    users   = get_all_active_users()
    removed = 0
    for u in users:
        try:
            await _bot_client.send_chat_action(u["user_id"], "typing")
        except Exception as e:
            if "USER_IS_BLOCKED" in str(e) or "peer id invalid" in str(e).lower() \
                    or "user is deactivated" in str(e).lower():
                mark_user_blocked(u["user_id"])
                removed += 1
        await asyncio.sleep(0.1)
    log.info(f"Cleanup: marked {removed} blocked users.")


# ═══════════════════════════════════════════════════════════════════
#  SCHEDULER SETUP
# ═══════════════════════════════════════════════════════════════════

def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Queue processor: har POST_INTERVAL minutes
    scheduler.add_job(
        process_queue, "interval",
        minutes=POST_INTERVAL,
        id="process_queue",
        max_instances=1, coalesce=True,
    )

    # Round 2 checker: har 1 ghante mein
    scheduler.add_job(
        schedule_round2, "interval",
        hours=1,
        id="schedule_round2",
        max_instances=1, coalesce=True,
    )

    # Mega-broadcast: 2x daily
    for i, t in enumerate(MEGA_TIMES.split(",")):
        h, m = t.strip().split(":")
        scheduler.add_job(
            mega_broadcast,
            CronTrigger(hour=int(h), minute=int(m)),
            id=f"mega_broadcast_{i}",
            max_instances=1,
        )

    # Copyright auto-delete: har 5 minutes check
    scheduler.add_job(
        auto_delete_copyright, "interval",
        minutes=5,
        id="auto_delete_copyright",
        max_instances=1,
    )

    # 18+ auto-delete: har 5 minutes check
    scheduler.add_job(
        auto_delete_18plus, "interval",
        minutes=5,
        id="auto_delete_18plus",
        max_instances=1,
    )

    # Blocked user cleanup: har Sunday 2am
    scheduler.add_job(
        clean_blocked_users,
        CronTrigger(day_of_week="sun", hour=2),
        id="clean_blocked_users",
        max_instances=1,
    )

    return scheduler
