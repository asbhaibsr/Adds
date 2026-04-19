# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait
from database import get_all_forcesub_channels

log = logging.getLogger(__name__)


async def check_subscription(client: Client, user_id: int) -> tuple:
    """
    Returns (all_joined: bool, missing_channels: list[dict])

    FIX: Request channels ke liye bhi sahi check hota hai.
    Agar bot admin nahi hai to user ko through jaane deta hai.
    """
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        ch_id = ch["channel_id"]
        try:
            member     = await client.get_chat_member(ch_id, user_id)
            status_val = member.status.value if hasattr(member.status, "value") else str(member.status)

            if status_val in ("banned", "left"):
                missing.append(ch)
            elif status_val == "restricted":
                if not getattr(member, "is_member", True):
                    missing.append(ch)
            # member, administrator, creator = OK

        except UserNotParticipant:
            missing.append(ch)

        except ChatAdminRequired:
            log.warning(f"Bot is not admin in channel {ch_id}, skipping check.")
            # Bot admin nahi -- let user through (don't add to missing)

        except FloodWait as e:
            log.warning(f"FloodWait {e.value}s while checking subscription for {user_id}")
            await asyncio.sleep(min(e.value, 5))
            # After sleep, let user through to avoid blocking them
            pass

        except Exception as e:
            err = str(e).lower()
            if "chat_admin_required" in err or "channel_private" in err:
                log.warning(f"Cannot check {ch_id} (no access): {e}")
            else:
                log.warning(f"Subscription check error for user {user_id} in {ch_id}: {e}")
            # On unknown errors, don't block user

    return len(missing) == 0, missing


def build_join_buttons(missing: list) -> "InlineKeyboardMarkup":
    """
    Build InlineKeyboard for missing channels.
    FIX: Request channel link properly set hoti hai (join_request link).
    """
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for ch in missing:
        invite_link = ch.get("invite_link", "")
        title       = ch.get("title", "Channel")

        if not invite_link:
            ch_id_str  = str(ch["channel_id"]).replace("-100", "")
            invite_link = f"https://t.me/c/{ch_id_str}"

        rows.append([InlineKeyboardButton(
            f"Join {title}",
            url=invite_link
        )])

    rows.append([InlineKeyboardButton(
        "Maine Join Kar Liya -- Verify Karo",
        callback_data="check_sub"
    )])
    return InlineKeyboardMarkup(rows)
