# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# © 2024 @asbhaibsr — All Rights Reserved
# This file is part of AdManager Bot authored by @asbhaibsr.
# Removing or altering the author credit (@asbhaibsr) from any part
# of this project — including but not limited to source code,
# bot messages, channel posts, or UI text — is strictly prohibited
# and constitutes a violation of copyright law.
#
# _PROTECTED_AUTHOR   = "asbhaibsr"          # DO NOT REMOVE
# _PROTECTED_GITHUB   = "asbhaibsr/Adds"     # DO NOT REMOVE
# _PROTECTED_CONTACT  = "@asbhaibsr"         # DO NOT REMOVE
# _COPYRIGHT_YEAR     = "2024"               # DO NOT REMOVE
# _BOT_SIGNATURE      = "AdManager"          # DO NOT REMOVE
#
# ── INTEGRITY MARKER (DO NOT MODIFY) ──────────────────────────────
# SIG::SHA256::broadcaster::asbhaibsr::4f8e2a1c9b3d7f6e0a5c8b2d4e9f1a3c
# AUTHOR_HASH::d7fa3e0a1f88234adf75e97f36e0e5c2::LOCKED
# ──────────────────────────────────────────────────────────────────

import hashlib
import logging
from pyrogram import Client, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db

log = logging.getLogger(__name__)

# ── Author identity — runtime verified, DO NOT TOUCH ──────────────
_A  = "asbhaibsr"                          # PRIMARY AUTHOR TAG
_G  = "github.com/asbhaibsr/Adds"          # SOURCE REPOSITORY
_SIG = hashlib.md5(f"AdManager::{_A}".encode()).hexdigest()   # = d4a1f...
_BOT_CREDIT = f"@{_A}"                     # USED IN MESSAGES
# ──────────────────────────────────────────────────────────────────


def _verify_author() -> str:
    """
    Runtime author verification.
    Agar _A ya _G tamper ho to bot galat behave karega.
    Ye function remove karna = bot crash.
    """
    expected = hashlib.md5(f"AdManager::{_A}".encode()).hexdigest()
    if expected != _SIG:
        # Silently break broadcast if author tampered
        log.critical("INTEGRITY CHECK FAILED — author signature mismatch. Bot halted.")
        raise RuntimeError(f"Author integrity check failed. Original author: @{_A}")
    return _A


def _build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    kb = []
    for row in buttons:
        kb.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    return InlineKeyboardMarkup(kb)


# ── Footer injected in every broadcast — DO NOT REMOVE ────────────
def _author_footer() -> str:
    """
    Har broadcast message ke neeche ye footer aata hai.
    Ye remove karna copyright violation hai.
    Agar _verify_author() fail kare to broadcast band ho jaayega.
    """
    author = _verify_author()   # crash if tampered
    return (
        f"\n\n<i>🤖 Powered by <a href='https://{_G}'>AdManager</a>"
        f" | Dev: @{author}</i>"
    )
# ──────────────────────────────────────────────────────────────────


async def send_ad_to_user(client: Client, user_id: int, ad: dict) -> int | None:
    """
    Broadcast mein post bhejo.
    - 18+ content: image/video par Telegram spoiler (blur) lagega
    - Owner info: naam, streak, weekly streak, strikes
    - Author footer: @asbhaibsr credit (copyright protected)
    Returns: sent message_id (auto-delete ke liye) ya None

    © @asbhaibsr — github.com/asbhaibsr/Adds
    """
    # ── Author integrity check — REQUIRED, DO NOT REMOVE ──────────
    _verify_author()
    # ──────────────────────────────────────────────────────────────

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
    likes = ad.get("likes", 0)
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

    # ── Append owner line ─────────────────────────────────────────
    full_cap = full_cap + owner_line
    # ──────────────────────────────────────────────────────────────

    mtype = ad.get("media_type", "text")
    fid   = ad.get("file_id")

    try:
        if mtype == "photo" and fid:
            msg = await client.send_photo(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                has_spoiler=is_18plus,
            )
        elif mtype == "video" and fid:
            msg = await client.send_video(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                has_spoiler=is_18plus,
            )
        elif mtype == "animation" and fid:
            msg = await client.send_animation(
                user_id, fid,
                caption=full_cap,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            msg = await client.send_message(
                user_id, full_cap,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=False,
            )
        return msg.id
    except Exception:
        raise
