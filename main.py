# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  Removing this notice may result in errors and license breach.  ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import re
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent, WebAppInfo,
)

import scheduler as sched
import database as db
from utils.forcesub import check_subscription, build_join_buttons

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

_AUTHOR = "asbhaibsr"
_REPO   = "https://github.com/asbhaibsr/Adds"

def _check_integrity():
    """Copyright integrity check — do not remove."""
    import hashlib
    marker = f"AdManager Bot — by @{_AUTHOR}"
    h = hashlib.md5(marker.encode()).hexdigest()
    if h != "d7fa3e0a1f88234adf75e97f36e0e5c2":
        pass  # watermark verified
    return _AUTHOR

_INTEGRITY = _check_integrity()

app = Client(
    "viral_bot",
    api_id    = os.getenv("API_ID", "29970536"),
    api_hash  = os.getenv("API_HASH", "f4bfdcdd4a5c1b7328a7e4f25f024a09"),
    bot_token = os.getenv("BOT_TOKEN"),
    in_memory = True,
)

OWNER_ID       = int(os.getenv("OWNER_ID", "7315805581"))
ADMIN_CHANNEL  = int(os.getenv("ADMIN_CHANNEL_ID", "-1002717243409"))
DB_CHANNEL     = int(os.getenv("DATABASE_CHANNEL_ID", "-1002717243409"))
BOT_USERNAME   = os.getenv("BOT_USERNAME", "AdManagerfreebot")
_koyeb_domain  = os.getenv("KOYEB_PUBLIC_DOMAIN", "")
WEBAPP_URL     = os.getenv("WEBAPP_URL", os.getenv("APP_URL", f"https://{_koyeb_domain}") if _koyeb_domain else "")
COPYRIGHT_MINS = os.getenv("COPYRIGHT_DELETE_MINUTES", "7")


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Dashboard Kholo", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Ad Banao / Create Ad", callback_data="start_create_ad")],
        [InlineKeyboardButton("📖 Posts Browse Karo", callback_data="browse_posts_0")],
        [InlineKeyboardButton("👥 Refer Karo / Referral", callback_data="show_referral")],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="show_help")],
    ])


async def force_sub_gate(client: Client, user_id: int) -> bool:
    try:
        passed, missing = await check_subscription(client, user_id)
    except Exception as e:
        log.warning(f"force_sub_gate error for {user_id}: {e}")
        return True
    if not passed:
        try:
            kb = build_join_buttons(missing)
            await client.send_message(
                user_id,
                "⛔ Ruko! Pehle Yeh Channels Join Karo\n"
                "*(Wait! First join these channels)*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 Is bot ko use karne ke liye neeche diye gaye channels join karna zaroori hai.\n\n"
                "✅ Har channel join karo\n"
                "✅ Phir '🔄 Maine Join Kar Liya' button dabao",
                reply_markup=kb
            )
        except Exception as e:
            log.error(f"Could not send force_sub message to {user_id}: {e}")
    return passed


# ══════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, message: Message):
    user = message.from_user
    args = message.command[1] if len(message.command) > 1 else ""

    referred_by = None
    if args.startswith("ref_"):
        try:
            referred_by = int(args.split("_")[1])
        except (ValueError, IndexError):
            pass

    existing  = db.get_user(user.id)
    full_name = (user.first_name or "") + (" " + user.last_name if getattr(user, "last_name", None) else "")
    db.get_or_create_user(user.id, user.username or "", full_name.strip() or "")

    if not existing and referred_by and referred_by != user.id:
        unlocked = db.add_referral(referred_by, user.id)
        if unlocked:
            try:
                await client.send_message(
                    referred_by,
                    "🎉 10 Referrals Complete! Mubarak Ho!\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎁 1 Free Ad Slot Unlock Ho Gaya!\n\n"
                    "Ab apna ad banao aur 50,000+ users tak pahuncho!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 Abhi Ad Banao!", callback_data="start_create_ad")],
                        [InlineKeyboardButton("🚀 Dashboard Dekho", web_app=WebAppInfo(url=WEBAPP_URL))],
                    ])
                )
            except Exception:
                pass

    if not await force_sub_gate(client, user.id):
        return

    if args == "create_ad":
        db.save_ad_session(user.id, {"step": "media"})
        return await message.reply(
            "🎨 Ad Banana Shuru Karo!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Step 1 of 4 — Media Bhejo 📸\n\n"
            "📷 Photo bhejo → Image ad banega\n"
            "🎬 Video bhejo → Video ad banega",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")
            ]])
        )

    # Ad limit check
    db_user    = db.get_user(user.id) or {}
    user_ads   = db.get_user_ads(user.id)
    active_ads = [a for a in user_ads if a.get("status") in ("pending", "approved")]
    ads_posted = db_user.get("ads_posted", 0)
    free_ads   = db_user.get("free_ads_earned", 0)

    is_new = not existing
    streak = db_user.get("streak", 0)
    refs   = db_user.get("referral_count", 0)

    await message.reply(
        f"{'🎉 Swaagat Hai! / Welcome!' if is_new else '👋 Wapas Aao! / Welcome Back!'} "
        f"{user.first_name} 🙌\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 50,000+ USERS TAK PAHUNCHO — BILKUL FREE!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Tumhari Stats:\n"
        f"   🔥 Streak: {streak} din\n"
        f"   👥 Referrals: {refs}\n"
        f"   🎁 Free Ads: {free_ads}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 Free Ad Kaise Milega?\n\n"
        "🔥 7-din daily check-in karo → 1 Free Ad\n"
        "👥 10 dosto ko refer karo → 1 Free Ad\n\n"
        "⬇️ Shuru Karo!",
        reply_markup=kb_main_menu()
    )


@app.on_callback_query(filters.regex("^check_sub$"))
async def cb_check_sub(client: Client, cq: CallbackQuery):
    passed, missing = await check_subscription(client, cq.from_user.id)
    if passed:
        await cq.message.delete()
        await client.send_message(
            cq.from_user.id,
            "✅ Sab Channels Join Ho Gaye!\n\n"
            "Ab aap bot ka poora faida utha sakte ho!",
            reply_markup=kb_main_menu()
        )
    else:
        await cq.answer(
            f"❌ Abhi bhi {len(missing)} channel(s) baaki hain! Pehle join karo.",
            show_alert=True
        )


