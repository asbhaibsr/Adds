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


async def _is_user_in_channel(client: Client, ch_id: int, user_id: int, is_request_ch: bool = False) -> bool:
    """
    Advanced membership check.
    - Public/normal channels: get_chat_member
    - Request channels (t.me/+hash): get_chat_join_requests fallback
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
        return True  # Unknown status — pass through

    except UserNotParticipant:
        if is_request_ch:
            return await _check_request_join(client, ch_id, user_id)
        return False

    except ChatAdminRequired:
        log.warning(f"Bot not admin in {ch_id}, skipping check.")
        return True
    except (ChannelPrivate, PeerIdInvalid):
        log.warning(f"Cannot access {ch_id}. Skipping.")
        return True
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 3))
        return True
    except Exception as e:
        log.warning(f"check error ch={ch_id} user={user_id}: {e}")
        return True


async def _check_request_join(client: Client, ch_id: int, user_id: int) -> bool:
    """
    Request channel join check using get_chat_join_requests.
    Pending request = lenient pass (user ne try kiya).
    No request = failed.
    """
    try:
        async for req in client.get_chat_join_requests(ch_id):
            if req.user.id == user_id:
                log.info(f"User {user_id} has pending join request for {ch_id} — passing (lenient).")
                return True
        return False
    except ChatAdminRequired:
        log.warning(f"No join_request admin permission for {ch_id}. Passing user.")
        return True
    except Exception as e:
        log.warning(f"Request join check failed ch={ch_id}: {e}")
        return True


def _is_request_channel(ch: dict) -> bool:
    """Detect request channel via invite_link pattern (t.me/+hash)."""
    link = ch.get("invite_link", "") or ""
    return "/+" in link or ch.get("is_request_channel", False)


async def check_subscription(client: Client, user_id: int) -> tuple:
    """
    Returns (all_joined: bool, missing_channels: list[dict])
    Handles both normal and request-join channels correctly.
    """
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        joined = await _is_user_in_channel(
            client, ch["channel_id"], user_id, _is_request_channel(ch)
        )
        if not joined:
            missing.append(ch)

    return len(missing) == 0, missing


def build_join_buttons(missing: list) -> "InlineKeyboardMarkup":
    """Build join buttons for missing channels."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for ch in missing:
        invite_link = ch.get("invite_link", "")
        title = ch.get("title", "Channel")
        is_req = _is_request_channel(ch)

        if not invite_link:
            ch_id_str = str(ch["channel_id"]).replace("-100", "")
            invite_link = f"https://t.me/c/{ch_id_str}"

        label = f"📨 {title} (Join Request Bhejo)" if is_req else f"📢 {title} Join Karo"
        rows.append([InlineKeyboardButton(label, url=invite_link)])

    rows.append([InlineKeyboardButton(
        "✅ Maine Join Kar Liya — Verify Karo",
        callback_data="check_sub"
    )])
    return InlineKeyboardMarkup(rows)
