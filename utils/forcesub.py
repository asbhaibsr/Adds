# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Force Subscribe — VJ Bot style, bot-compatible                 ║
# ╚══════════════════════════════════════════════════════════════════╝

import logging
import asyncio
from pyrogram import Client, enums
from pyrogram.errors import (
    UserNotParticipant, ChatAdminRequired, FloodWait,
    ChannelPrivate, PeerIdInvalid, UsernameInvalid,
    UsernameNotOccupied, ChatIdInvalid
)
from database import get_all_forcesub_channels

log = logging.getLogger(__name__)


async def _is_user_in_channel(client: Client, ch_id: int, user_id: int) -> bool:
    """
    VJ bot style membership check — sirf get_chat_member.
    get_chat_join_requests bots nahi kar sakte — completely removed.
    Sab edge cases handle kiye hain.
    """
    try:
        member = await client.get_chat_member(ch_id, user_id)

        # Pyrogram 2.x mein status ek enum hai
        status = member.status
        if status in (
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ):
            return True
        if status == enums.ChatMemberStatus.RESTRICTED:
            return bool(getattr(member, "is_member", False))
        if status in (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED):
            return False
        return True

    except UserNotParticipant:
        return False  # Join nahi kiya

    except ChatAdminRequired:
        # Bot ko admin nahi banaya — skip check, pass karo
        log.warning(f"Bot not admin in ch={ch_id}, skipping fsub check")
        return True

    except (ChannelPrivate, PeerIdInvalid, ChatIdInvalid,
            UsernameInvalid, UsernameNotOccupied):
        # Channel accessible nahi — pass karo, block mat karo user ko
        log.warning(f"Channel {ch_id} not accessible — skipping")
        return True

    except FloodWait as e:
        await asyncio.sleep(min(e.value, 5))
        return True

    except Exception as e:
        err = str(e).lower()
        # "belongs to a user" — galat channel ID stored hai, skip karo
        if "belongs to a user" in err or "chat_id" in err:
            log.warning(f"Invalid channel ID {ch_id} in DB: {e} — skipping")
            return True
        log.warning(f"fsub check error ch={ch_id} user={user_id}: {e}")
        return True  # Unknown error pe pass karo


async def check_subscription(client: Client, user_id: int) -> tuple:
    """
    Returns: (all_joined: bool, missing_channels: list[dict])
    """
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        try:
            joined = await _is_user_in_channel(client, ch["channel_id"], user_id)
            if not joined:
                missing.append(ch)
        except Exception as e:
            log.warning(f"Skipping channel {ch.get('channel_id')}: {e}")
            continue  # Error wale channel ko skip karo, block mat karo user

    return len(missing) == 0, missing


def _is_request_channel(ch: dict) -> bool:
    """Request-join channel detect karo via invite link."""
    link = ch.get("invite_link", "") or ""
    return "/+" in link or ch.get("is_request_channel", False)


def build_join_buttons(missing: list) -> "InlineKeyboardMarkup":
    """Missing channels ke liye join buttons banao."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for ch in missing:
        invite_link = ch.get("invite_link", "")
        title       = ch.get("title", "Channel")
        is_req      = _is_request_channel(ch)

        if not invite_link:
            ch_id_str   = str(ch["channel_id"]).replace("-100", "")
            invite_link = f"https://t.me/c/{ch_id_str}"

        label = f"📨 {title}" if is_req else f"📢 {title} Join Karo"
        rows.append([InlineKeyboardButton(label, url=invite_link)])

    rows.append([InlineKeyboardButton(
        "✅ Maine Join Kar Liya — Verify Karo",
        callback_data="check_sub"
    )])
    return InlineKeyboardMarkup(rows)