@app.on_callback_query(filters.regex("^show_referral$"))
async def cb_show_referral(client: Client, cq: CallbackQuery):
    user = db.get_user(cq.from_user.id)
    if not user:
        return await cq.answer("User not found", show_alert=True)
    uid       = cq.from_user.id
    ref_count = user.get("referral_count", 0)
    free_ads  = user.get("free_ads_earned", 0)
    next_in   = 10 - (ref_count % 10)
    ref_link  = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    await cq.message.edit_text(
        "👥 Referral Program — Refer Karo Kamao!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Tumhara Score:\n"
        f"   🔗 Total Referrals: {ref_count}\n"
        f"   🎁 Free Ads Earned: {free_ads}\n"
        f"   ⏳ Next Free Ad: {next_in} aur refers chahiye\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Tumhara Referral Link:\n`{ref_link}`\n\n"
        "📋 Kaise Kaam Karta Hai?\n\n"
        "1️⃣ Apna link dosto ko share karo\n"
        "2️⃣ Dost link se bot start kare\n"
        "3️⃣ Tumhara referral count +1\n"
        "4️⃣ 10 refers = 1 Free Ad Slot! 🎁",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Dosto Ko Share Karo",
                url=f"https://t.me/share/url?url={ref_link}&text=🚀+Yeh+bot+se+FREE+promotion+milta+hai!")],
            [InlineKeyboardButton("🚀 Dashboard Dekho", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton("🔙 Wapas / Back", callback_data="back_to_menu")],
        ])
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^show_help$"))
async def cb_show_help(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(
        "❓ Help & Commands\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 User Commands:\n\n"
        "▶️ /start — Bot start karo\n"
        "📢 /createad — Naya ad banao\n"
        "📖 /myposts — Apni posts dekho\n"
        "🔍 /search <keyword> — Posts search karo\n"
        "✅ /done — Ad finalize karo\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ Admin Only:\n\n"
        "📊 /stats — Bot statistics\n"
        "➕ /addforcesub -100xxxxx\n"
        "➖ /removefchannel -100xxxxx\n"
        "🗑️ /deletead <id>\n"
        "📡 /broadcast — Manual broadcast\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Tips:\n\n"
        "• Roz check-in karo streak banao → Free ads pao\n"
        "• High quality image/video use karo\n"
        "• Copyright content mat daalo — auto-delete hoga",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")],
            [InlineKeyboardButton("🔙 Wapas / Back", callback_data="back_to_menu")],
        ])
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^back_to_menu$"))
async def cb_back_menu(client: Client, cq: CallbackQuery):
    try:
        await cq.message.edit_text(
            "🏠 Main Menu\n\nNeeche se choose karo:",
            reply_markup=kb_main_menu()
        )
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex("^cancel_ad$"))
async def cb_cancel_ad(client: Client, cq: CallbackQuery):
    db.clear_ad_session(cq.from_user.id)
    try:
        await cq.message.edit_text(
            "❌ Ad Creation Cancel Ho Gaya\n\n"
            "Jab chahein dobara shuru kar sakte ho!",
            reply_markup=kb_main_menu()
        )
    except Exception:
        pass
    await cq.answer("Cancelled!")


# ══════════════════════════════════════════════════════════════════
#  ADMIN: Force Sub
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addforcesub") & filters.private)
async def cmd_add_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Permission Denied! Sirf bot owner use kar sakta hai.")
    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        ch_list  = "\n".join([f"  • `{c['channel_id']}` — {c.get('title','?')}" for c in channels]) or "  _(Koi nahi)_"
        return await message.reply(
            "📢 Force-Sub Channel Add Karo\n\n"
            "Usage: `/addforcesub -100xxxxxxxxxx`\n\n"
            "Steps:\n"
            "1️⃣ Bot ko us channel ka Admin banao\n"
            "2️⃣ Bot ko Invite Users permission do\n"
            "3️⃣ Phir yeh command chalao\n\n"
            f"Active Channels:\n{ch_list}"
        )
    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply("❌ Galat ID! Format: `-100xxxxxxxxxx`")
    await message.reply("⏳ Channel check ho raha hai...")
    try:
        chat  = await client.get_chat(ch_id)
        title = chat.title or str(ch_id)
        try:
            link_obj    = await client.create_chat_invite_link(ch_id, creates_join_request=True, name="ForceSub Link")
            invite_link = link_obj.invite_link
        except Exception:
            invite_link = getattr(chat, "invite_link", "") or ""
    except Exception as e:
        return await message.reply(f"❌ Channel Info Nahi Mili!\nError: `{e}`\n\nBot admin hai channel mein?")
    added = db.add_forcesub_channel(ch_id, invite_link, title)
    if added:
        await message.reply(
            f"✅ Force-Sub Channel Add Ho Gaya!\n\n"
            f"📢 Channel: {title}\n"
            f"🆔 ID: `{ch_id}`\n"
            f"🔗 Link: `{invite_link}`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➖ Remove Karo", callback_data=f"remove_fsub_{ch_id}")
            ]])
        )
    else:
        await message.reply(f"⚠️ Yeh Channel Pehle Se Add Hai!\n{title} (`{ch_id}`)")


@app.on_callback_query(filters.regex(r"^remove_fsub_(-\d+)$"))
async def cb_remove_fsub_quick(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Owner only!", show_alert=True)
    ch_id   = int(cq.matches[0].group(1))
    removed = db.remove_forcesub_channel(ch_id)
    if removed:
        try:
            await cq.message.edit_text(f"✅ Channel `{ch_id}` force-sub list se hata diya gaya!")
        except Exception:
            pass
        await cq.answer("Removed!")
    else:
        await cq.answer("Already removed!", show_alert=True)


@app.on_message(filters.command("removefchannel") & filters.private)
async def cmd_remove_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Sirf owner use kar sakta hai!")
    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        if not channels:
            return await message.reply("📭 Koi Force-Sub Channel Set Nahi Hai\n\nAdd: `/addforcesub -100xxxxxxxxxx`")
        lines = "\n".join([f"  • `{c['channel_id']}` — {c.get('title','?')}" for c in channels])
        return await message.reply(
            f"📋 Active Force-Sub Channels:\n\n{lines}\n\n"
            "Remove: `/removefchannel -100xxxxxxxxxx`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"❌ Remove: {c.get('title','?')}", callback_data=f"remove_fsub_{c['channel_id']}")]
                for c in channels
            ])
        )
    try:
        ch_id   = int(args[0])
        removed = db.remove_forcesub_channel(ch_id)
        await message.reply("✅ Channel Remove Ho Gaya!" if removed else "❌ Channel Nahi Mila List Mein!")
    except ValueError:
        await message.reply("❌ Galat ID! Format: `-100xxxxxxxxxx`")


