import os
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["viralbot"]

# ─── Collections ───────────────────────────────────────────────────
users_col      = db["users"]
ads_col        = db["ads"]
queue_col      = db["queue"]
forcesub_col   = db["forcesub_channels"]
sessions_col   = db["ad_sessions"]   # temp storage while user builds an ad
reports_col    = db["reports"]

# ─── Indexes ───────────────────────────────────────────────────────
users_col.create_index("user_id", unique=True)
ads_col.create_index([("hashtags", 1)])
ads_col.create_index([("owner_id", 1)])
ads_col.create_index([("status", 1)])
forcesub_col.create_index("channel_id", unique=True)


# ═══════════════════════════════════════════════════════════════════
#  USER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_or_create_user(user_id: int, username: str = "", full_name: str = "") -> dict:
    """Fetch user or create new record."""
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "streak": 0,
            "last_checkin": None,
            "referral_count": 0,
            "referred_by": None,
            "free_ads_earned": 0,
            "ads_posted": 0,
            "is_blocked": False,
            "joined_at": datetime.now(timezone.utc),
            "total_reach": 0,
        }
        users_col.insert_one(user)
    return user


def get_user(user_id: int) -> dict | None:
    return users_col.find_one({"user_id": user_id})


def update_user(user_id: int, data: dict):
    users_col.update_one({"user_id": user_id}, {"$set": data})


def mark_user_blocked(user_id: int):
    update_user(user_id, {"is_blocked": True})


def get_all_active_users() -> list:
    return list(users_col.find({"is_blocked": False}, {"user_id": 1}))


def get_user_stats() -> dict:
    total   = users_col.count_documents({})
    active  = users_col.count_documents({"is_blocked": False})
    blocked = users_col.count_documents({"is_blocked": True})
    return {"total": total, "active": active, "blocked": blocked}


# ─── Streak ────────────────────────────────────────────────────────

def do_checkin(user_id: int) -> dict:
    """
    Returns: {"success": bool, "streak": int, "already_done": bool, "broken": bool}
    """
    user = get_user(user_id)
    if not user:
        return {"success": False, "streak": 0, "already_done": False, "broken": False}

    now  = datetime.now(timezone.utc)
    last = user.get("last_checkin")

    if last:
        # Normalize to date comparison
        last_date = last.date() if hasattr(last, 'date') else datetime.fromisoformat(str(last)).date()
        today     = now.date()
        yesterday = today - timedelta(days=1)

        if last_date == today:
            return {"success": False, "streak": user["streak"], "already_done": True, "broken": False}
        elif last_date == yesterday:
            new_streak = user["streak"] + 1
            broken = False
        else:
            new_streak = 1
            broken = True
    else:
        new_streak = 1
        broken = False

    update_user(user_id, {
        "streak": new_streak,
        "last_checkin": now,
    })
    return {"success": True, "streak": new_streak, "already_done": False, "broken": broken}


# ─── Referral ──────────────────────────────────────────────────────

def add_referral(referrer_id: int, new_user_id: int) -> bool:
    """Returns True if free ad unlocked (every 10 referrals)."""
    referrer = get_user(referrer_id)
    if not referrer:
        return False

    # Link referral
    update_user(new_user_id, {"referred_by": referrer_id})

    new_count = referrer["referral_count"] + 1
    free_ad_bonus = 1 if new_count % 10 == 0 else 0

    users_col.update_one(
        {"user_id": referrer_id},
        {
            "$inc": {
                "referral_count": 1,
                "free_ads_earned": free_ad_bonus,
            }
        }
    )
    return free_ad_bonus == 1


# ═══════════════════════════════════════════════════════════════════
#  AD SESSIONS (while user is building an ad)
# ═══════════════════════════════════════════════════════════════════

def save_ad_session(user_id: int, data: dict):
    sessions_col.update_one(
        {"user_id": user_id},
        {"$set": {**data, "user_id": user_id, "updated_at": datetime.now(timezone.utc)}},
        upsert=True
    )


def get_ad_session(user_id: int) -> dict | None:
    return sessions_col.find_one({"user_id": user_id})


def clear_ad_session(user_id: int):
    sessions_col.delete_one({"user_id": user_id})


