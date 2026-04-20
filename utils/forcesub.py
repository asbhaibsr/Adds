# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    UserNotParticipant, ChatAdminRequired, FloodWait,
    ChannelPrivate, PeerIdInvalid
)
from database import get_all_forcesub_channels

log = logging.getLogger(__name__)


async def _is_user_in_channel(client: Client, ch_id: int, user_id: int) -> bool:
    """
    Membership check — sirf get_chat_member use karo.
    get_chat_join_requests bots nahi kar sakte (BOT_METHOD_INVALID) — completely hata diya.
    """
    try:
        member = await client.get_chat_member(ch_id, user_id)
        status_val = member.status.value if hasattr(member.status, "value") else str(member.status)

        if status_val in ("member", "administrator", "creator", "owner"):
            return True
        if status_val == "restricted":
            return bool(getattr(member, "is_member", False))
        if status_val in ("left", "banned", "kicked"):
            return False
        return True

    except UserNotParticipant:
        return False

    except ChatAdminRequired:
        log.warning(f"Bot not admin in {ch_id} — force sub check skip")
        return True
    except (ChannelPrivate, PeerIdInvalid):
        log.warning(f"Cannot access channel {ch_id} — skipping")
        return True
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 3))
        return True
    except Exception as e:
        log.warning(f"Force sub check error ch={ch_id} user={user_id}: {e}")
        return True


async def check_subscription(client: Client, user_id: int) -> tuple:
    """Returns (all_joined: bool, missing_channels: list[dict])"""
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        joined = await _is_user_in_channel(client, ch["channel_id"], user_id)
        if not joined:
            missing.append(ch)

    return len(missing) == 0, missing


def _is_request_channel(ch: dict) -> bool:
    link = ch.get("invite_link", "") or ""
    return "/+" in link or ch.get("is_request_channel", False)


def build_join_buttons(missing: list) -> "InlineKeyboardMarkup":
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for ch in missing:
        invite_link = ch.get("invite_link", "")
        title       = ch.get("title", "Channel")
        is_req      = _is_request_channel(ch)

        if not invite_link:
            ch_id_str   = str(ch["channel_id"]).replace("-100", "")
            invite_link = f"https://t.me/c/{ch_id_str}"

        label = f"📨 {title} (Join Request Bhejo)" if is_req else f"📢 {title} Join Karo"
        rows.append([InlineKeyboardButton(label, url=invite_link)])

    rows.append([InlineKeyboardButton(
        "✅ Maine Join Kar Liya — Verify Karo",
        callback_data="check_sub"
    )])
    return InlineKeyboardMarkup(rows)
