
# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import random
import string
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
likes_col      = db["likes"]
redeem_col     = db["redeem_codes"]   # NEW: redeem codes

# ─── Indexes ───────────────────────────────────────────────────────
users_col.create_index("user_id", unique=True)
ads_col.create_index([("hashtags", 1)])
ads_col.create_index([("owner_id", 1)])
ads_col.create_index([("status", 1)])
ads_col.create_index([("created_at", DESCENDING)])
ads_col.create_index([("round1_sent_at", 1)])
forcesub_col.create_index("channel_id", unique=True)
likes_col.create_index([("ad_id", 1), ("user_id", 1)], unique=True)
redeem_col.create_index("code", unique=True)


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
            "weekly_streak": 0,        # NEW: weekly streak count (10 weeks = 2 free ads)
            "last_week_checkin": None,  # NEW: last week number checked in
            "referral_count": 0,
            "referred_by": None,
            "free_ads_earned": 1,       # Naye user ko 1 free ad milta hai shuru mein
            "ads_posted": 0,
            "strikes": 0,
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

    free_ad_bonus = 0
    bonus_msg = ""

    # 7-day streak = 1 free ad
    if new_streak == 7:
        users_col.update_one({"user_id": user_id}, {"$inc": {"free_ads_earned": 1}})
        free_ad_bonus = 1
        bonus_msg = " 🎉 7-Day Streak! 1 Free Ad Unlock Ho Gaya!"

    # Weekly streak: har 7-day streak complete hone par weekly_streak +1
    # 10 weekly streaks = 2 extra free ads
    if new_streak % 7 == 0 and new_streak > 0:
        user_fresh = get_user(user_id) or {}
        new_weekly = user_fresh.get("weekly_streak", 0) + 1
        users_col.update_one({"user_id": user_id}, {"$set": {"weekly_streak": new_weekly}})
        if new_weekly % 10 == 0:
            users_col.update_one({"user_id": user_id}, {"$inc": {"free_ads_earned": 2}})
            bonus_msg += f" 🏆 {new_weekly} Weekly Streaks Complete! 2 Extra Free Ads Mil Gaye!"

    broken_msg = " (Streak toot gayi thi, naye sire se shuru!)" if broken else ""
    return {"success": True, "streak": new_streak, "already_done": False, "broken": broken,
            "free_ad_bonus": free_ad_bonus,
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
        "posted_count":      0,
        "round1_sent_at":    None,
        "round2_sent_at":    None,
        "reach":             0,
        "likes":             0,
        "is_copyright":      False,
        "is_18plus":          False,
        "copyright_flagged_at": None,
        "flagged_18plus_at":  None,
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
    """Copyright flag karo. ads_posted counter kam karo taaki user naya ad bana sake."""
    from bson import ObjectId
    now = datetime.now(timezone.utc)
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$set": {"is_copyright": True, "copyright_flagged_at": now}})
    # Strike do + ads_posted counter fix karo
    ad = get_ad(ad_id)
    if ad:
        owner_data = users_col.find_one({"user_id": ad["owner_id"]}) or {}
        current_posted = owner_data.get("ads_posted", 1)
        users_col.update_one(
            {"user_id": ad["owner_id"]},
            {"$inc": {"strikes": 1}, "$set": {"ads_posted": max(0, current_posted - 1)}}
        )


def flag_18plus(ad_id: str):
    """18+ content flag karo - 30 min baad delete hoga. ads_posted counter theek karo."""
    from bson import ObjectId
    now = datetime.now(timezone.utc)
    ads_col.update_one({"_id": ObjectId(ad_id)}, {"$set": {"is_18plus": True, "flagged_18plus_at": now}})
    # Strike do (ads_posted mat ghataao — ad broadcast hogi toh poster ko credit milega)
    ad = get_ad(ad_id)
    if ad:
        users_col.update_one({"user_id": ad["owner_id"]}, {"$inc": {"strikes": 1}})


def delete_user_data(user_id: int):
    """Admin ke liye - blocked user ka saara data delete karo."""
    users_col.delete_one({"user_id": user_id})


def get_user_ads(owner_id: int) -> list:
    return list(ads_col.find(
        {"owner_id": owner_id, "status": {"$nin": ["deleted"]}},
        sort=[("created_at", DESCENDING)]
    ))


def get_all_browseable_ads() -> list:
    return list(ads_col.find(
        {"status": {"$in": ["approved", "completed"]}},
        sort=[("approved_at", DESCENDING)]
    ))


def get_latest_ads(limit: int = 10) -> list:
    """Latest approved ads — mini app search page ke liye."""
    return list(ads_col.find(
        {"status": {"$in": ["approved", "completed"]}},
        sort=[("approved_at", DESCENDING)]
    ).limit(limit))


def get_next_queued_ad() -> dict | None:
    item = queue_col.find_one_and_delete({}, sort=[("queued_at", 1)])
    if not item:
        return None
    ad = get_ad(item["ad_id"])
    if ad:
        ad["_queue_round"] = item.get("round", 1)
    return ad


def queue_round2_ads():
    from bson import ObjectId
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
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


def search_ads(query: str, limit: int = 10) -> list:
    q = query.lower().strip()
    # Full projection — buttons bhi chahiye
    return list(ads_col.find(
        {
            "status": {"$in": ["approved", "completed"]},
            "$or": [
                {"hashtags": {"$in": [q]}},
                {"caption": {"$regex": q, "$options": "i"}},
            ]
        }
        # No projection — sab fields aayenge (buttons included)
    ).sort("approved_at", DESCENDING).limit(limit))


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
    from bson import ObjectId
    existing = likes_col.find_one({"ad_id": ad_id, "user_id": user_id})
    if existing:
        likes_col.delete_one({"ad_id": ad_id, "user_id": user_id})
        ads_col.update_one({"_id": ObjectId(ad_id)}, {"$inc": {"likes": -1}})
        ad = get_ad(ad_id)
        return {"liked": False, "total_likes": max(ad.get("likes", 0), 0)}
    else:
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


# ═══════════════════════════════════════════════════════════════════
#  REDEEM CODES  ← NEW
# ═══════════════════════════════════════════════════════════════════

def generate_redeem_code(created_by: int, max_uses: int = 1) -> str:
    """
    Unique redeem code generate karo.
    Format: ADMS-XXXXXX (6 random uppercase chars)
    max_uses: kitne log use kar sakte hain (default 1)
    """
    while True:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        code   = f"ADMS-{suffix}"
        try:
            redeem_col.insert_one({
                "code":       code,
                "created_by": created_by,
                "max_uses":   max_uses,
                "used_count": 0,
                "used_by":    [],
                "created_at": datetime.now(timezone.utc),
                "is_active":  True,
            })
            return code
        except DuplicateKeyError:
            continue  # Collision — retry


def redeem_code(code: str, user_id: int) -> dict:
    """
    User redeem code use kare.
    Returns: {success, message, free_ads_given}
    """
    code = code.strip().upper()
    doc  = redeem_col.find_one({"code": code})

    if not doc:
        return {"success": False, "message": "❌ Code galat hai ya exist nahi karta!"}

    if not doc.get("is_active", True):
        return {"success": False, "message": "❌ Yeh code already deactivate ho chuka hai!"}

    if user_id in (doc.get("used_by") or []):
        return {"success": False, "message": "❌ Tumne pehle hi yeh code use kar liya hai!"}

    if doc.get("used_count", 0) >= doc.get("max_uses", 1):
        return {"success": False, "message": "❌ Yeh code ki limit khatam ho gayi!"}

    # Mark as used
    redeem_col.update_one(
        {"code": code},
        {
            "$inc": {"used_count": 1},
            "$push": {"used_by": user_id},
        }
    )

    # Max uses reach ho gayi — deactivate
    new_count = doc.get("used_count", 0) + 1
    if new_count >= doc.get("max_uses", 1):
        redeem_col.update_one({"code": code}, {"$set": {"is_active": False}})

    # User ko 1 free ad do
    users_col.update_one({"user_id": user_id}, {"$inc": {"free_ads_earned": 1, "total_redeemed": 1}})

    return {
        "success":       True,
        "message":       "🎉 Code redeem ho gaya! 1 Free Ad tumhare account mein add ho gaya!\n\nAb /createad karke apna ad post karo!",
        "free_ads_given": 1,
    }


def get_all_redeem_codes() -> list:
    return list(redeem_col.find({}, sort=[("created_at", DESCENDING)]))


def deactivate_redeem_code(code: str) -> bool:
    res = redeem_col.update_one({"code": code}, {"$set": {"is_active": False}})
    return res.modified_count > 0


# ═══════════════════════════════════════════════════════════════════
#  MIGRATION — purane stuck users fix
#  Yeh function bot start pe call hota hai — ek baar chalata hai
#  Jinke ads copyright/rejected/18+ hain unka ads_posted counter fix karo
#  Aur jinke paas free_ads_earned = 0 hai aur koi active ad nahi unhe 1 free ad do
# ═══════════════════════════════════════════════════════════════════

def run_startup_migration():
    """
    Purane stuck users fix karo:
    1. Copyright flagged ads ke owners ka ads_posted counter fix
    2. Users jinke paas sirf rejected/copyright/18+ ads hain aur free_ads=0 — unhe 1 free ad do
    3. Naye users (joined baad mein) jo free_ads=0 pe stuck hain
    """
    fixed_count = 0

    # ── Fix 1: Copyright ads ke owners ───────────────────────────────
    copyright_ads = list(ads_col.find({
        "is_copyright": True,
        "status": {"$in": ["rejected", "deleted"]},
    }))
    for ad in copyright_ads:
        owner_id = ad.get("owner_id")
        if not owner_id:
            continue
        owner = users_col.find_one({"user_id": owner_id}) or {}
        # Agar owner ka ads_posted > 0 aur free_ads = 0 ho to fix karo
        if owner.get("free_ads_earned", 0) == 0:
            # Check: koi active ad hai?
            active = ads_col.count_documents({
                "owner_id": owner_id,
                "status": {"$in": ["pending", "approved"]},
                "is_copyright": {"$ne": True},
                "is_18plus": {"$ne": True},
            })
            if active == 0:
                users_col.update_one(
                    {"user_id": owner_id},
                    {"$inc": {"free_ads_earned": 1}}
                )
                fixed_count += 1

    # ── Fix 2: Sirf rejected ads wale users ──────────────────────────
    # Find users jinke paas koi approved/pending ad nahi aur free_ads = 0
    all_users_stuck = list(users_col.find({"free_ads_earned": 0, "is_blocked": False}))
    for user in all_users_stuck:
        owner_id = user.get("user_id")
        if not owner_id:
            continue
        active = ads_col.count_documents({
            "owner_id": owner_id,
            "status": {"$in": ["pending", "approved"]},
            "is_copyright": {"$ne": True},
            "is_18plus": {"$ne": True},
        })
        if active == 0:
            users_col.update_one(
                {"user_id": owner_id},
                {"$set": {"free_ads_earned": 1}}
            )
            fixed_count += 1

    return fixed_count
