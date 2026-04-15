import os
import hashlib
import hmac
import json
from functools import wraps
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import database as db

load_dotenv()

app = Flask(__name__)
app.secret_key  = os.getenv("FLASK_SECRET_KEY", "viral-bot-secret-2025")
PORT            = int(os.getenv("PORT", os.getenv("FLASK_PORT", 8080)))
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
OWNER_ID        = int(os.getenv("OWNER_ID", 0))
BOT_USERNAME    = os.getenv("BOT_USERNAME", "")
DB_CHANNEL_ID   = os.getenv("DATABASE_CHANNEL_ID", "")


# ─── Telegram WebApp Auth ─────────────────────────────────────────

def verify_telegram_webapp(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData. Returns user dict or None."""
    try:
        from urllib.parse import unquote
        pairs = {}
        for part in unquote(init_data).split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                pairs[k] = v

        received_hash = pairs.pop("hash", "")
        if not received_hash:
            return None

        check_string  = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key    = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if hmac.compare_digest(received_hash, expected_hash):
            return json.loads(pairs.get("user", "{}"))
    except Exception:
        pass
    return None


def get_tg_user() -> dict | None:
    """Extract initData from Header / Query / JSON body, verify, return user."""
    # 1. Header
    init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
    # 2. Query param
    if not init_data:
        init_data = request.args.get("tgWebAppData", "").strip()
    # 3. JSON body
    if not init_data and request.is_json:
        try:
            init_data = (request.get_json(silent=True) or {}).get("initData", "").strip()
        except Exception:
            pass
    if not init_data:
        return None
    return verify_telegram_webapp(init_data)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_tg_user()
        if not user:
            return jsonify({"error": "Unauthorized — initData missing or invalid"}), 401
        return f(user, *args, **kwargs)
    return decorated


def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_tg_user()
        if not user or int(user.get("id", 0)) != OWNER_ID:
            return jsonify({"error": "Owner only"}), 403
        return f(user, *args, **kwargs)
    return decorated


# ─── Health check (Koyeb needs this) ──────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "viral-streak-bot"}), 200


# ─── HTML Pages ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin_panel")
def admin_panel():
    return render_template("admin.html")


# ═══════════════════════════════════════════════════════════════════
#  USER API ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/userinfo", methods=["GET"])
@require_auth
def api_userinfo(tg_user):
    uid  = int(tg_user["id"])
    user = db.get_or_create_user(uid, tg_user.get("username", ""), tg_user.get("first_name", ""))

    base_reach    = user.get("total_reach", 0)
    display_reach = max(base_reach + 50000, 50000)

    return jsonify({
        "user_id":        uid,
        "full_name":      tg_user.get("first_name", "User"),
        "username":       tg_user.get("username", ""),
        "streak":         user["streak"],
        "last_checkin":   str(user.get("last_checkin") or ""),
        "referral_count": user["referral_count"],
        "free_ads":       user["free_ads_earned"],
        "ads_posted":     user["ads_posted"],
        "reach":          display_reach,
        "referral_link":  f"https://t.me/{BOT_USERNAME}?start=ref_{uid}",
        "is_owner":       uid == OWNER_ID,
    })


@app.route("/api/checkin", methods=["POST"])
@require_auth
def api_checkin(tg_user):
    uid    = int(tg_user["id"])
    result = db.do_checkin(uid)

    if result["already_done"]:
        return jsonify({
            "success": False,
            "message": "✅ Aaj already check-in kar liya hai!\nKal wapas aao 🌙",
            "streak":  result["streak"],
        })

    if result["broken"]:
        msg = f"💔 Streak toot gayi! Naye sar se shuru: Day 1\nHar din check-in karo, streak mat todna!"
    elif result["streak"] == 7:
        msg = f"🏆 WOAH! 7-Day Streak Complete!\nTum ek PRO ho! Dashboard dekhte raho 🔥"
    elif result["streak"] >= 3:
        msg = f"🔥 Day {result['streak']} — Kya Josh Hai!\n{7 - result['streak']} din aur → 7-Day Streak Badge!"
    else:
        msg = f"✅ Day {result['streak']} done!\nKal bhi aana, streak mat todna 💪"

    return jsonify({
        "success": True,
        "message": msg,
        "streak":  result["streak"],
        "broken":  result["broken"],
    })


@app.route("/api/my_ads", methods=["GET"])
@require_auth
def api_my_ads(tg_user):
    uid = int(tg_user["id"])
    ads = db.get_user_ads(uid)
    ch  = DB_CHANNEL_ID.replace("-100", "")

    result = []
    for ad in ads:
        msg_id = ad.get("db_channel_msg_id")
        result.append({
            "id":       str(ad["_id"]),
            "caption":  (ad.get("caption", "") or "")[:100],
            "hashtags": ad.get("hashtags", []),
            "status":   ad.get("status", "pending"),
            "reach":    ad.get("reach", 0),
            "link":     f"https://t.me/c/{ch}/{msg_id}" if msg_id and ch else "",
            "created":  str(ad.get("created_at", "")),
        })
    return jsonify(result)


@app.route("/api/delete_ad", methods=["POST"])
@require_auth
def api_delete_ad(tg_user):
    uid   = int(tg_user["id"])
    data  = request.get_json(silent=True) or {}
    ad_id = data.get("ad_id", "")
    ad    = db.get_ad(ad_id)

    if not ad:
        return jsonify({"error": "Ad nahi mila"}), 404
    if ad["owner_id"] != uid:
        return jsonify({"error": "Yeh tumhara ad nahi hai!"}), 403

    db.delete_ad(ad_id)
    return jsonify({"success": True, "message": "✅ Ad delete ho gaya!"})


@app.route("/api/search", methods=["GET"])
def api_search():
    q       = request.args.get("q", "").strip()
    results = db.search_ads(q, limit=5)
    ch      = DB_CHANNEL_ID.replace("-100", "")

    out = []
    for ad in results:
        msg_id = ad.get("db_channel_msg_id")
        out.append({
            "id":      str(ad["_id"]),
            "caption": (ad.get("caption", "") or "")[:100],
            "tags":    ad.get("hashtags", []),
            "link":    f"https://t.me/c/{ch}/{msg_id}" if msg_id and ch else "",
        })
    return jsonify(out)


@app.route("/api/report_ad", methods=["POST"])
@require_auth
def api_report_ad(tg_user):
    uid    = int(tg_user["id"])
    data   = request.get_json(silent=True) or {}
    ad_id  = data.get("ad_id", "")
    reason = data.get("reason", "copyright")

    if not ad_id:
        return jsonify({"error": "ad_id required"}), 400

    db.add_report(uid, ad_id, reason)
    return jsonify({"success": True, "message": "⚠️ Report submit ho gaya! Admin dekhega."})


# ═══════════════════════════════════════════════════════════════════
#  ADMIN API ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/admin/stats", methods=["GET"])
@require_owner
def api_admin_stats(tg_user):
    stats   = db.get_user_stats()
    reports = len(db.get_pending_reports())
    return jsonify({**stats, "pending_reports": reports})


@app.route("/api/admin/delete_ad", methods=["POST"])
@require_owner
def api_admin_delete_ad(tg_user):
    data  = request.get_json(silent=True) or {}
    ad_id = data.get("ad_id", "")
    ad    = db.get_ad(ad_id)
    if not ad:
        return jsonify({"error": "Ad nahi mila"}), 404
    db.delete_ad(ad_id)
    return jsonify({"success": True})


@app.route("/api/admin/broadcast", methods=["POST"])
@require_owner
def api_admin_broadcast(tg_user):
    return jsonify({"success": True, "message": "✅ Broadcast next cycle mein trigger hoga!"})


@app.route("/api/admin/forcesub_channels", methods=["GET"])
@require_owner
def api_forcesub_list(tg_user):
    channels = db.get_all_forcesub_channels()
    return jsonify([{
        "channel_id":  ch["channel_id"],
        "title":       ch.get("title", ""),
        "invite_link": ch.get("invite_link", ""),
    } for ch in channels])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