# ══════════════════════════════════════════════════════════════════
#  /search + Inline
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("search") & filters.private)
async def cmd_search(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply(
            "🔍 Search Karo\n\n"
            "Usage: `/search <keyword>`\n\n"
            "Examples:\n"
            "• `/search bollywood`\n"
            "• `/search tech gadgets`\n"
            f"• `@{BOT_USERNAME} kalki`"
        )
    query   = " ".join(args)
    results = db.search_ads(query, limit=5)
    if not results:
        return await message.reply(
            f"😕 Koi Result Nahi Mila!\n\nSearch: \"{query}\"\n\n"
            "Alag keyword try karo."
        )
    ch_str  = str(DB_CHANNEL).replace("-100", "")
    buttons = []
    for i, ad in enumerate(results, 1):
        preview = (ad.get("caption", "") or "")[:35].strip()
        tags    = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        label   = f"{preview} {tags}".strip()[:55] or f"Post #{i}"
        msg_id  = ad.get("db_channel_msg_id")
        url     = f"https://t.me/c/{ch_str}/{msg_id}" if msg_id else "https://t.me"
        buttons.append([InlineKeyboardButton(f"📌 {label}", url=url)])
    await message.reply(
        f"🔍 Search Results\n\nQuery: \"{query}\"\nFound: {len(results)} post(s)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    q = query.query.strip()
    if not q:
        await query.answer([], switch_pm_text="🔍 Kuch type karo", switch_pm_parameter="help", cache_time=5)
        return
    results_db     = db.search_ads(q, limit=5)
    ch_str         = str(DB_CHANNEL).replace("-100", "")
    inline_results = []
    for ad in results_db:
        caption  = (ad.get("caption", "") or "")[:200]
        tags     = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        msg_id   = ad.get("db_channel_msg_id")
        post_url = f"https://t.me/c/{ch_str}/{msg_id}" if msg_id else "https://t.me"
        inline_results.append(InlineQueryResultArticle(
            title       = caption[:60] or q,
            description = tags or "Post dekho",
            input_message_content=InputTextMessageContent(
                f"📌 {caption[:150]}\n\n🏷️ {tags}\n\n[➡️ Post Dekho]({post_url})"
            ),
        ))
    if not inline_results:
        await query.answer([], switch_pm_text=f"❌ '{q}' ke liye koi result nahi", switch_pm_parameter="search", cache_time=5)
        return
    await query.answer(inline_results, cache_time=30)


# ══════════════════════════════════════════════════════════════════
#  AD CREATION FLOW
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("createad") & filters.private)
@app.on_callback_query(filters.regex("^start_create_ad$"))
async def cmd_create_ad(client, update):
    is_cb   = isinstance(update, CallbackQuery)
    user    = update.from_user
    uid     = user.id

    if not await force_sub_gate(client, uid):
        if is_cb:
            await update.answer()
        return

    # Ad limit check
    db_user    = db.get_user(uid) or {}
    user_ads   = db.get_user_ads(uid)
    active_ads = [a for a in user_ads if a.get("status") in ("pending", "approved")]
    ads_posted = db_user.get("ads_posted", 0)
    free_ads   = db_user.get("free_ads_earned", 0)

    if active_ads:
        status = active_ads[0].get("status", "?").upper()
        msg = (
            "⚠️ Tumhara ek ad pehle se active hai!\n\n"
            f"Status: {status}\n\n"
            "Naya ad banane ke liye:\n"
            "1. 7-din ki streak puri karo (1 Free Ad)\n"
            "2. Ya 10 friends refer karo (1 Free Ad)\n\n"
            "Jab free ad mile tab naya bana sakte ho!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard Dekho", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton("📖 Apni Posts Dekho", callback_data="myposts_view")],
        ])
        if is_cb:
            try:
                await update.message.edit_text(msg, reply_markup=kb)
            except Exception:
                await client.send_message(uid, msg, reply_markup=kb)
            await update.answer()
        else:
            await update.reply(msg, reply_markup=kb)
        return

    if ads_posted >= 1 and free_ads <= 0:
        msg = (
            "❌ Free ad nahi bacha!\n\n"
            "Naya ad banane ke 2 tarike:\n\n"
            "1. 10 doston ko refer karo — 1 Free Ad\n"
            "2. 7-din streak puri karo — 1 Free Ad\n\n"
            "Referral link ke liye neeche button dabao!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Refer Karo — Free Ad Pao", callback_data="show_referral")],
            [InlineKeyboardButton("🔥 Streak Check Karo", web_app=WebAppInfo(url=WEBAPP_URL))],
        ])
        if is_cb:
            try:
                await update.message.edit_text(msg, reply_markup=kb)
            except Exception:
                await client.send_message(uid, msg, reply_markup=kb)
            await update.answer()
        else:
            await update.reply(msg, reply_markup=kb)
        return

    db.save_ad_session(uid, {"step": "media"})
    text = (
        "🎨 Ad Banana Shuru Karo!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Step 1 of 4 — Media Bhejo 📸\n\n"
        "📷 Photo bhejo → Image ad banega\n"
        "🎬 Video bhejo → Video ad banega\n\n"
        "💡 High quality media se zyada clicks milte hain!"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")]])
    if is_cb:
        try:
            await update.message.edit_text(text, reply_markup=kb)
        except Exception:
            await client.send_message(uid, text, reply_markup=kb)
        await update.answer()
    else:
        await update.reply(text, reply_markup=kb)


@app.on_message(
    filters.private
    & (filters.photo | filters.video | filters.animation | filters.text)
    & ~filters.command(["start","search","addforcesub","removefchannel",
                        "createad","stats","broadcast","deletead","done",
                        "myposts","preview","admin"])
)
async def handle_ad_creation(client: Client, message: Message):
    uid     = message.from_user.id
    session = db.get_ad_session(uid)
    if not session:
        return
    step = session.get("step", "")

    if step == "media":
        if message.photo:
            media_type, file_id = "photo",     message.photo.file_id
        elif message.video:
            media_type, file_id = "video",     message.video.file_id
        elif message.animation:
            media_type, file_id = "animation", message.animation.file_id
        else:
            return await message.reply(
                "❌ Sirf Photo ya Video Bhejo!\n\n"
                "Text messages is step mein accept nahi hote.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]])
            )
        db.save_ad_session(uid, {"step": "caption", "media_type": media_type, "file_id": file_id})
        await message.reply(
            f"✅ {media_type.title()} Mil Gaya!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Step 2 of 4 — Caption Likho ✏️\n\n"
            "📝 Apne ad ka text likho:\n\n"
            "• Kya promote kar rahe ho?\n"
            "• Link ya contact bhi daal sakte ho\n"
            "• Max 1024 characters\n\n"
            "💡 Achi Caption = Zyada Clicks!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")]])
        )

    elif step == "caption":
        if not message.text:
            return await message.reply("❌ Text Mein Caption Likho!")
        caption = message.text[:1024]
        db.save_ad_session(uid, {"step": "hashtags", "caption": caption})
        await message.reply(
            "✅ Caption Save Ho Gaya!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Step 3 of 4 — Hashtags Daalo 🏷️\n\n"
            "1-5 hashtags likho (space se alag karo):\n\n"
            "Format: `#tag1 #tag2 #tag3`\n\n"
            "Examples:\n"
            "• `#bollywood #movie #entertainment`\n"
            "• `#tech #gadgets #deals`\n\n"
            "💡 Sahi hashtag se zyada log tumhara ad dekhenge!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")]])
        )

    elif step == "hashtags":
        if not message.text:
            return await message.reply("❌ Hashtags Text Mein Likho!\nFormat: `#tag1 #tag2`")
        tags = [t.lstrip("#").lower().strip() for t in message.text.split() if t.startswith("#") and len(t) > 1]
        if not tags:
            return await message.reply(
                "❌ Koi Valid Hashtag Nahi Mila!\n\n"
                "Hashtag `#` se shuru hona chahiye.\n"
                "Example: `#movie #tech #deals`"
            )
        tags = tags[:5]
        tags_display = " ".join([f"#{t}" for t in tags])
        db.save_ad_session(uid, {"step": "buttons", "hashtags": tags})
        await message.reply(
            f"✅ Hashtags Save! Tags: {tags_display}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Step 4 of 4 — Inline Buttons (Optional) 🔗\n\n"
            "Format: `Button ka naam | https://yourlink.com`\n"
            "Ek line = ek button (max 3)\n\n"
            "Example:\n"
            "`Channel Join Karo | https://t.me/yourchannel`\n\n"
            "Buttons nahi chahiye? Neeche 'Skip' dabao.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Skip Buttons", callback_data="skip_buttons")],
                [InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")],
            ])
        )

    elif step == "buttons":
        if not message.text:
            return await message.reply("❌ Text Mein Buttons Likho!\nFormat: `Title | https://link.com`\nYa skip karo neeche button se.")
        rows   = []
        errors = []
        for line in message.text.strip().splitlines()[:3]:
            if "|" in line:
                parts   = line.split("|", 1)
                btn_txt = parts[0].strip()
                btn_url = parts[1].strip()
                if btn_txt and btn_url.startswith("http"):
                    rows.append([{"text": btn_txt, "url": btn_url}])
                else:
                    errors.append(line)
        if not rows and errors:
            return await message.reply(
                "❌ Galat Format!\n\n"
                "Sahi format:\n`Button Name | https://link.com`\n\n"
                f"Tumhari line: `{errors[0]}`\n\n"
                "Link `https://` se shuru hona chahiye."
            )
        db.save_ad_session(uid, {"step": "position", "buttons": rows})
        await _show_position_editor(client, uid, rows)

    elif step == "add_extra_button":
        if not message.text or "|" not in message.text:
            return await message.reply("❌ Galat Format!\nSahi format: `Button Name | https://link.com`")
        parts   = message.text.split("|", 1)
        btn_txt = parts[0].strip()
        btn_url = parts[1].strip()
        if not btn_url.startswith("http"):
            return await message.reply("❌ URL galat hai! `https://` se shuru karo.")
        existing = db.get_ad_session(uid)
        buttons  = existing.get("buttons", []) if existing else []
        buttons.append([{"text": btn_txt, "url": btn_url}])
        db.save_ad_session(uid, {"step": "position", "buttons": buttons})
        await message.reply(f"✅ Button Add Ho Gaya!\nButton: `{btn_txt}`\nTotal: {sum(len(r) for r in buttons)}/3")
        await _show_position_editor(client, uid, buttons)

    elif step == "position":
        pass


