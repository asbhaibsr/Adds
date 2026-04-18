# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from database import get_all_forcesub_channels


async def check_subscription(client: Client, user_id: int) -> tuple[bool, list]:
    """
    Returns (all_joined: bool, missing_channels: list[dict])
    missing_channels: [{"channel_id", "invite_link", "title"}, ...]
    """
    channels = get_all_forcesub_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)
            # banned or left = not subscribed
            if member.status.value in ("banned", "left", "restricted"):
                missing.append(ch)
        except UserNotParticipant:
            missing.append(ch)
        except Exception:
            pass                        # If we can't check, let user through

    return len(missing) == 0, missing


def build_join_buttons(missing: list) -> list:
    """Build InlineKeyboard rows for all missing channels."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for ch in missing:
        link = ch.get("invite_link") or f"https://t.me/c/{str(ch['channel_id']).replace('-100', '')}"
        rows.append([InlineKeyboardButton(
            f"✅ Join {ch.get('title', 'Channel')}",
            url=link
        )])
    rows.append([InlineKeyboardButton("🔄 I've Joined — Check Again", callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)
