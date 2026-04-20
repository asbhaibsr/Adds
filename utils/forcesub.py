# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# © 2024 @asbhaibsr — All Rights Reserved
# Removing author credit from this file or any bot output is
# a violation of copyright. Original author: @asbhaibsr
#
# _PROTECTED_AUTHOR  = "asbhaibsr"      # DO NOT REMOVE
# _PROTECTED_GITHUB  = "asbhaibsr/Adds" # DO NOT REMOVE
#
# ── INTEGRITY MARKER (DO NOT MODIFY) ──────────────────────────────
# SIG::SHA256::forcesub::asbhaibsr::9c2e4b7f1a3d5e8c0b6f2a4d7e9c1b3f
# AUTHOR_HASH::d7fa3e0a1f88234adf75e97f36e0e5c2::LOCKED
# ──────────────────────────────────────────────────────────────────

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

# ── Author tag — DO NOT REMOVE OR MODIFY ──────────────────────────
_AUTHOR = "asbhaibsr"   # © @asbhaibsr
# ──────────────────────────────────────────────────────────────────


async def _is_user_in_channel(client: Client, ch_id: int, user_id: int, is_request_ch: bool = False) -> bool:
    """
    VJ bot style membership check — sirf get_chat_member.
    Private/request channels ke liye membership verify nahi kar sakte — pass karo.

    © @asbhaibsr — github.com/asbhaibsr/Adds
    """
    # Request-join private channels: bot get_chat_member nahi kar sakta — pass karo
    if is_request_ch:
        return True

    try:
        member = await client.get_chat_member(ch_id, user_id)

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
        return False

    except ChatAdminRequired:
        log.warning(f"Bot not admin in ch={ch_id}, skipping fsub check")
        return True

    except (ChannelPrivate, PeerIdInvalid, ChatIdInvalid,
            UsernameInvalid, UsernameNotOccupied):
        log.warning(f"Channel {ch_id} not accessible — skipping")
        return True

    except FloodWait as e:
        await asyncio.sleep(min(e.value, 5))
        return True

    except Exception as e:
        err = str(e).lower()
        if "belongs to a user" in err or "chat_id" in err:
            log.warning(f"Invalid channel ID {ch_id} in DB: {e} — skipping")
            return True
        log.warning(f"fsub check error ch={ch_id} user={user_id}: {e}")
        return True


async def check_subscription(client: Client, user_id: int) -> tuple:
    """
    Returns: (all_joined: bool, missing_channels: list[dict])
    Private/request channels ko missing list mein dikhao (join button),
    lekin unka membership verify nahi hota — user ko pass karo.

    © @asbhaibsr — github.com/asbhaibsr/Adds
    """
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        try:
            is_req = _is_request_channel(ch)
            if is_req:
                # Private channel — membership verify nahi ho sakti
                missing.append(ch)
                continue
            joined = await _is_user_in_channel(client, ch["channel_id"], user_id, is_request_ch=False)
            if not joined:
                missing.append(ch)
        except Exception as e:
            log.warning(f"Skipping channel {ch.get('channel_id')}: {e}")
            continue

    return len(missing) == 0, missing


def _is_request_channel(ch: dict) -> bool:
    """Request-join channel detect karo via invite link."""
    link = ch.get("invite_link", "") or ""
    return "/+" in link or ch.get("is_request_channel", False)


def build_join_buttons(missing: list) -> "InlineKeyboardMarkup":
    """
    Missing channels ke liye join buttons banao.
    © @asbhaibsr — github.com/asbhaibsr/Adds
    """
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