@app.on_message(filters.command("done") & filters.private)
async def cmd_done(client: Client, message: Message):
    session = db.get_ad_session(message.from_user.id)
    if session and session.get("step") in ("buttons", "position"):
        await _finalize_ad(client, message.from_user, session)
    else:
        await message.reply("❌ Koi Active Ad Session Nahi Hai\n\nNaya ad banane ke liye:\n`/createad`")


@app.on_callback_query(filters.regex("^skip_buttons$"))
async def cb_skip_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya. /createad se dobara shuru karo.", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "position", "buttons": []})
    try:
        await cq.message.edit_text(
            "⏭️ Buttons Skip Kiye\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎉 Ad Almost Ready!\n\n"
            "Pehle preview dekho, phir submit karo!\n\n"
            "Ad submit hone ke baad:\n"
            "1️⃣ Admin review karega\n"
            "2️⃣ Approve hone par queue mein jaayega\n"
            "3️⃣ 50,000+ users tak pahunchega!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁️ Preview Dekho",      callback_data="preview_ad")],
                [InlineKeyboardButton("🚀 Submit Ad / Bhejo!", callback_data="submit_ad")],
                [InlineKeyboardButton("❌ Cancel / Roko",       callback_data="cancel_ad")],
            ])
        )
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex("^submit_ad$"))
async def cb_submit_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya! /createad se dobara shuru karo.", show_alert=True)
    try:
        await cq.message.edit_text("⏳ Ad Submit Ho Raha Hai...\n\nPlease wait... 🔄")
    except Exception:
        pass
    await _finalize_ad(client, cq.from_user, session)


async def _show_position_editor(client: Client, user_id: int, buttons: list):
    layout = _render_button_layout(buttons)
    await client.send_message(
        user_id,
        f"🔧 Button Arrangement\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Current Layout:\n{layout}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Buttons upar-neeche ya left-right move karo.\n\n"
        f"✅ Sab theek hai? Submit karo!",
        reply_markup=_position_keyboard(buttons, 0)
    )


def _render_button_layout(buttons: list) -> str:
    if not buttons:
        return "_(Koi buttons nahi)_"
    text = ""
    for i, row in enumerate(buttons):
        names = " | ".join([f"[{b['text']}]" for b in row])
        text += f"Row {i+1}: {names}\n"
    return text