# ═══════════════════════════════════════════════════════════════════
#  ADS
# ═══════════════════════════════════════════════════════════════════

def create_ad(owner_id: int, data: dict) -> str:
    """
    data keys: media_type, file_id, caption, hashtags, buttons,
                db_channel_msg_id
    Returns inserted _id as string.
    """
    ad = {
        "owner_id":         owner_id,
        "media_type":       data.get("media_type"),        # photo / video / text
        "file_id":          data.get("file_id"),
        "caption":          data.get("caption", ""),
        "hashtags":         data.get("hashtags", []),
        "buttons":          data.get("buttons", []),       # [[{"text","url"},...], ...]
        "db_channel_msg_id":data.get("db_channel_msg_id"), # stored in DB channel
        "status":           "pending",                     # pending/approved/rejected/deleted
        "approved_at":      None,
        "posted_count":     0,
        "reach":            0,
        "is_copyright":     False,
        "created_at":       datetime.now(timezone.utc),
    }
    result = ads_col.insert_one(ad)
    return str(result.inserted_id)


def get_ad(ad_id: str) -> dict | None:
    from bson import ObjectId
    return ads_col.find_one({"_id": ObjectId(ad_id)})


def approve_ad(ad_id: str):
    from bson import ObjectId
    ads_col.update_one(
        {"_id": ObjectId(ad_id)},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc)}}
    )
    # Push to queue
    queue_col.insert_one({"ad_id": ad_id, "queued_at": datetime.now(timezone.utc)})


def reject_ad(ad_id: str):
    from bson import ObjectId
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$set": {"status": "rejected"}})


def delete_ad(ad_id: str):
    from bson import ObjectId
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$set": {"status": "deleted"}})
    queue_col.delete_one({"ad_id": ad_id})


def flag_copyright(ad_id: str):
    from bson import ObjectId
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$set": {"is_copyright": True}})


def get_user_ads(owner_id: int) -> list:
    return list(ads_col.find(
        {"owner_id": owner_id, "status": {"$nin": ["deleted"]}},
        sort=[("created_at", DESCENDING)]
    ))


def get_next_queued_ad() -> dict | None:
    """Pop the oldest ad from queue, return full ad doc."""
    item = queue_col.find_one_and_delete({}, sort=[("queued_at", 1)])
    if not item:
        return None
    return get_ad(item["ad_id"])


def search_ads(query: str, limit: int = 5) -> list:
    """Search hashtags + caption text."""
    q = query.lower().strip()
    results = list(ads_col.find(
        {
            "status": "approved",
            "$or": [
                {"hashtags": {"$in": [q]}},
                {"caption": {"$regex": q, "$options": "i"}},
            ]
        },
        {"_id": 1, "caption": 1, "hashtags": 1, "db_channel_msg_id": 1, "owner_id": 1}
    ).limit(limit))
    return results


def increment_ad_reach(ad_id: str, count: int = 1):
    from bson import ObjectId
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$inc": {"reach": count, "posted_count": 1}})


# ═══════════════════════════════════════════════════════════════════
#  FORCE-SUB CHANNELS
# ═══════════════════════════════════════════════════════════════════

def add_forcesub_channel(channel_id: int, invite_link: str = "", title: str = "") -> bool:
    try:
        forcesub_col.insert_one({
            "channel_id":   channel_id,
            "invite_link":  invite_link,
            "title":        title,
            "added_at":     datetime.now(timezone.utc),
        })
        return True
    except DuplicateKeyError:
        return False


def remove_forcesub_channel(channel_id: int) -> bool:
    res = forcesub_col.delete_one({"channel_id": channel_id})
    return res.deleted_count > 0


def get_all_forcesub_channels() -> list:
    return list(forcesub_col.find({}))


# ═══════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════

def add_report(reporter_id: int, ad_id: str, reason: str = "copyright"):
    reports_col.insert_one({
        "reporter_id": reporter_id,
        "ad_id":       ad_id,
        "reason":      reason,
        "reported_at": datetime.now(timezone.utc),
        "resolved":    False,
    })
    # Auto-flag the ad
    flag_copyright(ad_id)


def get_pending_reports() -> list:
    return list(reports_col.find({"resolved": False}))
