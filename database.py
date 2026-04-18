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
sessions_col   = db["ad_sessions"]
reports_col    = db["reports"]
likes_col      = db["likes"]          # like/unlike tracking

# ─── Indexes ───────────────────────────────────────────────────────
users_col.create_index("user_id", unique=True)
ads_col.create_index([("hashtags", 1)])
ads_col.create_index([("owner_id", 1)])
ads_col.create_index([("status", 1)])
ads_col.create_index([("round1_sent_at", 1)])
forcesub_col.create_index("channel_id", unique=True)
likes_col.create_index([("ad_id", 1), ("user_id", 1)], unique=True)


# ═══════════════════════════════════════════════════════════════════
#  USER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_or_create_user(user_id: int, username: str = "", full_name: str = "") -> dict:
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

def daily_checkin(user_id: int) -> dict:
    """Alias for do_checkin — used by Flask API."""
    return do_checkin(user_id)


def do_checkin(user_id: int) -> dict:
    user = get_user(user_id)
    if not user:
        return {"success": False, "streak": 0, "already_done": False, "broken": False,
                "message": "User nahi mila!"}

    now  = datetime.now(timezone.utc)
    last = user.get("last_checkin")

    if last:
        last_date = last.date() if hasattr(last, 'date') else datetime.fromisoformat(str(last)).date()
        today     = now.date()
        yesterday = today - timedelta(days=1)

        if last_date == today:
            return {"success": False, "streak": user["streak"], "already_done": True, "broken": False,
                    "message": "Aaj ka check-in pehle hi ho gaya! Kal dobara aana!"}
        elif last_date == yesterday:
            new_streak = user["streak"] + 1
            broken = False
        else:
            new_streak = 1
            broken = True
    else:
        new_streak = 1
        broken = False

    update_user(user_id, {"streak": new_streak, "last_checkin": now})

    if new_streak == 7:
        users_col.update_one({"user_id": user_id}, {"$inc": {"free_ads_earned": 1}})

    bonus_msg  = " 7-Day Streak! 1 Free Ad Unlock Ho Gaya!" if new_streak == 7 else ""
    broken_msg = " (Streak toot gayi thi, naye sire se shuru!)" if broken else ""
    return {"success": True, "streak": new_streak, "already_done": False, "broken": broken,
            "message": f"Check-in ho gaya! Streak: {new_streak} din!{broken_msg}{bonus_msg}"}


# ─── Referral ──────────────────────────────────────────────────────

def add_referral(referrer_id: int, new_user_id: int) -> bool:
    referrer = get_user(referrer_id)
    if not referrer:
        return False
    update_user(new_user_id, {"referred_by": referrer_id})
    new_count     = referrer["referral_count"] + 1
    free_ad_bonus = 1 if new_count % 10 == 0 else 0
    users_col.update_one(
        {"user_id": referrer_id},
        {"$inc": {"referral_count": 1, "free_ads_earned": free_ad_bonus}}
    )
    return free_ad_bonus == 1


# ═══════════════════════════════════════════════════════════════════
#  AD SESSIONS
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
    ad = {
        "owner_id":          owner_id,
        "media_type":        data.get("media_type"),
        "file_id":           data.get("file_id"),
        "caption":           data.get("caption", ""),
        "hashtags":          data.get("hashtags", []),
        "buttons":           data.get("buttons", []),
        "db_channel_msg_id": data.get("db_channel_msg_id"),
        "status":            "pending",
        "approved_at":       None,
        "posted_count":      0,           # 0 = not sent, 1 = round1 done, 2 = both done
        "round1_sent_at":    None,        # timestamp when round 1 completed
        "round2_sent_at":    None,        # timestamp when round 2 completed
        "reach":             0,
        "likes":             0,
        "is_copyright":      False,
        "created_at":        datetime.now(timezone.utc),
    }
    result = ads_col.insert_one(ad)
    return str(result.inserted_id)


def get_ad(ad_id: str) -> dict | None:
    from bson import ObjectId
    try:
        return ads_col.find_one({"_id": ObjectId(ad_id)})
    except Exception:
        return None


def approve_ad(ad_id: str):
    from bson import ObjectId
    ads_col.update_one(
        {"_id": ObjectId(ad_id)},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc)}}
    )
    # Push to queue for round 1
    queue_col.insert_one({
        "ad_id":     ad_id,
        "round":     1,
        "queued_at": datetime.now(timezone.utc),
    })


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