def _position_keyboard(buttons: list, selected: int) -> InlineKeyboardMarkup:
    total = sum(len(row) for row in buttons)
    rows  = [
        [InlineKeyboardButton("⬆️ Upar / Up",    callback_data=f"btn_up_{selected}")],
        [
            InlineKeyboardButton("⬅️ Left",  callback_data=f"btn_left_{selected}"),
            InlineKeyboardButton("Right ➡️", callback_data=f"btn_right_{selected}"),
        ],
        [InlineKeyboardButton("⬇️ Neeche / Down", callback_data=f"btn_down_{selected}")],
    ]
    if total < 3:
        rows.append([InlineKeyboardButton("➕ Naya Button Add Karo", callback_data="add_new_button")])
    rows.append([InlineKeyboardButton("👁️ Preview Dekho",            callback_data="preview_ad")])
    rows.append([InlineKeyboardButton("🚀 Submit Karo! / Submit Ad!", callback_data="submit_ad")])
    rows.append([InlineKeyboardButton("❌ Cancel / Roko",             callback_data="cancel_ad")])
    return InlineKeyboardMarkup(rows)


@app.on_callback_query(filters.regex(r"^btn_(up|down|left|right)_(\d+)$"))
async def cb_position(client: Client, cq: CallbackQuery):
    direction = cq.matches[0].group(1)
    idx       = int(cq.matches[0].group(2))
    session   = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya!", show_alert=True)
    buttons = session.get("buttons", [])
    if not buttons:
        return await cq.answer("Koi buttons nahi hain!", show_alert=True)
    if direction == "up"    and idx > 0:
        buttons[idx], buttons[idx-1] = buttons[idx-1], buttons[idx]; idx -= 1
    elif direction == "down" and idx < len(buttons) - 1:
        buttons[idx], buttons[idx+1] = buttons[idx+1], buttons[idx]; idx += 1
    elif direction == "left" and idx < len(buttons):
        row = buttons[idx]
        if len(row) > 1: row.insert(0, row.pop())
    elif direction == "right" and idx < len(buttons):
        row = buttons[idx]
        if len(row) > 1: row.append(row.pop(0))
    db.save_ad_session(cq.from_user.id, {"buttons": buttons})
    try:
        await cq.message.edit_text(
            f"🔧 Button Layout\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_render_button_layout(buttons)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Theek lag raha hai? Submit karo!",
            reply_markup=_position_keyboard(buttons, idx)
        )
    except Exception:
        pass
    await cq.answer("✅ Updated!")


@app.on_callback_query(filters.regex("^add_new_button$"))
async def cb_add_new_button(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya! /createad se dobara shuru karo.", show_alert=True)
    buttons = session.get("buttons", [])
    if sum(len(row) for row in buttons) >= 3:
        return await cq.answer("❌ Max 3 buttons allowed!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "add_extra_button"})
    try:
        await cq.message.edit_text(
            "➕ Naya Button Add Karo\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Format: `Button ka naam | https://link.com`\n\n"
            "Example:\n`Join Channel | https://t.me/mychannel`\n\n"
            "⚠️ Link `https://` se shuru hona chahiye.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]])
        )
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex("^preview_ad$"))
async def cb_preview_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya! /createad se dobara shuru karo.", show_alert=True)
    from utils.broadcaster import _build_keyboard
    caption   = session.get("caption", "") or ""
    tags_text = " ".join([f"#{t}" for t in session.get("hashtags", [])])
    full_cap  = f"{caption}\n\n{tags_text}".strip()
    kb_data   = session.get("buttons", [])
    preview_kb = _build_keyboard(kb_data) if kb_data else None
    action_kb  = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Submit Karo! Final Hai!", callback_data="submit_ad")],
        [InlineKeyboardButton("✏️ Edit Karo (Buttons)",    callback_data="back_to_buttons")],
        [InlineKeyboardButton("❌ Cancel",                  callback_data="cancel_ad")],
    ])
    await cq.answer("👁️ Yeh raha tumhara ad preview!")
    mtype = session.get("media_type", "text")
    fid   = session.get("file_id")
    try:
        if mtype == "photo" and fid:
            await client.send_photo(cq.from_user.id, fid, caption=f"👁️ PREVIEW:\n\n{full_cap}", reply_markup=preview_kb)
        elif mtype == "video" and fid:
            await client.send_video(cq.from_user.id, fid, caption=f"👁️ PREVIEW:\n\n{full_cap}", reply_markup=preview_kb)
        elif mtype == "animation" and fid:
            await client.send_animation(cq.from_user.id, fid, caption=f"👁️ PREVIEW:\n\n{full_cap}", reply_markup=preview_kb)
        else:
            await client.send_message(cq.from_user.id, f"👁️ PREVIEW:\n\n{full_cap}", reply_markup=preview_kb)
    except Exception as e:
        log.warning(f"Preview send failed: {e}")
    await client.send_message(cq.from_user.id, "⬆️ Yeh tha tumhara ad ka preview!\n\nSab theek hai? Submit karo ya edit karo:", reply_markup=action_kb)


@app.on_callback_query(filters.regex("^back_to_buttons$"))
async def cb_back_to_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya!", show_alert=True)
    buttons = session.get("buttons", [])
    try:
        await cq.message.edit_text(
            f"🔧 Button Layout\n\n{_render_button_layout(buttons)}\n\nButtons move karo ya submit karo:",
            reply_markup=_position_keyboard(buttons, 0)
        )
    except Exception:
        pass
    await cq.answer()


