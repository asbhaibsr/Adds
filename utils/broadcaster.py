# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db


def _build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    kb = []
    for row in buttons:
        kb.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    return InlineKeyboardMarkup(kb)


async def send_ad_to_user(client: Client, user_id: int, ad: dict) -> int | None:
    """
    Broadcast mein post bhejo.
    - 18+ content: image/video par Telegram spoiler (blur) lagega
    - Owner info: naam, streak, weekly streak, strikes
    Returns: sent message_id (auto-delete ke liye) ya None
    """
    ad_id     = str(ad["_id"])
    owner_id  = ad.get("owner_id")
    is_18plus = ad.get("is_18plus", False)
    kb_data   = ad.get("buttons", [])
    kb_rows   = []

    # ── Owner info ──────────────────────────────────────────────
    owner      = db.get_user(owner_id) if owner_id else None
    owner_line = ""
    if owner:
        name          = owner.get("full_name") or owner.get("username") or f"User {owner_id}"
        streak        = owner.get("streak", 0)
        weekly_streak = owner.get("weekly_streak", 0)
        strikes       = owner.get("strikes", 0)
        owner_line = (
            f"\n\n👤 <b>{name}</b>"
            f"  🔥 <b>{streak}</b> streak"
            f"  📅 <b>{weekly_streak}</b> weekly"
            f"  ⚠️ <b>{strikes}</b> strikes"
        )

    # ── Custom buttons ───────────────────────────────────────────
    for row in kb_data:
        kb_rows.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])

    # ── Like + Delete row ────────────────────────────────────────
    likes    = ad.get("likes", 0)
    kb_rows.append([
        InlineKeyboardButton(f"❤️ Like {likes}", callback_data=f"like_post_{ad_id}_0"),
        InlineKeyboardButton("🗑 Delete",         callback_data=f"del_broadcast_{ad_id}"),
    ])
    keyboard = InlineKeyboardMarkup(kb_rows)

    # ── Caption ──────────────────────────────────────────────────
    caption  = ad.get("caption", "")
    tags     = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    full_cap = f"{caption}\n\n{tags}".strip() if tags else caption

    # 18+ watermark — blue bold text
    if is_18plus:
        full_cap = f"🔵 <b>18+ CONTENT</b> 🔵\n\n{full_cap}"

    full_cap = full_cap + owner_line

    mtype = ad.get("media_type", "text")
    fid   = ad.get("file_id")

    try:
        if mtype == "photo" and fid:
            # 18+ photo → has_spoiler=True (Telegram blur)
            msg = await client.send_photo(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode="html",
                has_spoiler=is_18plus,
            )
        elif mtype == "video" and fid:
            # 18+ video → has_spoiler=True (Telegram blur)
            msg = await client.send_video(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode="html",
                has_spoiler=is_18plus,
            )
        elif mtype == "animation" and fid:
            msg = await client.send_animation(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode="html",
            )
        else:
            msg = await client.send_message(
                user_id, full_cap,
                reply_markup=keyboard,
                parse_mode="html",
                disable_web_page_preview=False,
            )
        return msg.id
    except Exception:
        raise
