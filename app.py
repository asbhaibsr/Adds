import os
import hashlib
import hmac
import json
from functools import wraps
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key  = os.getenv("FLASK_SECRET_KEY", "viral-bot-secret-2025")
PORT            = int(os.getenv("PORT", os.getenv("FLASK_PORT", 8080)))
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
OWNER_ID        = int(os.getenv("OWNER_ID", 0))
BOT_USERNAME    = os.getenv("BOT_USERNAME", "")
DB_CHANNEL_ID   = os.getenv("DATABASE_CHANNEL_ID", "")


# ─── HEALTH CHECK — DB import nahi, seedha OK deta hai ───────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "viral-streak-bot"}), 200


# ─── DB lazy import (sirf tab jab actually zaroorat ho) ──────────
def get_db():
    import database as db
    return db


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
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            return None
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key   = hmac.new(b"WebAppData", BOT_TOKEN.encode(), "sha256").digest()
        expected     = hmac.new(secret_key, check_string.encode(), "sha256").hexdigest()
        if not hmac.compare_digest(expected, received_hash):
            return None
        user_json = pairs.get("user", "{}")
        return json.loads(user_json)
    except Exception:
        return None


def require_telegram_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data") or request.args.get("initData", "")
        user = verify_telegram_webapp(init_data) if init_data else None
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated


def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data") or request.args.get("initData", "")
        user = verify_telegram_webapp(init_data) if init_data else None
        if not user or user.get("id") != OWNER_ID:
            return jsonify({"error": "Forbidden"}), 403
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated


# ─── HTML Pages ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin_panel")
def admin_panel():
    return render_template("admin.html")


# ─── API Routes ────────────────────────────────────────────────────

@app.route("/api/userinfo", methods=["GET"])
@require_telegram_auth
def api_userinfo():
    db = get_db()
    uid  = request.tg_user.get("id")
    user = db.get_or_create_user(uid, request.tg_user.get("username", ""), request.tg_user.get("first_name", ""))
    return jsonify({
        "user_id":        uid,
        "username":       user.get("username", ""),
        "name":           user.get("name", ""),
        "free_ads":       user.get("free_ads_earned", 0),
        "streak":         user.get("streak", 0),
        "referral_count": user.get("referral_count", 0),
        "referral_link":  f"https://t.me/{BOT_USERNAME}?start=ref_{uid}",
    })


@app.route("/api/checkin", methods=["POST"])
@require_telegram_auth
def api_checkin():
    db  = get_db()
    uid = request.tg_user.get("id")
    result = db.daily_checkin(uid)
    return jsonify(result)


@app.route("/api/my_ads", methods=["GET"])
@require_telegram_auth
def api_my_ads():
    db   = get_db()
    uid  = request.tg_user.get("id")
    ads  = db.get_user_ads(uid)
    safe = []
    for ad in ads:
        safe.append({
            "ad_id":    str(ad.get("_id", "")),
            "status":   ad.get("status", ""),
            "caption":  (ad.get("caption") or "")[:100],
            "hashtags": ad.get("hashtags", []),
            "reach":    ad.get("reach", 0),
            "created":  str(ad.get("created_at", "")),
        })
    return jsonify({"ads": safe})


@app.route("/api/delete_ad", methods=["POST"])
@require_telegram_auth
def api_delete_ad():
    db    = get_db()
    uid   = request.tg_user.get("id")
    ad_id = request.json.get("ad_id")
    ad    = db.get_ad(ad_id)
    if not ad or ad.get("owner_id") != uid:
        return jsonify({"error": "Not found or not your ad"}), 404
    db.delete_ad(ad_id)
    return jsonify({"success": True})


@app.route("/api/search", methods=["GET"])
def api_search():
    db    = get_db()
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    results = db.search_ads(query, limit=10)
    safe    = []
    ch_str  = str(DB_CHANNEL_ID).replace("-100", "")
    for ad in results:
        msg_id = ad.get("db_channel_msg_id")
        safe.append({
            "ad_id":    str(ad.get("_id", "")),
            "caption":  (ad.get("caption") or "")[:200],
            "hashtags": ad.get("hashtags", []),
            "post_url": f"https://t.me/c/{ch_str}/{msg_id}" if msg_id else "",
        })
    return jsonify({"results": safe})


@app.route("/api/report_ad", methods=["POST"])
@require_telegram_auth
def api_report_ad():
    db       = get_db()
    uid      = request.tg_user.get("id")
    ad_id    = request.json.get("ad_id")
    reason   = request.json.get("reason", "user_report")
    db.add_report(uid, ad_id, reason)
    return jsonify({"success": True})


# ─── Admin API Routes ──────────────────────────────────────────────

@app.route("/api/admin/stats", methods=["GET"])
@require_owner
def api_admin_stats():
    db    = get_db()
    stats = db.get_user_stats()
    return jsonify(stats)


@app.route("/api/admin/delete_ad", methods=["POST"])
@require_owner
def api_admin_delete_ad():
    db    = get_db()
    ad_id = request.json.get("ad_id")
    db.delete_ad(ad_id)
    return jsonify({"success": True})


@app.route("/api/admin/broadcast", methods=["POST"])
@require_owner
def api_admin_broadcast():
    return jsonify({"success": True, "message": "Use /broadcast command in bot"})


@app.route("/api/admin/forcesub_channels", methods=["GET"])
@require_owner
def api_admin_forcesub():
    db       = get_db()
    channels = db.get_all_forcesub_channels()
    return jsonify({"channels": [
        {"channel_id": c["channel_id"], "title": c.get("title", ""), "invite_link": c.get("invite_link", "")}
        for c in channels
    ]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