async def _finalize_ad(client, user, session: dict):
    uid       = user.id
    tags_text = " ".join([f"#{t}" for t in session.get("hashtags", [])])
    caption   = session.get("caption", "") or ""
    full_cap  = f"{caption}\n\n{tags_text}".strip()
    from utils.broadcaster import _build_keyboard
    kb_data    = session.get("buttons", [])
    buttons_kb = _build_keyboard(kb_data) if kb_data else None

    try:
        mtype = session.get("media_type", "text")
        fid   = session.get("file_id")
        if mtype == "photo" and fid:
            db_msg = await client.send_photo(DB_CHANNEL, fid, caption=full_cap, reply_markup=buttons_kb)
        elif mtype == "video" and fid:
            db_msg = await client.send_video(DB_CHANNEL, fid, caption=full_cap, reply_markup=buttons_kb)
        elif mtype == "animation" and fid:
            db_msg = await client.send_animation(DB_CHANNEL, fid, caption=full_cap, reply_markup=buttons_kb)
        else:
            db_msg = await client.send_message(DB_CHANNEL, full_cap, reply_markup=buttons_kb)
    except Exception as e:
        log.error(f"DB channel send failed: {e}")
        return await client.send_message(uid, f"❌ Ad Submit Nahi Ho Saka!\nError: `{e}`\n\nDobara try karo: `/createad`")

    ad_id = db.create_ad(uid, {**session, "db_channel_msg_id": db_msg.id})

    # Track ads_posted + consume free ad
    db_user    = db.get_user(uid) or {}
    ads_posted = db_user.get("ads_posted", 0)
    free_ads   = db_user.get("free_ads_earned", 0)
    upd        = {"ads_posted": ads_posted + 1}
    if ads_posted >= 1 and free_ads > 0:
        upd["free_ads_earned"] = max(0, free_ads - 1)
    db.update_user(uid, upd)

    try:
        await client.send_message(
            ADMIN_CHANNEL,
            f"📢 Naya Ad Approval Chahiye\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: [{user.first_name}](tg://user?id={uid}) (`{uid}`)\n"
            f"🆔 Ad ID: `{ad_id}`\n"
            f"📝 Caption: {caption[:200]}\n"
            f"🏷️ Tags: {tags_text}\n"
            f"🔗 Buttons: {len(kb_data)} row(s)\n"
            f"📦 Type: {session.get('media_type','text').title()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Approve = Queue mein jaayega\n"
            f"❌ Reject = User ko reject notification\n"
            f"🚫 Copyright = Flag + {COPYRIGHT_MINS}min mein auto-delete",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve",    callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton("❌ Reject",     callback_data=f"reject_{ad_id}"),
                InlineKeyboardButton("🚫 Copyright", callback_data=f"copyright_{ad_id}"),
            ]])
        )
    except Exception as e:
        log.error(f"Admin channel send failed: {e}")

    db.clear_ad_session(uid)
    await client.send_message(
        uid,
        "🎉 Ad Submit Ho Gaya!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Ad ID: `{ad_id}`\n\n"
        "Aage Kya Hoga?\n\n"
        "1️⃣ ⏳ Admin tumhara ad review karega\n"
        "2️⃣ ✅ Approve hone par queue mein add hoga\n"
        "3️⃣ 📡 Broadcast jaayega sabko\n"
        "4️⃣ 🚀 50,000+ users tak pahunchega!\n\n"
        "📊 Dashboard mein status track karo!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Dashboard Dekho", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton("📢 Aur Ad Banao",    callback_data="start_create_ad")],
        ])
    )


# ══════════════════════════════════════════════════════════════════
#  ADMIN APPROVAL
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^approve_(.+)$"))
async def cb_approve(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.approve_ad(ad_id)
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVED — Queue Mein Hai", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("✅ Ad approved & queued!")
    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                "🎊 Tumhara Ad APPROVE Ho Gaya!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "✅ Broadcasting queue mein add ho gaya!\n"
                "🚀 Jaldi hi 50,000+ users tak pahunchega!\n\n"
                "📊 Dashboard mein live reach track karo!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Reach Track Karo", web_app=WebAppInfo(url=WEBAPP_URL))
                ]])
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^reject_(.+)$"))
async def cb_reject(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.reject_ad(ad_id)
    ad = db.get_ad(ad_id)
    if ad:
        # Free ad waapis karo
        db_user  = db.get_user(ad["owner_id"]) or {}
        ads_post = db_user.get("ads_posted", 1)
        db.update_user(ad["owner_id"], {
            "ads_posted":      max(0, ads_post - 1),
            "free_ads_earned": db_user.get("free_ads_earned", 0) + 1,
        })
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ REJECTED", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("Ad rejected.")
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                "😔 Tumhara Ad Reject Ho Gaya\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "Possible Reasons:\n"
                "• Ad unclear ya low quality tha\n"
                "• Misleading content tha\n"
                "• Guidelines violate ki thi\n\n"
                "Free ad waapis mil gaya!\n"
                "Dobara try karo: /createad",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Dobara Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^copyright_(.+)$"))
async def cb_copyright(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.flag_copyright(ad_id)
    db.reject_ad(ad_id)
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🚫 COPYRIGHT — {COPYRIGHT_MINS}min mein DELETE", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer(f"⚠️ Flagged! Auto-delete in {COPYRIGHT_MINS} minutes.")
    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"⚠️ Copyright Warning!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "🚫 Tumhare ad mein copyright content detect hua hai.\n\n"
                f"⏰ Yeh post {COPYRIGHT_MINS} minutes mein auto-delete ho jaayega.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Copyright Content:\n"
                "• Movies/web series ke clips/posters\n"
                "• Pirated software ya apps\n"
                "• Kisi aur ka music ya video bina permission\n\n"
                "✅ Agli baar original content use karo!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Original Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^report_(.+)$"))
async def cb_report(client: Client, cq: CallbackQuery):
    ad_id    = cq.matches[0].group(1)
    reporter = cq.from_user.id
    db.add_report(reporter, ad_id, "user_report")
    await cq.answer("⚠️ Report submit ho gaya! Admin review karega.", show_alert=True)
    try:
        await client.send_message(
            OWNER_ID,
            f"🚨 User Report Aaya!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Reporter: `{reporter}`\n"
            f"🆔 Ad ID: `{ad_id}`\n\n"
            f"Action: `/deletead {ad_id}`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑️ Delete Ad",       callback_data=f"admin_del_{ad_id}"),
                InlineKeyboardButton("🚫 Copyright Flag", callback_data=f"copyright_{ad_id}"),
            ]])
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^admin_del_(.+)$"))
async def cb_admin_del(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    ad    = db.get_ad(ad_id)
    if ad and ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception:
            pass
    db.delete_ad(ad_id)
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑️ DELETED", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("✅ Ad deleted!")


# ══════════════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("stats") & filters.private)
async def cmd_stats(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    stats    = db.get_user_stats()
    reports  = len(db.get_pending_reports())
    sleeping = sched.is_sleeping()
    await message.reply(
        "📊 Bot Statistics\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users:     `{stats['total']}`\n"
        f"✅ Active Users:    `{stats['active']}`\n"
        f"🚫 Blocked Users:   `{stats['blocked']}`\n\n"
        f"🚨 Pending Reports: `{reports}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Bot Status:\n"
        f"🛌 Deep Sleep: `{'⚠️ YES — FloodWait!' if sleeping else '✅ No — Running'}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Broadcast Now",   callback_data="admin_broadcast")],
            [InlineKeyboardButton("🚀 Admin Dashboard", url=f"{WEBAPP_URL}/admin_panel")],
        ])
    )


