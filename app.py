# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import hashlib
import hmac
import json
from functools import wraps
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "viral-bot-secret-2025")
PORT           = int(os.getenv("PORT", 8080))
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
OWNER_ID       = int(os.getenv("OWNER_ID", 0))
BOT_USERNAME   = os.getenv("BOT_USERNAME", "")

def get_bot_username() -> str:
    return os.environ.get("BOT_USERNAME", BOT_USERNAME) or BOT_USERNAME

DB_CHANNEL_ID  = os.getenv("DATABASE_CHANNEL_ID", "")
DEV_MODE       = os.getenv("DEV_MODE", "false").lower() == "true"


# ─── Health check ─────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


def get_db():
    import database as db
    return db


# ═══════════════════════════════════════════════════════════════════
#  TELEGRAM WEBAPP AUTH
# ═══════════════════════════════════════════════════════════════════

def verify_telegram_webapp(init_data: str) -> dict | None:
    if not init_data:
        return None
    try:
        from urllib.parse import unquote, parse_qsl
        parsed = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            return None
        user_json = parsed.get("user", "{}")
        return json.loads(user_json)
    except Exception as e:
        app.logger.warning(f"Auth verify error: {e}")
        return None


ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

def _get_tg_user_from_request() -> dict | None:
    if DEV_MODE:
        return {"id": OWNER_ID, "first_name": "Dev", "username": "dev"}
    admin_secret = request.headers.get("X-Admin-Secret", "")
    if admin_secret and ADMIN_SECRET and admin_secret == ADMIN_SECRET:
        return {"id": OWNER_ID, "first_name": "Admin", "username": "admin"}
    init_data = (
        request.headers.get("X-Telegram-Init-Data", "")
        or request.args.get("initData", "")
        or ""
    )
    return verify_telegram_webapp(init_data) if init_data else None


def require_telegram_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_tg_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized — Telegram auth fail"}), 401
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated


def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_tg_user_from_request()
        if not user or int(user.get("id", 0)) != OWNER_ID:
            return jsonify({"error": "Forbidden — owner only"}), 403
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════════════
#  HTML PAGES
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin_panel")
def admin_panel():
    return render_template("admin.html")


# ═══════════════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/userinfo", methods=["GET"])
@require_telegram_auth
def api_userinfo():
    db   = get_db()
    tgu  = request.tg_user
    uid  = int(tgu.get("id", 0))
    user = db.get_or_create_user(
        uid,
        tgu.get("username", ""),
        tgu.get("first_name", "") + " " + tgu.get("last_name", "")
    )
    full_name = (
        user.get("full_name", "")
        or tgu.get("first_name", "")
        or "User"
    ).strip()

    return jsonify({
        "user_id":        uid,
        "username":       user.get("username", ""),
        "name":           full_name,
        "full_name":      full_name,
        "free_ads":       user.get("free_ads_earned", 0),
        "streak":         user.get("streak", 0),
        "referral_count": user.get("referral_count", 0),
        "reach":          user.get("total_reach", 0),
        "referral_link":  f"https://t.me/{get_bot_username()}?start=ref_{uid}",
        "bot_username":   get_bot_username(),
    })


@app.route("/api/checkin", methods=["POST"])
@require_telegram_auth
def api_checkin():
    db  = get_db()
    uid = int(request.tg_user.get("id", 0))
    return jsonify(db.daily_checkin(uid))


@app.route("/api/my_ads", methods=["GET"])
@require_telegram_auth
def api_my_ads():
    db   = get_db()
    uid  = int(request.tg_user.get("id", 0))
    ads  = db.get_user_ads(uid)
    safe = []
    for ad in ads:
        ad_id_str = str(ad.get("_id", ""))
        safe.append({
            "ad_id":    ad_id_str,
            "id":       ad_id_str,
            "status":   ad.get("status", ""),
            "caption":  (ad.get("caption") or "")[:100],
            "hashtags": ad.get("hashtags", []),
            "buttons":  ad.get("buttons", []),
            "reach":    ad.get("reach", 0),
            "likes":    ad.get("likes", 0),
            "created":  str(ad.get("created_at", "")),
            # link NAHI — channel pe nahi lejana
        })
    return jsonify({"ads": safe})


