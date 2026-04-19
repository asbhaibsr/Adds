# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db


def _build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    """
    buttons = list of rows, each row = list of {"text": str, "url": str}.
    Returns InlineKeyboardMarkup or None.
    """
    if not buttons:
        return None
    kb = []
    for row in buttons:
        kb.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    return InlineKeyboardMarkup(kb)


async def send_ad_to_user(client: Client, user_id: int, ad: dict):
    """
    Broadcast mein post bhejo.
    FIX: Like button + Delete button (sirf owner ke liye) add karo.
    Channel link nahi dena -- seedha PM mein content aata hai.
    """
    ad_id   = str(ad["_id"])
    kb_data = ad.get("buttons", [])
    kb_rows = []

    # User ke custom buttons
    for row in kb_data:
        kb_rows.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])

    # Like button + Delete button -- sabhi users ko milega
    liked = db.has_liked(ad_id, user_id)
    likes = ad.get("likes", 0)
    like_row = [
        InlineKeyboardButton(
            f"Like {likes}",
            callback_data=f"like_post_{ad_id}_0"
        ),
        InlineKeyboardButton(
            "Delete",
            callback_data=f"del_broadcast_{ad_id}"
        ),
    ]

    kb_rows.append(like_row)
    keyboard = InlineKeyboardMarkup(kb_rows) if kb_rows else None

    caption  = ad.get("caption", "")
    tags     = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    full_cap = f"{caption}\n\n{tags}".strip() if tags else caption

    mtype = ad.get("media_type", "text")
    fid   = ad.get("file_id")

    if mtype == "photo" and fid:
        await client.send_photo(user_id, fid, caption=full_cap, reply_markup=keyboard)
    elif mtype == "video" and fid:
        await client.send_video(user_id, fid, caption=full_cap, reply_markup=keyboard)
    elif mtype == "animation" and fid:
        await client.send_animation(user_id, fid, caption=full_cap, reply_markup=keyboard)
    else:
        await client.send_message(user_id, full_cap, reply_markup=keyboard, disable_web_page_preview=False)
