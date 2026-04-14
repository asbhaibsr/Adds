from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    """
    buttons is a list of rows, each row is a list of {"text": str, "url": str}.
    Returns InlineKeyboardMarkup or None.
    """
    if not buttons:
        return None
    kb = []
    for row in buttons:
        kb.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    return InlineKeyboardMarkup(kb)


async def send_ad_to_user(client: Client, user_id: int, ad: dict):
    keyboard = _build_keyboard(ad.get("buttons", []))
    caption  = ad.get("caption", "")
    mtype    = ad.get("media_type", "text")
    fid      = ad.get("file_id")

    if mtype == "photo" and fid:
        await client.send_photo(user_id, fid, caption=caption, reply_markup=keyboard)
    elif mtype == "video" and fid:
        await client.send_video(user_id, fid, caption=caption, reply_markup=keyboard)
    elif mtype == "animation" and fid:
        await client.send_animation(user_id, fid, caption=caption, reply_markup=keyboard)
    else:
        await client.send_message(user_id, caption, reply_markup=keyboard, disable_web_page_preview=False)
