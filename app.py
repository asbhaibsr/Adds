import os
import hashlib
import hmac
import json
from functools import wraps
from flask import Flask, request, jsonify, render_template, abort
from dotenv import load_dotenv
import database as db

load_dotenv()

app   = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-pls")
PORT  = int(os.getenv("FLASK_PORT", 8080))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID  = int(os.getenv("OWNER_ID", 0))


# ─── Telegram WebApp Auth ─────────────────────────────────────────

def verify_telegram_webapp(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData and return user dict if valid."""
    try:
        from urllib.parse import parse_qs, unquote
        parsed = dict(x.split("=", 1) for x in unquote(init_data).split("&"))
        received_hash = parsed.pop("hash", "")
        check_string  = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key    = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(received_hash, expected_hash):
            user_str = parsed.get("user", "{}")
            return json.loads(user_str)
    except Exception:
        pass
    return None


def get_tg_user() -> dict | None:
    """Extract and verify user from request."""
    init_data = request.headers.get("X-Telegram-Init-Data") or \
                request.args.get("tgWebAppData") or \
                request.json.get("initData", "") if request.is_json else ""
    return verify_telegram_webapp(init_data) if init_data else None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_tg_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
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


# ─── Mini App HTML Page ────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin_panel")
def admin_panel():
    return render_template("admin.html")


# ═══════════════════════════════════════════════════════════════════
#  USER API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/userinfo", methods=["GET"])
@require_auth
def api_userinfo(tg_user):
    uid = int(tg_user["id"])
    user = db.get_or_create_user(uid, tg_user.get("username",""), tg_user.get("first_name",""))

    # Fake-inflate reach for motivation 😄
    base_reach = user.get("total_reach", 0)
    display_reach = max(base_reach + 50000, 50000)

    return jsonify({
        "user_id":       uid,
        "full_name":     tg_user.get("first_name","User"),
        "username":      tg_user.get("username",""),
        "streak":        user["streak"],
        "last_checkin":  str(user.get("last_checkin") or ""),
        "referral_count":user["referral_count"],
        "free_ads":      user["free_ads_earned"],
        "ads_posted":    user["ads_posted"],
        "reach":         display_reach,
        "referral_link": f"https://t.me/{os.getenv('BOT_USERNAME','bot')}?start=ref_{uid}",
        "is_owner":      uid == OWNER_ID,
    })


@app.route("/api/checkin", methods=["POST"])
@require_auth
def api_checkin(tg_user):
    uid    = int(tg_user["id"])
    result = db.do_checkin(uid)

    if result["already_done"]:
        return jsonify({"success": False, "message": "Aaj already check-in kar liya hai! Kal wapas aao 🌙", "streak": result["streak"]})

    msg = ""
    if result["broken"]:
        msg = f"💔 Streak toot gayi! Dobara shuru: 1 din"
    else:
        msg = f"🔥 Day {result['streak']}! " + ("Kal bhi aana! 💪" if result["streak"] < 7 else "🏆 7-Day Streak Complete!")

    return jsonify({"success": True, "message": msg, "streak": result["streak"], "broken": result["broken"]})


@app.route("/api/my_ads", methods=["GET"])
@require_auth
def api_my_ads(tg_user):
    uid  = int(tg_user["id"])
    ads  = db.get_user_ads(uid)
    ch   = str(os.getenv("DATABASE_CHANNEL_ID","")).replace("-100","")

    result = []
    for ad in ads:
        msg_id = ad.get("db_channel_msg_id")
        result.append({
            "id":       str(ad["_id"]),
            "caption":  (ad.get("caption","") or "")[:100],
            "hashtags": ad.get("hashtags",[]),
            "status":   ad.get("status","pending"),
            "reach":    ad.get("reach", 0),
            "link":     f"https://t.me/c/{ch}/{msg_id}" if msg_id else "",
            "created":  str(ad.get("created_at","")),
        })
    return jsonify(result)


@app.route("/api/delete_ad", methods=["POST"])
@require_auth
def api_delete_ad(tg_user):
    uid   = int(tg_user["id"])
    data  = request.json or {}
    ad_id = data.get("ad_id","")
    ad    = db.get_ad(ad_id)

    if not ad:
        return jsonify({"error": "Ad nahi mila"}), 404
    if ad["owner_id"] != uid:
        return jsonify({"error": "Yeh tumhara ad nahi hai"}), 403

    db.delete_ad(ad_id)
    return jsonify({"success": True, "message": "Ad delete ho gaya!"})


@app.route("/api/search", methods=["GET"])
def api_search():
    q       = request.args.get("q","").strip()
    results = db.search_ads(q, limit=5)
    ch      = str(os.getenv("DATABASE_CHANNEL_ID","")).replace("-100","")

    out = []
    for ad in results:
        msg_id = ad.get("db_channel_msg_id")
        out.append({
            "id":      str(ad["_id"]),
            "caption": (ad.get("caption","") or "")[:100],
            "tags":    ad.get("hashtags",[]),
            "link":    f"https://t.me/c/{ch}/{msg_id}" if msg_id else "",
        })
    return jsonify(out)


@app.route("/api/report_ad", methods=["POST"])
@require_auth
def api_report_ad(tg_user):
    uid    = int(tg_user["id"])
    data   = request.json or {}
    ad_id  = data.get("ad_id","")
    reason = data.get("reason","copyright")
    if not ad_id:
        return jsonify({"error": "ad_id required"}), 400
    db.add_report(uid, ad_id, reason)
    return jsonify({"success": True, "message": "Report submit ho gaya!"})


# ═══════════════════════════════════════════════════════════════════
#  ADMIN API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/admin/stats", methods=["GET"])
@require_owner
def api_admin_stats(tg_user):
    stats = db.get_user_stats()
    reports = len(db.get_pending_reports())
    return jsonify({**stats, "pending_reports": reports})


@app.route("/api/admin/delete_ad", methods=["POST"])
@require_owner
def api_admin_delete_ad(tg_user):
    ad_id = (request.json or {}).get("ad_id","")
    ad    = db.get_ad(ad_id)
    if not ad:
        return jsonify({"error": "Ad nahi mila"}), 404
    db.delete_ad(ad_id)
    return jsonify({"success": True})


@app.route("/api/admin/broadcast", methods=["POST"])
@require_owner
def api_admin_broadcast(tg_user):
    # Signal scheduler (scheduler reads from queue)
    import requests as req
    try:
        req.post("http://localhost:8080/internal/trigger_broadcast", timeout=2)
    except Exception:
        pass
    return jsonify({"success": True, "message": "Broadcast queued!"})


@app.route("/api/admin/forcesub_channels", methods=["GET"])
@require_owner
def api_forcesub_list(tg_user):
    channels = db.get_all_forcesub_channels()
    return jsonify([{
        "channel_id": ch["channel_id"],
        "title":      ch.get("title",""),
        "invite_link":ch.get("invite_link",""),
    } for ch in channels])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