def get_all_browseable_ads() -> list:
    """Get all approved ads for browse feature — sorted newest first."""
    return list(ads_col.find(
        {"status": {"$in": ["approved", "completed"]}},
        sort=[("approved_at", DESCENDING)]
    ))


def get_next_queued_ad() -> dict | None:
    """Pop oldest ad from queue, return full ad doc."""
    item = queue_col.find_one_and_delete({}, sort=[("queued_at", 1)])
    if not item:
        return None
    ad = get_ad(item["ad_id"])
    if ad:
        ad["_queue_round"] = item.get("round", 1)
    return ad


def queue_round2_ads():
    """Queue all ads that completed round1 at least 24 hours ago for round 2."""
    from bson import ObjectId
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    # Find ads: approved, round 1 done (posted_count=1), round1_sent_at > 24h ago
    eligible = list(ads_col.find({
        "status":         "approved",
        "posted_count":   1,
        "round1_sent_at": {"$lte": cutoff},
    }))
    already_queued_ids = {d["ad_id"] for d in queue_col.find({})}
    count = 0
    for ad in eligible:
        ad_id = str(ad["_id"])
        if ad_id not in already_queued_ids:
            queue_col.insert_one({
                "ad_id":     ad_id,
                "round":     2,
                "queued_at": datetime.now(timezone.utc),
            })
            count += 1
    return count


def search_ads(query: str, limit: int = 5) -> list:
    q = query.lower().strip()
    return list(ads_col.find(
        {
            "status": {"$in": ["approved", "completed"]},
            "$or": [
                {"hashtags": {"$in": [q]}},
                {"caption": {"$regex": q, "$options": "i"}},
            ]
        },
        {"_id": 1, "caption": 1, "hashtags": 1, "db_channel_msg_id": 1, "owner_id": 1}
    ).limit(limit))


def increment_ad_reach(ad_id: str, count: int = 1, round_num: int = 1):
    from bson import ObjectId
    now = datetime.now(timezone.utc)
    update_data = {"$inc": {"reach": count, "posted_count": 1}}
    if round_num == 1:
        update_data["$set"] = {"round1_sent_at": now}
    elif round_num == 2:
        update_data["$set"] = {"round2_sent_at": now}
    ads_col.update_one({"_id": ObjectId(ad_id)}, update_data)


# ═══════════════════════════════════════════════════════════════════
#  LIKES
# ═══════════════════════════════════════════════════════════════════

def toggle_like(ad_id: str, user_id: int) -> dict:
    """Toggle like. Returns {liked: bool, total_likes: int}"""
    from bson import ObjectId
    existing = likes_col.find_one({"ad_id": ad_id, "user_id": user_id})
    if existing:
        # Unlike
        likes_col.delete_one({"ad_id": ad_id, "user_id": user_id})
        ads_col.update_one({"_id": ObjectId(ad_id)}, {"$inc": {"likes": -1}})
        ad = get_ad(ad_id)
        return {"liked": False, "total_likes": max(ad.get("likes", 0), 0)}
    else:
        # Like
        try:
            likes_col.insert_one({
                "ad_id":    ad_id,
                "user_id":  user_id,
                "liked_at": datetime.now(timezone.utc),
            })
            ads_col.update_one({"_id": ObjectId(ad_id)}, {"$inc": {"likes": 1}})
        except DuplicateKeyError:
            pass
        ad = get_ad(ad_id)
        return {"liked": True, "total_likes": ad.get("likes", 0)}


def has_liked(ad_id: str, user_id: int) -> bool:
    return likes_col.find_one({"ad_id": ad_id, "user_id": user_id}) is not None


# ═══════════════════════════════════════════════════════════════════
#  FORCE-SUB CHANNELS
# ═══════════════════════════════════════════════════════════════════

def add_forcesub_channel(channel_id: int, invite_link: str = "", title: str = "") -> bool:
    try:
        forcesub_col.insert_one({
            "channel_id":  channel_id,
            "invite_link": invite_link,
            "title":       title,
            "added_at":    datetime.now(timezone.utc),
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
    flag_copyright(ad_id)


def get_pending_reports() -> list:
    return list(reports_col.find({"resolved": False}))