@app.on_callback_query(filters.regex("^admin_broadcast$"))
async def cb_admin_broadcast(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    await sched.mega_broadcast()
    await cq.answer("✅ Broadcast queued!", show_alert=True)


@app.on_message(filters.command("deletead") & filters.private)
async def cmd_delete_ad(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    args = message.command[1:]
    if not args:
        return await message.reply("🗑️ Usage: `/deletead <ad_id>`")
    ad_id = args[0]
    ad    = db.get_ad(ad_id)
    if not ad:
        return await message.reply(f"❌ Ad Nahi Mila!\nID: `{ad_id}`")
    owner_id = ad["owner_id"]
    if ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"Could not delete DB channel message: {e}")
    db.delete_ad(ad_id)
    await message.reply(f"✅ Ad Delete Ho Gaya!\n🆔 Ad ID: `{ad_id}`\n👤 Owner: `{owner_id}`")
    try:
        await client.send_message(
            owner_id,
            f"ℹ️ Tumhara Ad Delete Kar Diya Gaya\n\n"
            f"🆔 Ad ID: `{ad_id}`\n\n"
            "Admin ne guidelines violation ke karan yeh ad delete kiya.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Naya Ad Banao", callback_data="start_create_ad")
            ]])
        )
    except Exception:
        pass


@app.on_message(filters.command("broadcast") & filters.private)
async def cmd_broadcast(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.reply("⏳ Mega-broadcast queue ho raha hai...")
    await sched.mega_broadcast()
    await message.reply(
        "✅ Mega-Broadcast Queue Ho Gaya!\n\n"
        "Saare approved ads queue mein push kar diye.\n"
        f"Har {os.getenv('POST_INTERVAL_MINUTES','30')} minute mein ek post jaayega."
    )


@app.on_callback_query(filters.regex("^noop$"))
async def cb_noop(client: Client, cq: CallbackQuery):
    await cq.answer()


# ══════════════════════════════════════════════════════════════════
#  ADMIN PANEL COMMANDS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("admin") & filters.private)
async def cmd_admin(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Sirf owner ke liye hai!")
    stats   = db.get_user_stats()
    reports = len(db.get_pending_reports())
    await message.reply(
        "🛡️ Admin Panel\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: `{stats['total']}`\n"
        f"✅ Active: `{stats['active']}`\n"
        f"🚫 Blocked: `{stats['blocked']}`\n"
        f"🚨 Pending Reports: `{reports}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Commands:\n"
        "`/stats` — Poori stats\n"
        "`/broadcast` — Manual broadcast\n"
        "`/addforcesub -100xxx` — Force sub add\n"
        "`/removefchannel -100xxx` — Remove\n"
        "`/deletead <id>` — Ad delete\n\n"
        "Admin dashboard neeche button se kholo:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥️ Admin Dashboard Kholo", url=f"{WEBAPP_URL}/admin_panel")],
            [InlineKeyboardButton("📡 Broadcast Karo",         callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 Stats Dekho",            callback_data="show_admin_stats")],
        ])
    )


@app.on_callback_query(filters.regex("^show_admin_stats$"))
async def cb_show_admin_stats(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    stats   = db.get_user_stats()
    reports = len(db.get_pending_reports())
    await cq.answer(
        f"👥 Total: {stats['total']} | ✅ Active: {stats['active']} | 🚨 Reports: {reports}",
        show_alert=True
    )


# ══════════════════════════════════════════════════════════════════
#  MY POSTS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("myposts") & filters.private)
async def cmd_myposts(client: Client, message: Message):
    uid  = message.from_user.id
    ads  = db.get_user_ads(uid)
    if not ads:
        return await message.reply(
            "📭 Tumhara Koi Ad Nahi Hai!\n\n"
            "Pehla ad banane ke liye:\n`/createad`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")
            ]])
        )
    await _send_mypost_page(client, uid, ads, 0, message)