@app.route("/api/delete_ad", methods=["POST"])
@require_telegram_auth
def api_delete_ad():
    db    = get_db()
    uid   = int(request.tg_user.get("id", 0))
    data  = request.get_json(silent=True) or {}
    ad_id = data.get("ad_id")
    ad    = db.get_ad(ad_id)
    if not ad or ad.get("owner_id") != uid:
        return jsonify({"error": "Not found or not your ad"}), 404
    db.delete_ad(ad_id)
    return jsonify({"success": True})


# ── LATEST POSTS — Search page pe by default dikhein ─────────────
@app.route("/api/latest_ads", methods=["GET"])
def api_latest_ads():
    db      = get_db()
    limit   = min(int(request.args.get("limit", 10)), 20)
    ads     = db.get_latest_ads(limit)
    results = []
    for ad in ads:
        results.append({
            "ad_id":    str(ad.get("_id", "")),
            "caption":  (ad.get("caption") or ""),
            "hashtags": ad.get("hashtags", []),
            "buttons":  ad.get("buttons", []),
            "reach":    ad.get("reach", 0),
            "likes":    ad.get("likes", 0),
        })
    return jsonify({"results": results})


@app.route("/api/search", methods=["GET"])
def api_search():
    db    = get_db()
    query = request.args.get("q", "").strip()
    if not query:
        # Koi query nahi — latest 10 return karo
        return api_latest_ads()
    results = db.search_ads(query, limit=10)
    safe    = []
    for ad in results:
        safe.append({
            "ad_id":    str(ad.get("_id", "")),
            "caption":  (ad.get("caption") or ""),
            "hashtags": ad.get("hashtags", []),
            "buttons":  ad.get("buttons", []),
            "reach":    ad.get("reach", 0),
            "likes":    ad.get("likes", 0),
        })
    return jsonify({"results": safe})


@app.route("/api/report_ad", methods=["POST"])
@require_telegram_auth
def api_report_ad():
    db     = get_db()
    uid    = int(request.tg_user.get("id", 0))
    data   = request.get_json(silent=True) or {}
    ad_id  = data.get("ad_id")
    reason = data.get("reason", "user_report")
    db.add_report(uid, ad_id, reason)
    return jsonify({"success": True})


# ── REDEEM CODE APIs ──────────────────────────────────────────────

@app.route("/api/redeem", methods=["POST"])
@require_telegram_auth
def api_redeem():
    """User redeem code lagaye."""
    db   = get_db()
    uid  = int(request.tg_user.get("id", 0))
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"success": False, "message": "Code daalo pehle!"})
    result = db.redeem_code(code, uid)
    return jsonify(result)


@app.route("/api/admin/generate_redeem", methods=["POST"])
@require_owner
def api_generate_redeem():
    """Owner redeem code generate kare."""
    db       = get_db()
    data     = request.get_json(silent=True) or {}
    max_uses = int(data.get("max_uses", 1))
    code     = db.generate_redeem_code(OWNER_ID, max_uses)
    return jsonify({"success": True, "code": code, "max_uses": max_uses})


@app.route("/api/admin/redeem_codes", methods=["GET"])
@require_owner
def api_list_redeem_codes():
    db    = get_db()
    codes = db.get_all_redeem_codes()
    return jsonify({"codes": [
        {
            "code":       c["code"],
            "max_uses":   c.get("max_uses", 1),
            "used_count": c.get("used_count", 0),
            "is_active":  c.get("is_active", True),
            "created_at": str(c.get("created_at", "")),
        }
        for c in codes
    ]})


# ─── Admin APIs ───────────────────────────────────────────────────

@app.route("/api/admin/stats", methods=["GET"])
@require_owner
def api_admin_stats():
    return jsonify(get_db().get_user_stats())


@app.route("/api/admin/delete_ad", methods=["POST"])
@require_owner
def api_admin_delete_ad():
    data  = request.get_json(silent=True) or {}
    ad_id = data.get("ad_id")
    get_db().delete_ad(ad_id)
    return jsonify({"success": True})


@app.route("/api/admin/broadcast", methods=["POST"])
@require_owner
def api_admin_broadcast():
    return jsonify({"success": True, "message": "Use /broadcast command in bot"})


@app.route("/api/admin/forcesub_channels", methods=["GET"])
@require_owner
def api_admin_forcesub():
    channels = get_db().get_all_forcesub_channels()
    return jsonify({"channels": [
        {"channel_id": c["channel_id"], "title": c.get("title", ""), "invite_link": c.get("invite_link", "")}
        for c in channels
    ]})


# ─── 404 / 500 — always JSON ──────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