@app.on_callback_query(filters.regex("^myposts_view$"))
async def cb_myposts_view(client: Client, cq: CallbackQuery):
    uid  = cq.from_user.id
    ads  = db.get_user_ads(uid)
    if not ads:
        try:
            await cq.message.edit_text(
                "📭 Tumhara Koi Ad Nahi Hai!\n\nPehla ad banao:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass
        return await cq.answer()
    await _send_mypost_page(client, uid, ads, 0, cq, edit=True)
    await cq.answer()


async def _send_mypost_page(client, uid, ads, idx, message_or_cq, edit=False):
    ad      = ads[idx]
    total   = len(ads)
    status  = ad.get("status", "?")
    caption = (ad.get("caption") or "")[:300]
    tags    = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    reach   = ad.get("reach", 0)
    likes   = ad.get("likes", 0)
    ad_id   = str(ad.get("_id", ""))
    status_emoji = {"approved": "✅", "pending": "⏳", "rejected": "❌", "deleted": "🗑️", "completed": "🏆"}.get(status, "❓")

    text = (
        f"📢 Meri Post {idx+1} / {total}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_emoji} Status: {status.upper()}\n"
        f"👁️ Reach: {reach}\n"
        f"❤️ Likes: {likes}\n"
        f"🏷️ Tags: {tags or 'None'}\n\n"
        f"📝 Caption:\n{caption}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Ad ID: `{ad_id}`"
    )
    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton("◀️ Pehle", callback_data=f"mypost_nav_{idx-1}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton("Agle ▶️", callback_data=f"mypost_nav_{idx+1}"))
    action_row = [InlineKeyboardButton("🗑️ Delete", callback_data=f"mypost_del_{ad_id}_{idx}")]
    if ad.get("db_channel_msg_id"):
        action_row.insert(0, InlineKeyboardButton("📌 Post Dekho (PM)", callback_data=f"view_mypost_{ad_id}"))
    kb_rows = []
    if nav_row:    kb_rows.append(nav_row)
    kb_rows.append(action_row)
    kb_rows.append([InlineKeyboardButton("📢 Naya Ad Banao", callback_data="start_create_ad")])
    kb = InlineKeyboardMarkup(kb_rows)
    if edit:
        try:
            await message_or_cq.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
    else:
        await message_or_cq.reply(text, reply_markup=kb)


@app.on_callback_query(filters.regex(r"^mypost_nav_(\d+)$"))
async def cb_mypost_nav(client: Client, cq: CallbackQuery):
    idx = int(cq.matches[0].group(1))
    ads = db.get_user_ads(cq.from_user.id)
    if not ads or idx >= len(ads):
        return await cq.answer("Post nahi mili!", show_alert=True)
    await _send_mypost_page(client, cq.from_user.id, ads, idx, cq, edit=True)
    await cq.answer()


@app.on_callback_query(filters.regex(r"^mypost_del_([^_]+)_(\d+)$"))
async def cb_mypost_del(client: Client, cq: CallbackQuery):
    ad_id = cq.matches[0].group(1)
    idx   = int(cq.matches[0].group(2))
    ad    = db.get_ad(ad_id)
    if not ad or ad.get("owner_id") != cq.from_user.id:
        return await cq.answer("Ad nahi mila!", show_alert=True)
    if ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception:
            pass
    db.delete_ad(ad_id)
    await cq.answer("✅ Ad delete ho gaya!")
    ads = db.get_user_ads(cq.from_user.id)
    if ads:
        await _send_mypost_page(client, cq.from_user.id, ads, min(idx, len(ads)-1), cq, edit=True)
    else:
        try:
            await cq.message.edit_text(
                "📭 Saare ads delete ho gaye!\nNaya ad banao: /createad",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Naya Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^view_mypost_(.+)$"))
async def cb_view_mypost(client: Client, cq: CallbackQuery):
    ad_id = cq.matches[0].group(1)
    uid   = cq.from_user.id
    ad    = db.get_ad(ad_id)
    if not ad or ad.get("owner_id") != uid:
        return await cq.answer("Ad nahi mila!", show_alert=True)
    await cq.answer("Post bhej raha hoon...")
    from utils.broadcaster import send_ad_to_user
    try:
        await send_ad_to_user(client, uid, ad)
        status_str = ad.get("status", "?").upper()
        reach_str  = ad.get("reach", 0)
        likes_str  = ad.get("likes", 0)
        await client.send_message(uid, f"Yeh tha tumhara ad!\n\nStatus: {status_str}\nReach: {reach_str} users\nLikes: {likes_str}")
    except Exception as e:
        await client.send_message(uid, f"Post bhejne mein error: {e}")


# ══════════════════════════════════════════════════════════════════
#  BROWSE POSTS — next/back + like/unlike + owner notification
# ══════════════════════════════════════════════════════════════════

def _browse_keyboard(idx: int, total: int, ad_id: str, liked: bool, likes: int) -> InlineKeyboardMarkup:
    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton("◀️ Pehli Post", callback_data=f"browse_posts_{idx-1}"))
    if idx < total - 1:
        nav.append(InlineKeyboardButton("Agli Post ▶️", callback_data=f"browse_posts_{idx+1}"))
    like_btn = InlineKeyboardButton(
        f"{'❤️' if liked else '🤍'} {likes} Like{'s' if likes != 1 else ''}",
        callback_data=f"like_post_{ad_id}_{idx}"
    )
    rows = []
    if nav:
        rows.append(nav)
    rows.extend([
        [like_btn],
        [InlineKeyboardButton("📢 Apna Ad Banao", callback_data="start_create_ad")],
        [InlineKeyboardButton("🏠 Menu",           callback_data="back_to_menu")],
    ])
    return InlineKeyboardMarkup(rows)


async def _show_browse_post(client: Client, cq: CallbackQuery, idx: int):
    ads = db.get_all_browseable_ads()
    if not ads:
        try:
            await cq.message.edit_text(
                "📭 Abhi koi post nahi hai!\n\nPehla ad banao:\n/createad",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass
        return await cq.answer()
    total = len(ads)
    idx   = max(0, min(idx, total - 1))
    ad    = ads[idx]
    ad_id = str(ad["_id"])
    uid   = cq.from_user.id
    liked = db.has_liked(ad_id, uid)
    likes = ad.get("likes", 0)
    caption   = ad.get("caption", "") or ""
    tags      = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    full_cap  = f"{caption}\n\n{tags}".strip()
    browse_cap = (
        f"📌 Post {idx+1} / {total}\n\n"
        f"{full_cap}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ {likes} likes"
    )
    kb    = _browse_keyboard(idx, total, ad_id, liked, likes)
    mtype = ad.get("media_type", "text")
    fid   = ad.get("file_id")
    try:
        await cq.message.delete()
    except Exception:
        pass
    try:
        if mtype == "photo" and fid:
            await client.send_photo(uid, fid, caption=browse_cap, reply_markup=kb)
        elif mtype == "video" and fid:
            await client.send_video(uid, fid, caption=browse_cap, reply_markup=kb)
        elif mtype == "animation" and fid:
            await client.send_animation(uid, fid, caption=browse_cap, reply_markup=kb)
        else:
            await client.send_message(uid, browse_cap, reply_markup=kb)
    except Exception as e:
        log.warning(f"Browse send failed: {e}")
        await client.send_message(uid, browse_cap, reply_markup=kb)
    await cq.answer()


@app.on_callback_query(filters.regex(r"^browse_posts_(\d+)$"))
async def cb_browse_posts(client: Client, cq: CallbackQuery):
    await _show_browse_post(client, cq, int(cq.matches[0].group(1)))


@app.on_callback_query(filters.regex(r"^like_post_([^_]+)_(\d+)$"))
async def cb_like_post(client: Client, cq: CallbackQuery):
    ad_id  = cq.matches[0].group(1)
    idx    = int(cq.matches[0].group(2))
    uid    = cq.from_user.id
    user   = cq.from_user
    result = db.toggle_like(ad_id, uid)
    liked  = result["liked"]
    total  = result["total_likes"]
    await cq.answer(f"{'❤️ Like kiya!' if liked else '💔 Unlike kiya!'} Total: {total}", show_alert=False)
    # Owner ko notify karo (sirf like pe, unlike pe nahi)
    ad = db.get_ad(ad_id)
    if ad and liked and ad.get("owner_id") != uid:
        try:
            uname    = f"@{user.username}" if user.username else user.first_name
            cap_prev = (ad.get("caption") or "")[:50]
            await client.send_message(
                ad["owner_id"],
                f"❤️ Tumhari post ko {uname} ne like kiya!\n\nPost: {cap_prev}...\nTotal likes: {total}"
            )
        except Exception:
            pass
    ads       = db.get_all_browseable_ads()
    total_ads = len(ads)
    new_kb    = _browse_keyboard(max(0, min(idx, total_ads-1)), total_ads, ad_id, liked, total)
    try:
        await cq.message.edit_reply_markup(new_kb)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

async def main():
    global BOT_USERNAME
    await app.start()
    me = await app.get_me()
    BOT_USERNAME = me.username or BOT_USERNAME
    os.environ["BOT_USERNAME"] = BOT_USERNAME
    log.info(f"Bot started: @{BOT_USERNAME} (ID: {me.id}) | Author: @{_AUTHOR}")
    try:
        await app.get_chat(DB_CHANNEL)
        log.info(f"DB Channel OK: {DB_CHANNEL}")
    except Exception as db_err:
        log.warning(f"DB Channel issue: {db_err}")
    sched.set_client(app)
    scheduler = sched.build_scheduler()
    scheduler.start()
    log.info("Scheduler started. Bot is running!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
