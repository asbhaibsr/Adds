# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters, enums
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

def _check_integrity():
    import hashlib
    marker = f"AdManager Bot — by @{_AUTHOR}"
    h = hashlib.md5(marker.encode()).hexdigest()
    if h != "d7fa3e0a1f88234adf75e97f36e0e5c2":
        pass
    return _AUTHOR

_INTEGRITY = _check_integrity()

# ── Client — in_memory=True (storage baad mein override hoga) ───────
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
COPYRIGHT_MINS = int(os.getenv("COPYRIGHT_DELETE_MINUTES", 120))  # default 2 hours
LOG_CHANNEL    = int(os.getenv("LOG_CHANNEL_ID", os.getenv("ADMIN_CHANNEL_ID", "-1002717243409")))


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


# ══════════════════════════════════════════════════════════════════
#  MAIN MENU
#  - Ad Banao sabse upar (single row)
#  - Baaki 2-2 per line
#  - Browse sabse niche
# ══════════════════════════════════════════════════════════════════

def kb_main_menu() -> InlineKeyboardMarkup:
    # Dashboard button: WEBAPP_URL ho to web_app, warna url button
    if WEBAPP_URL:
        dashboard_btn = InlineKeyboardButton("🚀 Dashboard", web_app=WebAppInfo(url=WEBAPP_URL))
    else:
        dashboard_btn = InlineKeyboardButton("🚀 Dashboard", callback_data="noop")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")],
        [
            InlineKeyboardButton("📋 Meri Posts",  callback_data="myposts_view"),
            InlineKeyboardButton("👥 Referral",     callback_data="show_referral"),
        ],
        [
            InlineKeyboardButton("❓ Help",          callback_data="show_help"),
            InlineKeyboardButton("💬 Feedback",      callback_data="send_feedback"),
        ],
        [dashboard_btn],
        [InlineKeyboardButton("📖 Posts Browse Karo", callback_data="browse_posts_0")],
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
                "⛔ <b>Pehle Yeh Channel Join Karo!</b>\n\n"
                "Is bot ko use karne ke liye neeche diye gaye channel join karna zaroori hai.\n\n"
                "1. Channel join karo\n"
                "2. <b>Verify Karo</b> button dabao",
                reply_markup=kb,
                parse_mode=enums.ParseMode.HTML
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

    if not existing:
        try:
            total_users = db.get_user_stats()["total"]
            await client.send_message(
                LOG_CHANNEL,
                f"👤 <b>Naya User Juda!</b>\n\n"
                f"Naam: {user.first_name or 'N/A'}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"User ID: <code>{user.id}</code>\n"
                f"Total Users: <b>{total_users}</b>",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            log.warning(f"Log channel send failed: {e}")

    if not existing and referred_by and referred_by != user.id:
        unlocked = db.add_referral(referred_by, user.id)
        if unlocked:
            try:
                await client.send_message(
                    referred_by,
                    "🎉 <b>10 Referrals Complete!</b>\n\n"
                    "1 Free Ad Slot Unlock Ho Gaya!\n\n"
                    "Ab apna ad banao aur 50,000+ users tak pahuncho!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 Abhi Ad Banao!", callback_data="start_create_ad")],
                    ]),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass

    # Deeplink: view post
    if args.startswith("view_"):
        ad_id = args[5:]
        if not await force_sub_gate(client, user.id):
            return
        ad = db.get_ad(ad_id)
        if ad:
            try:
                await send_ad_to_user_with_controls(client, user.id, ad)
            except Exception as e:
                await message.reply(f"Post load nahi ho saka: {e}")
        else:
            await message.reply("Post nahi mili ya expire ho gayi.")
        return

    if not await force_sub_gate(client, user.id):
        return

    db_user       = db.get_user(user.id) or {}
    streak        = db_user.get("streak", 0)
    weekly_streak = db_user.get("weekly_streak", 0)
    refs          = db_user.get("referral_count", 0)
    free_ads      = db_user.get("free_ads_earned", 0)
    strikes       = db_user.get("strikes", 0)
    is_new        = not existing

    await message.reply(
        f"{'👋' if is_new else '🙌'} <b>{'Swaagat Hai!' if is_new else 'Wapas Aao!'} {user.first_name}</b>\n\n"
        "🚀 <b>50,000+ Users Tak FREE Promotion!</b>\n\n"
        f"🔥 Streak: <b>{streak} din</b>  |  📅 Weekly: <b>{weekly_streak}</b>\n"
        f"👥 Referrals: <b>{refs}</b>  |  🎟 Free Ads: <b>{free_ads}</b>  |  ⚠️ Strikes: <b>{strikes}</b>\n\n"
        "Neeche se option choose karo:",
        reply_markup=kb_main_menu(),
        parse_mode=enums.ParseMode.HTML
    )


@app.on_callback_query(filters.regex("^check_sub$"))
async def cb_check_sub(client: Client, cq: CallbackQuery):
    passed, missing = await check_subscription(client, cq.from_user.id)
    if passed:
        await cq.message.delete()
        await client.send_message(
            cq.from_user.id,
            "✅ <b>Verify Ho Gaya!</b>\n\nAb bot ka poora maza lo!",
            reply_markup=kb_main_menu(),
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await cq.answer(
            f"Abhi bhi {len(missing)} channel baaki hai! Join karo phir verify karo.",
            show_alert=True
        )


# ══════════════════════════════════════════════════════════════════
#  FEEDBACK
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("^send_feedback$"))
async def cb_send_feedback(client: Client, cq: CallbackQuery):
    db.save_ad_session(cq.from_user.id, {"step": "awaiting_feedback"})
    try:
        await cq.message.edit_text(
            "💬 <b>Feedback / Help</b>\n\n"
            "Apna message ya problem likho — owner tak pahunch jaayega.\n\n"
            "Cancel: /start",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")
            ]]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer()


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
        "👥 <b>Referral Program</b>\n\n"
        f"Total Referrals: <b>{ref_count}</b>\n"
        f"Free Ads Earned: <b>{free_ads}</b>\n"
        f"Next Free Ad: <b>{next_in} aur refers chahiye</b>\n\n"
        f"Tera Link:\n<code>{ref_link}</code>\n\n"
        "10 refers = 1 Free Ad!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Karo",
                url=f"https://t.me/share/url?url={ref_link}&text=FREE+promotion+bot!")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^show_help$"))
async def cb_show_help(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(
        "❓ <b>Help and Guide</b>\n\n"
        "<b>Commands:</b>\n"
        "/createad — Naya ad banao\n"
        "/myposts — Apni posts dekho\n"
        "/search keyword — Posts search karo\n\n"
        "<b>Is Bot Se Kya Kar Sakte Ho?</b>\n\n"
        "Instagram reel, YouTube video, Telegram channel, business — koi bhi "
        "promote karo. Tumhara ad dusre users ke paas jaayega. "
        "Like milne par notification aata hai. "
        "Is tarah views, followers, subscribers badhenge!\n\n"
        "<b>Free Ad Kaise Milega?</b>\n"
        "7 din streak — 1 Free Ad\n"
        "10 refers — 1 Free Ad\n"
        "10 weekly streaks (7-day streaks) — 2 Extra Free Ads\n"
        "Redeem Code — 1 Free Ad",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^back_to_menu$"))
async def cb_back_menu(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if session:
        db.clear_ad_session(cq.from_user.id)
    try:
        await cq.message.edit_text(
            "🏠 <b>Main Menu</b>\n\nNeeche se choose karo:",
            reply_markup=kb_main_menu(),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex("^cancel_ad$"))
async def cb_cancel_ad(client: Client, cq: CallbackQuery):
    db.clear_ad_session(cq.from_user.id)
    try:
        await cq.message.edit_text(
            "❌ <b>Ad Cancel Ho Gaya</b>\n\nJab chahein dobara banao!",
            reply_markup=kb_main_menu(),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer("Cancelled!")


# ══════════════════════════════════════════════════════════════════
#  FORCE SUB ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addforcesub") & filters.private)
async def cmd_add_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("Sirf bot owner use kar sakta hai.")
    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        ch_list  = "\n".join([f"  {c['channel_id']} — {c.get('title','?')}" for c in channels]) or "  Koi nahi"
        return await message.reply(
            f"<b>Active Force-Sub Channels:</b>\n{ch_list}\n\n"
            "Add: /addforcesub -100xxxxxxxxxx",
            parse_mode=enums.ParseMode.HTML
        )
    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply("Galat ID! Format: -100xxxxxxxxxx")
    await message.reply("Channel check ho raha hai...")
    try:
        chat  = await client.get_chat(ch_id)
        title = chat.title or str(ch_id)
        try:
            link_obj    = await client.create_chat_invite_link(ch_id, creates_join_request=True, name="ForceSub")
            invite_link = link_obj.invite_link
        except Exception:
            invite_link = getattr(chat, "invite_link", "") or ""
    except Exception as e:
        return await message.reply(f"Channel info nahi mili!\nError: {e}\n\nBot channel ka admin hai?")
    added = db.add_forcesub_channel(ch_id, invite_link, title)
    if added:
        await message.reply(
            f"✅ <b>Force-Sub Add Ho Gaya!</b>\n\nChannel: {title}\nID: <code>{ch_id}</code>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Remove Karo", callback_data=f"remove_fsub_{ch_id}")
            ]]),
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply("Yeh channel pehle se add hai!")


@app.on_callback_query(filters.regex(r"^remove_fsub_(-\d+)$"))
async def cb_remove_fsub_quick(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    ch_id   = int(cq.matches[0].group(1))
    removed = db.remove_forcesub_channel(ch_id)
    if removed:
        try:
            await cq.message.edit_text(f"✅ Channel <code>{ch_id}</code> hata diya!", parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        await cq.answer("Removed!")
    else:
        await cq.answer("Already removed!", show_alert=True)


@app.on_message(filters.command("removefchannel") & filters.private)
async def cmd_remove_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("Sirf owner use kar sakta hai!")
    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        if not channels:
            return await message.reply("Koi force-sub channel set nahi hai.")
        lines = "\n".join([f"  {c['channel_id']} — {c.get('title','?')}" for c in channels])
        return await message.reply(
            f"<b>Active Channels:</b>\n{lines}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"❌ {c.get('title','?')}", callback_data=f"remove_fsub_{c['channel_id']}")]
                for c in channels
            ]),
            parse_mode=enums.ParseMode.HTML
        )
    try:
        ch_id   = int(args[0])
        removed = db.remove_forcesub_channel(ch_id)
        await message.reply("✅ Remove ho gaya!" if removed else "Channel nahi mila!")
    except ValueError:
        await message.reply("Galat ID!")


# ══════════════════════════════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("search") & filters.private)
async def cmd_search(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply(
            "🔍 <b>Search</b>\n\nUsage: /search keyword\nExample: /search bollywood",
            parse_mode=enums.ParseMode.HTML
        )
    query   = " ".join(args)
    results = db.search_ads(query, limit=5)
    if not results:
        return await message.reply(f"Koi result nahi mila: <b>{query}</b>", parse_mode=enums.ParseMode.HTML)
    buttons = []
    for i, ad in enumerate(results, 1):
        preview = (ad.get("caption", "") or "")[:40].strip()
        ad_id   = str(ad.get("_id", ""))
        buttons.append([InlineKeyboardButton(f"📌 {preview or f'Post {i}'}", callback_data=f"view_search_post_{ad_id}")])
    await message.reply(
        f"🔍 <b>{len(results)} result mile:</b> {query}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


@app.on_callback_query(filters.regex(r"^view_search_post_(.+)$"))
async def cb_view_search_post(client: Client, cq: CallbackQuery):
    ad_id = cq.matches[0].group(1)
    ad    = db.get_ad(ad_id)
    if not ad:
        return await cq.answer("Post nahi mili!", show_alert=True)
    await cq.answer("Post bhej raha hoon...")
    try:
        await send_ad_to_user_with_controls(client, cq.from_user.id, ad)
    except Exception as e:
        await client.send_message(cq.from_user.id, f"Error: {e}")


@app.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    q = query.query.strip()
    if not q:
        await query.answer([], switch_pm_text="Kuch type karo", switch_pm_parameter="help", cache_time=5)
        return
    results_db     = db.search_ads(q, limit=5)
    inline_results = []
    for ad in results_db:
        caption   = (ad.get("caption", "") or "")[:200]
        tags      = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        ad_id     = str(ad.get("_id", ""))
        deep_link = f"https://t.me/{BOT_USERNAME}?start=view_{ad_id}"
        inline_results.append(InlineQueryResultArticle(
            title       = caption[:60] or q,
            description = tags or "Post dekho",
            input_message_content=InputTextMessageContent(
                f"📌 {caption[:150]}\n\n{tags}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Post Dekho", url=deep_link)
            ]])
        ))
    if not inline_results:
        await query.answer([], switch_pm_text=f"'{q}' ka koi result nahi", switch_pm_parameter="search", cache_time=5)
        return
    await query.answer(inline_results, cache_time=30)


# ══════════════════════════════════════════════════════════════════
#  AD CREATION FLOW — COMPLETE REWRITE
#
#  Step 1: Media    (Skip bhi kar sakte ho — text-only ad)
#  Step 2: Caption  (Required — text likhna zaroori)
#  Step 3: Hashtags (Skip kar sakte ho)
#  Step 4: Buttons  (Add/Delete kar sakte ho, skip bhi)
#  Preview: Actual post dikhata hai
#  Edit:    Caption/Tags/Media/Buttons sab edit ho sakte hain
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("createad") & filters.private)
@app.on_callback_query(filters.regex("^start_create_ad$"))
async def cmd_create_ad(client, update):
    is_cb = isinstance(update, CallbackQuery)
    user  = update.from_user
    uid   = user.id

    if not await force_sub_gate(client, uid):
        if is_cb:
            await update.answer()
        return

    db_user    = db.get_user(uid) or {}
    user_ads   = db.get_user_ads(uid)
    free_ads   = db_user.get("free_ads_earned", 0)

    # ── Sirf GENUINELY ACTIVE ads count honge ──────────────────────
    # Rejected, copyright-flagged, 18+-flagged, completed, deleted = allowed to create new
    active_ads = [
        a for a in user_ads
        if a.get("status") in ("pending", "approved")
        and not a.get("is_copyright", False)   # copyright laga = active count se bahar
        and not a.get("is_18plus", False)       # 18+ laga = active count se bahar
    ]

    # ── CASE 1: Active ad hai + free slot bhi nahi ─────────────────
    if active_ads and free_ads <= 0:
        active = active_ads[0]
        status = active.get("status", "?").upper()
        msg = (
            f"⚠️ <b>Tumhara ek ad pehle se active hai!</b>\n\n"
            f"Status: {status}\n\n"
            "Naya ad banane ke liye earn karo:\n"
            "🔁 7 din streak puri karo — 1 Free Ad\n"
            "👥 10 dosto ko refer karo — 1 Free Ad\n"
            "🎟 Redeem code use karo — 1 Free Ad"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Meri Posts", callback_data="myposts_view")],
            [InlineKeyboardButton("🔙 Back",        callback_data="back_to_menu")],
        ])
        if is_cb:
            try:
                await update.message.edit_text(msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
            except Exception:
                await client.send_message(uid, msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
            await update.answer()
        else:
            await update.reply(msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
        return

    # ── CASE 2: Free ad nahi bacha ─────────────────────────────────
    if free_ads <= 0:
        msg = (
            "❌ <b>Free ad nahi bacha!</b>\n\n"
            "Free ad kaise pao:\n"
            "🔁 7 din streak — 1 Free Ad\n"
            "👥 10 refers — 1 Free Ad\n"
            "🏆 10 weekly streaks — 2 Free Ads\n"
            "🎟 Redeem code use karo — 1 Free Ad"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Refer Karo", callback_data="show_referral")],
            [InlineKeyboardButton("🔙 Back",        callback_data="back_to_menu")],
        ])
        if is_cb:
            try:
                await update.message.edit_text(msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
            except Exception:
                await client.send_message(uid, msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
            await update.answer()
        else:
            await update.reply(msg, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
        return

    db.save_ad_session(uid, {"step": "media"})
    text = (
        "📢 <b>Ad Banana Shuru Karo!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Step 1 — Media Bhejo</b>\n\n"
        "📷 Photo bhejo — Image ad banega\n"
        "🎬 Video bhejo — Video ad banega\n\n"
        "Sirf text ad banana chahte ho?\n"
        "Neeche <b>Skip</b> dabao."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip — Sirf Text Ad Chahiye", callback_data="skip_media")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
    ])
    if is_cb:
        try:
            await update.message.edit_text(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
        except Exception:
            await client.send_message(uid, text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
        await update.answer()
    else:
        await update.reply(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)


# Skip media — text only ad
@app.on_callback_query(filters.regex("^skip_media$"))
async def cb_skip_media(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "caption", "media_type": "text", "file_id": None})
    try:
        await cq.message.edit_text(
            "📝 <b>Step 2 — Caption Likho</b>\n\n"
            "Apne ad ka text type karo:\n\n"
            "Kya promote karna chahte ho?\n"
            "Link, contact, details — sab likh sakte ho.\n"
            "Max 1024 characters.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer()


# Skip hashtags
@app.on_callback_query(filters.regex("^skip_hashtags$"))
async def cb_skip_hashtags(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "buttons", "hashtags": []})
    buttons = session.get("buttons", [])
    try:
        await cq.message.delete()
    except Exception:
        pass
    await _show_button_step(client, cq.from_user.id, buttons)
    await cq.answer()


# Main message handler
@app.on_message(
    filters.private
    & (filters.photo | filters.video | filters.animation | filters.text)
    & ~filters.command(["start","search","addforcesub","removefchannel",
                        "createad","stats","broadcast","deletead","done",
                        "myposts","preview","admin","send_broadcast","cancel_broadcast",
                        "gencode"])
    & ~filters.regex(r"^#redeem\s+\S+")
)
async def handle_ad_creation(client: Client, message: Message):
    uid     = message.from_user.id
    session = db.get_ad_session(uid)
    if not session:
        return
    step = session.get("step", "")

    # Owner broadcast mode
    if step == "awaiting_broadcast":
        if not is_owner(uid):
            return
        db.clear_ad_session(uid)
        await _do_owner_broadcast(client, message, uid)
        return

    # Feedback mode
    if step == "awaiting_feedback":
        if not message.text:
            return await message.reply("Sirf text message bhejo feedback ke liye.")
        db.clear_ad_session(uid)
        try:
            user  = message.from_user
            uname = f"@{user.username}" if user.username else user.first_name
            await client.send_message(
                OWNER_ID,
                f"💬 <b>User Feedback</b>\n\n"
                f"User: {uname} (<code>{uid}</code>)\n\n"
                f"Message:\n{message.text}",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        await message.reply(
            "✅ <b>Message Pahunch Gaya!</b>\n\nOwner jald hi reply karega.",
            reply_markup=kb_main_menu(),
            parse_mode=enums.ParseMode.HTML
        )
        return

    # ── STEP: MEDIA ──
    if step == "media":
        if message.photo:
            media_type, file_id = "photo", message.photo.file_id
        elif message.video:
            media_type, file_id = "video", message.video.file_id
        elif message.animation:
            media_type, file_id = "animation", message.animation.file_id
        else:
            return await message.reply(
                "📷 Photo ya Video bhejo!\n\n"
                "Ya text-only ad ke liye Skip dabao:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Skip — Text Only", callback_data="skip_media")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
                ])
            )
        db.save_ad_session(uid, {"step": "caption", "media_type": media_type, "file_id": file_id})
        await message.reply(
            f"✅ <b>{media_type.title()} Mil Gaya!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Step 2 — Caption Likho</b>\n\n"
            "Apne ad ka text type karo.\n"
            "Kya promote karna chahte ho?\n"
            "Max 1024 characters.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]]),
            parse_mode=enums.ParseMode.HTML
        )

    # ── STEP: CAPTION ──
    elif step == "caption":
        if not message.text:
            return await message.reply("Text mein caption likho!")
        caption = message.text[:1024]
        db.save_ad_session(uid, {"step": "hashtags", "caption": caption})
        await message.reply(
            "✅ <b>Caption Save Ho Gaya!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Step 3 — Hashtags Daalo</b>\n\n"
            "Hashtags se log tumhara ad search kar paate hain!\n"
            "Agar koi #tech search kare aur tumne #tech lagaya ho\n"
            "to tumhara ad usse milega.\n\n"
            "Format: <code>#tag1 #tag2 #tag3</code>\n"
            "Example: <code>#instagram #viral #reels</code>\n\n"
            "Skip karna chahte ho to neeche button dabao.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Skip — Hashtag Nahi Chahiye", callback_data="skip_hashtags")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
            ]),
            parse_mode=enums.ParseMode.HTML
        )

    # ── STEP: HASHTAGS ──
    elif step == "hashtags":
        if not message.text:
            return await message.reply("Hashtags text mein likho ya skip karo.")
        tags = [t.lstrip("#").lower().strip() for t in message.text.split() if t.startswith("#") and len(t) > 1]
        if not tags:
            return await message.reply(
                "Koi valid hashtag nahi mila!\n\n"
                "Format: <code>#movie #tech #deals</code>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Skip", callback_data="skip_hashtags")],
                ]),
                parse_mode=enums.ParseMode.HTML
            )
        tags = tags[:5]
        db.save_ad_session(uid, {"step": "buttons", "hashtags": tags})
        buttons = session.get("buttons", [])
        await _show_button_step(client, uid, buttons)

    # ── STEP: BUTTON INPUT ──
    elif step == "buttons_input":
        if not message.text or "|" not in message.text:
            return await message.reply(
                "❌ Galat format!\n\nSahi: <code>Button Naam | https://link.com</code>",
                parse_mode=enums.ParseMode.HTML
            )
        parts   = message.text.split("|", 1)
        btn_txt = parts[0].strip()
        btn_url = parts[1].strip()
        if not btn_url.startswith("http"):
            return await message.reply("URL https:// se shuru hona chahiye!")
        existing = db.get_ad_session(uid)
        buttons  = existing.get("buttons", []) if existing else []
        total_btns = sum(len(r) for r in buttons)
        if total_btns >= 3:
            return await message.reply("Max 3 buttons add kar sakte ho!")

        new_btn = {"text": btn_txt, "url": btn_url}

        # Agar pehle se koi button hai — puchho: side mein ya neeche?
        if total_btns >= 1:
            # Last row mein sirf 1 button ho to side mein add kar sakte hain (max 2 per row)
            last_row = buttons[-1] if buttons else []
            can_side = len(last_row) < 2

            # Session mein pending button store karo
            db.save_ad_session(uid, {"step": "button_placement", "pending_btn": new_btn})

            placement_kb_rows = []
            if can_side:
                placement_kb_rows.append([
                    InlineKeyboardButton(
                        f"◀▶ Side Mein (Pichle wale ke saath)",
                        callback_data="btn_place_side"
                    )
                ])
            placement_kb_rows.append([
                InlineKeyboardButton(
                    "⬇ Neeche Naye Row Mein",
                    callback_data="btn_place_below"
                )
            ])
            placement_kb_rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")])

            await message.reply(
                f"✅ Button ready: <b>{btn_txt}</b>\n\n"
                "🔲 Yeh button kahan rakhein?",
                reply_markup=InlineKeyboardMarkup(placement_kb_rows),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            # Pehla button — seedha add karo
            buttons.append([new_btn])
            db.save_ad_session(uid, {"step": "buttons", "buttons": buttons})
            await message.reply(f"✅ Button add ho gaya: <b>{btn_txt}</b>", parse_mode=enums.ParseMode.HTML)
            await _show_button_step(client, uid, buttons)

    elif step in ("buttons", "ready", "button_placement"):
        pass


# ── BUTTON PLACEMENT CALLBACKS ──
@app.on_callback_query(filters.regex("^btn_place_side$"))
async def cb_btn_place_side(client: Client, cq: CallbackQuery):
    """Pending button ko last row mein side mein add karo."""
    uid     = cq.from_user.id
    session = db.get_ad_session(uid)
    if not session or not session.get("pending_btn"):
        return await cq.answer("Session expire ho gaya!", show_alert=True)

    buttons    = session.get("buttons", [])
    new_btn    = session["pending_btn"]
    last_row   = buttons[-1] if buttons else []

    if last_row and len(last_row) < 2:
        buttons[-1].append(new_btn)
    else:
        buttons.append([new_btn])

    db.save_ad_session(uid, {"step": "buttons", "buttons": buttons, "pending_btn": None})
    try:
        await cq.message.delete()
    except Exception:
        pass
    await cq.answer("Side mein add ho gaya! ✅")
    await _show_button_step(client, uid, buttons)


@app.on_callback_query(filters.regex("^btn_place_below$"))
async def cb_btn_place_below(client: Client, cq: CallbackQuery):
    """Pending button ko naye row mein neeche add karo."""
    uid     = cq.from_user.id
    session = db.get_ad_session(uid)
    if not session or not session.get("pending_btn"):
        return await cq.answer("Session expire ho gaya!", show_alert=True)

    buttons = session.get("buttons", [])
    new_btn = session["pending_btn"]
    buttons.append([new_btn])

    db.save_ad_session(uid, {"step": "buttons", "buttons": buttons, "pending_btn": None})
    try:
        await cq.message.delete()
    except Exception:
        pass
    await cq.answer("Neeche add ho gaya! ✅")
    await _show_button_step(client, uid, buttons)


async def _show_button_step(client: Client, uid: int, buttons: list):
    """
    Step 4 — Button manager.
    Existing buttons dikhao with delete option.
    Add new button option.
    Preview + Skip.
    """
    total = sum(len(r) for r in buttons)

    btn_list = ""
    if buttons:
        for i, row in enumerate(buttons):
            for b in row:
                btn_list += f"  {i+1}. <b>{b['text']}</b> — {b['url']}\n"
    else:
        btn_list = "  (Koi button nahi abhi)\n"

    text = (
        "🔗 <b>Step 4 — Buttons (Optional)</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Buttons:</b>\n{btn_list}\n"
        "Button add karo ya seedha preview dekho."
    )

    kb_rows = []

    # Delete buttons — ek ek
    if buttons:
        for i, row in enumerate(buttons):
            for b in row:
                kb_rows.append([InlineKeyboardButton(
                    f"🗑 Delete: {b['text'][:20]}",
                    callback_data=f"del_btn_{i}"
                )])

    # Add button row
    add_row = []
    if total < 3:
        add_row.append(InlineKeyboardButton("➕ Button Add Karo", callback_data="add_new_button"))
    add_row.append(InlineKeyboardButton("⏭ Skip", callback_data="skip_buttons"))
    kb_rows.append(add_row)

    kb_rows.append([InlineKeyboardButton("👁 Preview Dekho", callback_data="preview_ad")])
    kb_rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")])

    await client.send_message(uid, text, reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode=enums.ParseMode.HTML)


@app.on_callback_query(filters.regex(r"^del_btn_(\d+)$"))
async def cb_del_btn(client: Client, cq: CallbackQuery):
    idx     = int(cq.matches[0].group(1))
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    buttons = session.get("buttons", [])
    if idx < len(buttons):
        removed_name = buttons[idx][0]["text"] if buttons[idx] else "Button"
        buttons.pop(idx)
        db.save_ad_session(cq.from_user.id, {"buttons": buttons})
        await cq.answer(f"Hata diya: {removed_name}", show_alert=False)
    else:
        return await cq.answer("Button nahi mila!", show_alert=True)
    try:
        await cq.message.delete()
    except Exception:
        pass
    await _show_button_step(client, cq.from_user.id, buttons)


@app.on_callback_query(filters.regex("^add_new_button$"))
async def cb_add_new_button(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    buttons = session.get("buttons", [])
    if sum(len(r) for r in buttons) >= 3:
        return await cq.answer("Max 3 buttons allowed!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "buttons_input"})
    try:
        await cq.message.edit_text(
            "➕ <b>Naya Button Add Karo</b>\n\n"
            "Format: <code>Button Naam | https://link.com</code>\n\n"
            "Example:\n"
            "<code>Channel Join Karo | https://t.me/mychannel</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex("^skip_buttons$"))
async def cb_skip_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "ready"})
    try:
        await cq.message.edit_text(
            "✅ <b>Ad Ready Hai!</b>\n\n"
            "Preview dekho ya seedha submit karo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁 Preview Dekho", callback_data="preview_ad"),
                 InlineKeyboardButton("🚀 Submit Karo",  callback_data="submit_ad")],
                [InlineKeyboardButton("❌ Cancel",        callback_data="cancel_ad")],
            ]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
    await cq.answer()


# ── PREVIEW — actual post dikhao ──
@app.on_callback_query(filters.regex("^preview_ad$"))
async def cb_preview_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire! /createad se shuru karo.", show_alert=True)

    caption   = session.get("caption", "") or ""
    hashtags  = session.get("hashtags", [])
    tags_text = " ".join([f"#{t}" for t in hashtags])
    full_cap  = f"{caption}\n\n{tags_text}".strip() if tags_text else caption
    kb_data   = session.get("buttons", [])
    mtype     = session.get("media_type", "text")
    fid       = session.get("file_id")

    # Preview keyboard (user ke custom buttons)
    preview_kb = None
    if kb_data:
        kb_rows = []
        for row in kb_data:
            kb_rows.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
        preview_kb = InlineKeyboardMarkup(kb_rows)

    # Action keyboard
    action_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Submit Karo", callback_data="submit_ad"),
            InlineKeyboardButton("✏ Edit Karo",    callback_data="edit_ad_menu"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
    ])

    await cq.answer("Yeh raha preview!")

    try:
        if mtype == "photo" and fid:
            await client.send_photo(cq.from_user.id, fid, caption=f"👁 PREVIEW\n\n{full_cap}", reply_markup=preview_kb)
        elif mtype == "video" and fid:
            await client.send_video(cq.from_user.id, fid, caption=f"👁 PREVIEW\n\n{full_cap}", reply_markup=preview_kb)
        elif mtype == "animation" and fid:
            await client.send_animation(cq.from_user.id, fid, caption=f"👁 PREVIEW\n\n{full_cap}", reply_markup=preview_kb)
        else:
            await client.send_message(cq.from_user.id, f"👁 <b>PREVIEW</b>\n\n{full_cap}", reply_markup=preview_kb, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        log.warning(f"Preview send failed: {e}")

    await client.send_message(
        cq.from_user.id,
        "Upar dekho — yahi dikhega sabko!\n\n<b>Kya karna chahte ho?</b>",
        reply_markup=action_kb,
        parse_mode=enums.ParseMode.HTML
    )


# ── EDIT MENU — sab cheez edit kar sako ──
@app.on_callback_query(filters.regex("^edit_ad_menu$"))
async def cb_edit_ad_menu(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    await cq.message.edit_text(
        "✏ <b>Kya Edit Karna Chahte Ho?</b>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📷 Media Change Karo",  callback_data="edit_media"),
             InlineKeyboardButton("📝 Caption Edit Karo",  callback_data="edit_caption")],
            [InlineKeyboardButton("🏷 Tags Edit Karo",     callback_data="edit_hashtags"),
             InlineKeyboardButton("🔗 Buttons Edit Karo",  callback_data="edit_buttons")],
            [InlineKeyboardButton("👁 Back to Preview",    callback_data="preview_ad")],
            [InlineKeyboardButton("❌ Cancel",              callback_data="cancel_ad")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^edit_media$"))
async def cb_edit_media(client: Client, cq: CallbackQuery):
    db.save_ad_session(cq.from_user.id, {"step": "media"})
    await cq.message.edit_text(
        "📷 <b>Naya Media Bhejo</b>\n\nPhoto ya video bhejo:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Text Only", callback_data="skip_media")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^edit_caption$"))
async def cb_edit_caption(client: Client, cq: CallbackQuery):
    db.save_ad_session(cq.from_user.id, {"step": "caption"})
    await cq.message.edit_text(
        "📝 <b>Naya Caption Likho</b>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^edit_hashtags$"))
async def cb_edit_hashtags(client: Client, cq: CallbackQuery):
    db.save_ad_session(cq.from_user.id, {"step": "hashtags"})
    await cq.message.edit_text(
        "🏷 <b>Naye Hashtags Likho</b>\n\nFormat: <code>#tag1 #tag2</code>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Skip", callback_data="skip_hashtags")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^edit_buttons$"))
async def cb_edit_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire!", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "buttons"})
    buttons = session.get("buttons", [])
    try:
        await cq.message.delete()
    except Exception:
        pass
    await _show_button_step(client, cq.from_user.id, buttons)
    await cq.answer()


@app.on_callback_query(filters.regex("^submit_ad$"))
async def cb_submit_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire! /createad se shuru karo.", show_alert=True)
    try:
        await cq.message.edit_text("⏳ Submit ho raha hai...")
    except Exception:
        pass
    await _finalize_ad(client, cq.from_user, session)


@app.on_message(filters.command("done") & filters.private)
async def cmd_done(client: Client, message: Message):
    session = db.get_ad_session(message.from_user.id)
    if session and session.get("step") in ("buttons", "ready"):
        await _finalize_ad(client, message.from_user, session)
    else:
        await message.reply("Koi active ad session nahi. /createad se shuru karo.")


async def _finalize_ad(client, user, session: dict):
    uid       = user.id
    hashtags  = session.get("hashtags", [])
    tags_text = " ".join([f"#{t}" for t in hashtags])
    caption   = session.get("caption", "") or ""
    full_cap  = f"{caption}\n\n{tags_text}".strip() if tags_text else caption
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
        return await client.send_message(uid, f"❌ Submit nahi ho saka!\nError: {e}")

    ad_id = db.create_ad(uid, {**session, "db_channel_msg_id": db_msg.id})

    db_user    = db.get_user(uid) or {}
    ads_posted = db_user.get("ads_posted", 0)
    free_ads   = db_user.get("free_ads_earned", 0)
    upd        = {"ads_posted": ads_posted + 1}
    # BUG FIX: pehle free_ads check karo — agar hai to use karo (ads_posted >= 1 check hata diya)
    if free_ads > 0:
        upd["free_ads_earned"] = max(0, free_ads - 1)
    db.update_user(uid, upd)

    try:
        await client.send_message(
            ADMIN_CHANNEL,
            f"📢 <b>Naya Ad — Approval Chahiye</b>\n\n"
            f"User: {user.first_name} (<code>{uid}</code>)\n"
            f"Ad ID: <code>{ad_id}</code>\n"
            f"Type: {session.get('media_type','text').title()}\n"
            f"Caption: {caption[:150]}\n"
            f"Tags: {tags_text or 'None'}\n"
            f"Buttons: {len(kb_data)}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve",      callback_data=f"approve_{ad_id}"),
                    InlineKeyboardButton("❌ Reject",       callback_data=f"reject_{ad_id}"),
                ],
                [
                    InlineKeyboardButton("🚫 Copyright",   callback_data=f"copyright_{ad_id}"),
                    InlineKeyboardButton("🔞 18+ Approve", callback_data=f"adult_{ad_id}"),
                ],
            ]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        log.error(f"Admin channel send failed: {e}")

    db.clear_ad_session(uid)
    await client.send_message(
        uid,
        f"🎉 <b>Ad Submit Ho Gaya!</b>\n\n"
        f"Ad ID: <code>{ad_id}</code>\n\n"
        "Admin review karega — approve hone par sabko jaayega!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Meri Posts",  callback_data="myposts_view"),
             InlineKeyboardButton("🏠 Menu",         callback_data="back_to_menu")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )


# ══════════════════════════════════════════════════════════════════
#  ADMIN APPROVAL
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^approve_(.+)$"))
async def cb_approve(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.approve_ad(ad_id)
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVED", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("Approved!")
    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"🎊 <b>Ad Approve Ho Gaya!</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                "Jaldi hi sabko broadcast hoga!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Meri Posts", callback_data="myposts_view")
                ]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^reject_(.+)$"))
async def cb_reject(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.reject_ad(ad_id)
    ad = db.get_ad(ad_id)
    if ad:
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
    await cq.answer("Rejected.")
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"😔 <b>Ad Reject Ho Gaya</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                "✅ Tumhara <b>1 Free Ad wapas</b> tumhare account mein aa gaya!\n"
                "Tum abhi dobara naya ad bana sakte ho.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Abhi Dobara Banao", callback_data="start_create_ad")
                ]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^copyright_(.+)$"))
async def cb_copyright(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.flag_copyright(ad_id)
    db.reject_ad(ad_id)

    # ── Free ad wapas karo owner ko ──────────────────────────────
    ad = db.get_ad(ad_id)
    if ad:
        db_user  = db.get_user(ad["owner_id"]) or {}
        ads_post = db_user.get("ads_posted", 1)
        db.update_user(ad["owner_id"], {
            "ads_posted":      max(0, ads_post - 1),
            "free_ads_earned": db_user.get("free_ads_earned", 0) + 1,
        })

    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🚫 COPYRIGHT — {COPYRIGHT_MINS//60}hr AUTO-DELETE", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("Flagged!")
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"⚠️ <b>Copyright Warning!</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                f"Tumhara content copyright violate karta hai.\n"
                f"Yeh {COPYRIGHT_MINS // 60} ghante ({COPYRIGHT_MINS} min) baad sabhi users ke paas se "
                f"auto-delete ho jaayega.\n\n"
                f"⚠️ Ek <b>strike</b> tumhare account par lag gayi hai.\n\n"
                f"✅ Tumhara <b>1 Free Ad wapas</b> aa gaya — naya ad bana sakte ho.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Naya Ad Banao", callback_data="start_create_ad")
                ]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass



# ══════════════════════════════════════════════════════════════════
#  18+ APPROVED HANDLER
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^adult_(.+)$"))
async def cb_adult_approve(client: Client, cq: CallbackQuery):
    """18+ content approve karo — user tak jaayega lekin 30 min baad delete hoga."""
    if not is_owner(cq.from_user.id):
        return await cq.answer("Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.flag_18plus(ad_id)
    db.approve_ad(ad_id)

    # ── 18+ approved mein free ad consume hoti hai (wapas nahi) ──
    # Ad broadcast hogi, phir auto-delete. Free ad wapas NAHI milegi.
    # Lekin user naya ad bana sake — active_ads check mein is_18plus=True skip hoga.

    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
            InlineKeyboardButton("🔞 18+ APPROVED — 30min DELETE", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("18+ Approved!")
    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"🔞 <b>18+ Content Approve Hua!</b>\n\n"
                f"Ad ID: <code>{ad_id}</code>\n\n"
                f"⚠️ Tumhara ad sabko jaayega lekin <b>30 minute baad auto-delete</b> ho jaayega users ke paas se.\n"
                f"Strike bhi lagi hai tumhare account par.\n\n"
                f"<i>Note: 18+ content ke liye free ad wapas nahi milti.</i>",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^report_(.+)$"))
async def cb_report(client: Client, cq: CallbackQuery):
    ad_id    = cq.matches[0].group(1)
    reporter = cq.from_user.id
    db.add_report(reporter, ad_id, "user_report")
    await cq.answer("Report submit ho gaya!", show_alert=True)
    try:
        await client.send_message(
            OWNER_ID,
            f"🚨 <b>User Report</b>\n\nReporter: <code>{reporter}</code>\nAd ID: <code>{ad_id}</code>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑 Delete",        callback_data=f"admin_del_{ad_id}"),
                InlineKeyboardButton("🚫 Copyright",     callback_data=f"copyright_{ad_id}"),
                InlineKeyboardButton("🔞 18+ Approve",  callback_data=f"adult_{ad_id}"),
            ]]),
            parse_mode=enums.ParseMode.HTML
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
            InlineKeyboardButton("🗑 DELETED", callback_data="noop")
        ]]))
    except Exception:
        pass
    await cq.answer("Deleted!")


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
        f"📊 <b>Bot Statistics</b>\n\n"
        f"Total Users: <b>{stats['total']}</b>\n"
        f"Active: <b>{stats['active']}</b>\n"
        f"Blocked/Deleted: <b>{stats['blocked']}</b>\n"
        f"Reports: <b>{reports}</b>\n\n"
        f"Deep Sleep: <b>{'YES' if sleeping else 'No'}</b>\n\n"
        f"<i>Blocked users ka data clear karne ke liye niche button dabao.</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Broadcast",  callback_data="admin_broadcast"),
             InlineKeyboardButton("🚀 Dashboard",  url=f"{WEBAPP_URL}/admin_panel")],
            [InlineKeyboardButton("🗑 Blocked Users Clear Karo", callback_data="clear_blocked_users")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )


@app.on_callback_query(filters.regex("^admin_broadcast$"))
async def cb_admin_broadcast(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    await sched.mega_broadcast()
    await cq.answer("Broadcast queued!", show_alert=True)


@app.on_callback_query(filters.regex("^clear_blocked_users$"))
async def cb_clear_blocked_users(client: Client, cq: CallbackQuery):
    """Blocked/deleted users ka data DB se hata do."""
    if not is_owner(cq.from_user.id):
        return await cq.answer("Owner only!", show_alert=True)
    await cq.answer("Clearing...", show_alert=False)
    from database import users_col
    result = users_col.delete_many({"is_blocked": True})
    deleted_count = result.deleted_count
    try:
        await cq.message.edit_text(
            f"✅ <b>Cleanup Complete!</b>\n\n"
            f"<b>{deleted_count}</b> blocked/deleted users ka data remove ho gaya.\n\n"
            f"Ab naya /stats check karo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 Stats", callback_data="noop")
            ]]),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass


@app.on_message(filters.command("deletead") & filters.private)
async def cmd_delete_ad(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    args = message.command[1:]
    if not args:
        return await message.reply("Usage: /deletead ad_id")
    ad_id    = args[0]
    ad       = db.get_ad(ad_id)
    if not ad:
        return await message.reply(f"Ad nahi mila: <code>{ad_id}</code>", parse_mode=enums.ParseMode.HTML)
    owner_id = ad["owner_id"]
    if ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception:
            pass
    db.delete_ad(ad_id)
    await message.reply(f"✅ Deleted! <code>{ad_id}</code>", parse_mode=enums.ParseMode.HTML)
    try:
        await client.send_message(
            owner_id,
            f"ℹ️ Tumhara ad delete kar diya gaya.\nAd ID: <code>{ad_id}</code>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass


@app.on_message(filters.command("broadcast") & filters.private)
async def cmd_broadcast(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.reply("Mega-broadcast queue ho raha hai...")
    await sched.mega_broadcast()
    await message.reply("✅ <b>Mega-Broadcast Queued!</b>", parse_mode=enums.ParseMode.HTML)


@app.on_message(filters.command("send_broadcast") & filters.private)
async def cmd_send_broadcast(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    db.save_ad_session(message.from_user.id, {"step": "awaiting_broadcast"})
    await message.reply(
        "📡 <b>Broadcast Mode Active!</b>\n\n"
        "Ab apna message bhejo (photo, video, text — kuch bhi).\n"
        "Bot woh sabhi users ko copy kar dega.\n\n"
        "Cancel: /cancel_broadcast",
        parse_mode=enums.ParseMode.HTML
    )


@app.on_message(filters.command("cancel_broadcast") & filters.private)
async def cmd_cancel_broadcast(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    db.clear_ad_session(message.from_user.id)
    await message.reply("Broadcast cancel ho gaya.")


async def _do_owner_broadcast(client: Client, message: Message, uid: int):
    users      = db.get_all_active_users()
    total      = len(users)
    success    = 0
    failed     = 0
    status_msg = await client.send_message(uid, f"📡 Broadcast shuru...\nTotal: {total}")
    for i, u in enumerate(users):
        try:
            await client.copy_message(
                chat_id      = u["user_id"],
                from_chat_id = message.chat.id,
                message_id   = message.id,
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            err = str(e)
            if "USER_IS_BLOCKED" in err or "deactivated" in err.lower() or "peer id invalid" in err.lower():
                db.mark_user_blocked(u["user_id"])
            failed += 1
        if (i + 1) % 100 == 0:
            try:
                await status_msg.edit_text(f"Progress: {i+1}/{total}\nOK: {success} | Failed: {failed}")
            except Exception:
                pass
    try:
        await status_msg.edit_text(
            f"✅ <b>Broadcast Complete!</b>\n\nTotal: {total}\nDelivered: {success}\nFailed: {failed}",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex("^noop$"))
async def cb_noop(client: Client, cq: CallbackQuery):
    await cq.answer()


@app.on_message(filters.command("admin") & filters.private)
async def cmd_admin(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    stats    = db.get_user_stats()
    reports  = len(db.get_pending_reports())
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    await message.reply(
        f"🛡 <b>Admin Panel</b>\n\n"
        f"Total: {stats['total']}  Active: {stats['active']}  Blocked: {stats['blocked']}\n"
        f"Reports: {reports}\n\n"
        f"Panel Password: <code>{password}</code>\n\n"
        "/stats  /broadcast  /send_broadcast\n"
        "/addforcesub  /removefchannel  /deletead\n"
        "/gencode — Redeem code generate karo",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥 Dashboard",     url=f"{WEBAPP_URL}/admin_panel"),
             InlineKeyboardButton("📡 Broadcast",     callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎟 Redeem Code Generate Karo", callback_data="admin_gen_redeem")],
        ]),
        parse_mode=enums.ParseMode.HTML
    )


@app.on_callback_query(filters.regex("^admin_gen_redeem$"))
async def cb_admin_gen_redeem(client: Client, cq: CallbackQuery):
    """Owner callback se redeem code generate kare."""
    if not is_owner(cq.from_user.id):
        return await cq.answer("Sirf owner!", show_alert=True)
    code = db.generate_redeem_code(OWNER_ID, max_uses=1)
    await cq.answer("Code generate ho gaya!", show_alert=False)
    await client.send_message(
        cq.from_user.id,
        f"🎟 <b>Naya Redeem Code Ready!</b>\n\n"
        f"Code: <code>{code}</code>\n\n"
        f"Limit: <b>1 user</b>\n"
        f"Value: <b>1 Free Ad</b>\n\n"
        f"Is code ko channel pe post karo!\n"
        f"User bot mein <code>#redeem {code}</code> likhega.",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Code Copy", switch_inline_query=code)],
        ])
    )


@app.on_message(filters.command("gencode") & filters.private)
async def cmd_gencode(client: Client, message: Message):
    """Owner /gencode [max_uses] se code generate kare."""
    if not is_owner(message.from_user.id):
        return
    args     = message.command[1:]
    max_uses = 1
    try:
        if args:
            max_uses = max(1, int(args[0]))
    except ValueError:
        pass
    code = db.generate_redeem_code(message.from_user.id, max_uses=max_uses)
    await message.reply(
        f"🎟 <b>Redeem Code Generate Ho Gaya!</b>\n\n"
        f"Code: <code>{code}</code>\n"
        f"Max Uses: <b>{max_uses}</b>\n"
        f"Value: <b>1 Free Ad per use</b>\n\n"
        f"User <code>#redeem {code}</code> bot mein likhe.",
        parse_mode=enums.ParseMode.HTML
    )


@app.on_message(filters.regex(r"^#redeem\s+(\S+)") & filters.private)
async def cmd_redeem_hashtag(client: Client, message: Message):
    """User #redeem CODE likhke code redeem kare."""
    uid  = message.from_user.id
    code = message.matches[0].group(1).strip()

    if not await force_sub_gate(client, uid):
        return

    result = db.redeem_code(code, uid)
    emoji  = "🎉" if result["success"] else "❌"
    await message.reply(
        f"{emoji} <b>{'Redeem Successful!' if result['success'] else 'Redeem Failed!'}</b>\n\n"
        f"{result['message']}",
        reply_markup=kb_main_menu() if result["success"] else InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Menu", callback_data="back_to_menu")]
        ]),
        parse_mode=enums.ParseMode.HTML
    )


# ══════════════════════════════════════════════════════════════════
#  MY POSTS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("myposts") & filters.private)
async def cmd_myposts(client: Client, message: Message):
    uid = message.from_user.id
    ads = db.get_user_ads(uid)
    if not ads:
        return await message.reply(
            "📭 Koi ad nahi hai.\n\nBanao: /createad",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")
            ]])
        )
    await _send_mypost_page(client, uid, ads, 0, message)


@app.on_callback_query(filters.regex("^myposts_view$"))
async def cb_myposts_view(client: Client, cq: CallbackQuery):
    uid = cq.from_user.id
    ads = db.get_user_ads(uid)
    if not ads:
        try:
            await cq.message.edit_text(
                "📭 Koi ad nahi hai.\n\nBanao:",
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
    caption = (ad.get("caption") or "")[:200]
    tags    = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    reach   = ad.get("reach", 0)
    likes   = ad.get("likes", 0)
    ad_id   = str(ad.get("_id", ""))
    s_emoji = {"approved": "✅", "pending": "⏳", "rejected": "❌", "deleted": "🗑", "completed": "🏆"}.get(status, "❓")

    text = (
        f"📋 <b>Meri Post {idx+1}/{total}</b>\n\n"
        f"Status: {s_emoji} <b>{status.upper()}</b>\n"
        f"Live Reach: <b>{reach} users</b>\n"
        f"Likes: <b>{likes}</b>\n"
        f"Tags: {tags or 'None'}\n\n"
        f"Caption:\n{caption}\n\n"
        f"Ad ID: <code>{ad_id}</code>"
    )

    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton("◀ Pehle", callback_data=f"mypost_nav_{idx-1}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton("Agle ▶", callback_data=f"mypost_nav_{idx+1}"))

    action_row = [InlineKeyboardButton("🗑 Delete", callback_data=f"mypost_del_{ad_id}_{idx}")]
    if ad.get("db_channel_msg_id"):
        action_row.insert(0, InlineKeyboardButton("👁 Post Dekho", callback_data=f"view_mypost_{ad_id}"))

    kb_rows = []
    if nav_row:    kb_rows.append(nav_row)
    kb_rows.append(action_row)
    kb_rows.append([
        InlineKeyboardButton("📢 Naya Ad", callback_data="start_create_ad"),
        InlineKeyboardButton("🏠 Menu",    callback_data="back_to_menu"),
    ])
    kb = InlineKeyboardMarkup(kb_rows)

    if edit:
        try:
            await message_or_cq.message.edit_text(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
    else:
        await message_or_cq.reply(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)


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
    await cq.answer("Deleted!")
    ads = db.get_user_ads(cq.from_user.id)
    if ads:
        await _send_mypost_page(client, cq.from_user.id, ads, min(idx, len(ads)-1), cq, edit=True)
    else:
        try:
            await cq.message.edit_text(
                "Saare ads delete ho gaye!\n/createad se naya banao.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")
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
    await cq.answer("📨 Post PM mein bhej raha hoon...")
    # FIXED: Seedha PM mein bhejo — channel link nahi dena
    try:
        await send_ad_to_user_with_controls(client, uid, ad)
    except Exception as e:
        await client.send_message(uid, f"❌ Post load nahi ho saka: {e}")


async def send_ad_to_user_with_controls(client: Client, uid: int, ad: dict):
    """Post PM mein bhejo with like + delete buttons."""
    ad_id   = str(ad["_id"])
    kb_data = ad.get("buttons", [])
    kb_rows = []
    for row in kb_data:
        kb_rows.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    liked = db.has_liked(ad_id, uid)
    likes = ad.get("likes", 0)
    reach = ad.get("reach", 0)
    kb_rows.append([
        InlineKeyboardButton(f"{'❤️' if liked else '🤍'} {likes}", callback_data=f"like_mypost_{ad_id}"),
        InlineKeyboardButton("🗑 Delete", callback_data=f"mypost_del_{ad_id}_0"),
    ])
    keyboard = InlineKeyboardMarkup(kb_rows)
    caption  = ad.get("caption", "")
    tags     = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    full_cap = f"{caption}\n\n{tags}".strip() if tags else caption
    full_cap += f"\n\nReach: {reach} | Likes: {likes}"
    mtype = ad.get("media_type", "text")
    fid   = ad.get("file_id")
    if mtype == "photo" and fid:
        await client.send_photo(uid, fid, caption=full_cap, reply_markup=keyboard)
    elif mtype == "video" and fid:
        await client.send_video(uid, fid, caption=full_cap, reply_markup=keyboard)
    elif mtype == "animation" and fid:
        await client.send_animation(uid, fid, caption=full_cap, reply_markup=keyboard)
    else:
        await client.send_message(uid, full_cap, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r"^like_mypost_(.+)$"))
async def cb_like_mypost(client: Client, cq: CallbackQuery):
    ad_id  = cq.matches[0].group(1)
    uid    = cq.from_user.id
    result = db.toggle_like(ad_id, uid)
    liked  = result["liked"]
    total  = result["total_likes"]
    await cq.answer(f"{'Liked!' if liked else 'Unliked!'}", show_alert=False)
    ad = db.get_ad(ad_id)
    if ad and liked and ad.get("owner_id") != uid:
        try:
            uname = f"@{cq.from_user.username}" if cq.from_user.username else cq.from_user.first_name
            await client.send_message(
                ad["owner_id"],
                f"❤️ <b>{uname}</b> ne tumhari post like ki!\nTotal likes: {total}",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
    try:
        msg = cq.message
        if msg.reply_markup:
            new_rows = []
            for row in msg.reply_markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data and btn.callback_data.startswith("like_mypost_"):
                        new_row.append(InlineKeyboardButton(
                            f"{'❤️' if liked else '🤍'} {total}",
                            callback_data=btn.callback_data
                        ))
                    else:
                        new_row.append(btn)
                new_rows.append(new_row)
            await msg.edit_reply_markup(InlineKeyboardMarkup(new_rows))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  BROWSE POSTS — Instagram reel style
# ══════════════════════════════════════════════════════════════════

def _browse_keyboard(idx: int, total: int, ad_id: str, liked: bool, likes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'❤️' if liked else '🤍'} {likes}", callback_data=f"like_post_{ad_id}_{idx}"),
            InlineKeyboardButton("🗑 Delete",                           callback_data=f"del_broadcast_{ad_id}"),
        ],
        [
            InlineKeyboardButton("◀ Pehli", callback_data=f"browse_posts_{idx-1}") if idx > 0 else InlineKeyboardButton(" ", callback_data="noop"),
            InlineKeyboardButton(f"{idx+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("Agli ▶", callback_data=f"browse_posts_{idx+1}") if idx < total-1 else InlineKeyboardButton(" ", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad"),
            InlineKeyboardButton("🏠 Menu",     callback_data="back_to_menu"),
        ],
    ])


async def _show_browse_post(client: Client, cq: CallbackQuery, idx: int):
    ads = db.get_all_browseable_ads()
    if not ads:
        try:
            await cq.message.edit_text(
                "📭 Abhi koi post nahi hai!\n\n/createad se pehla ad banao.",
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

    caption  = ad.get("caption", "") or ""
    tags     = " ".join([f"#{t}" for t in ad.get("hashtags", [])])
    full_cap = f"{caption}\n\n{tags}".strip() if tags else caption
    browse_cap = f"📌 Post {idx+1}/{total}\n\n{full_cap}\n\n{likes} likes"

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
    result = db.toggle_like(ad_id, uid)
    liked  = result["liked"]
    total  = result["total_likes"]
    await cq.answer(f"{'Liked!' if liked else 'Unliked!'}", show_alert=False)
    ad = db.get_ad(ad_id)
    if ad and liked and ad.get("owner_id") != uid:
        try:
            uname = f"@{cq.from_user.username}" if cq.from_user.username else cq.from_user.first_name
            cap_p = (ad.get("caption") or "")[:50]
            await client.send_message(
                ad["owner_id"],
                f"❤️ <b>{uname}</b> ne like kiya!\n{cap_p}...\nTotal: {total}",
                parse_mode=enums.ParseMode.HTML
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


@app.on_callback_query(filters.regex(r"^del_broadcast_(.+)$"))
async def cb_del_broadcast(client: Client, cq: CallbackQuery):
    """User apni PM se post hata sakta hai."""
    try:
        await cq.message.delete()
        await cq.answer("Post hata di!", show_alert=False)
    except Exception:
        await cq.answer("Delete nahi hua.", show_alert=True)


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

async def main():
    global BOT_USERNAME

    # ── Startup migration — purane stuck users fix ───────────────
    try:
        fixed = db.run_startup_migration()
        log.info(f"Startup migration complete: {fixed} users ke free_ads fix kiye")
    except Exception as e:
        log.warning(f"Migration error (non-fatal): {e}")

    # ── MongoDB Storage inject karo — restart-proof session ──────
    # Pyrogram 2.0.106 mein 'storage' param nahi hai, isliye directly override karte hain
    try:
        _mongo_uri = os.getenv("MONGO_URI", "")
        if _mongo_uri:
            from mongo_session import MongoStorage
            mongo_storage = MongoStorage("viral_bot", _mongo_uri)
            app.storage = mongo_storage
            log.info("MongoDB session storage injected — restart-proof!")
        else:
            log.warning("MONGO_URI missing — using in-memory session (peer id may reset on restart)")
    except Exception as e:
        log.warning(f"MongoDB storage inject failed: {e} — falling back to in-memory")

    await app.start()
    me = await app.get_me()
    BOT_USERNAME = me.username or BOT_USERNAME
    os.environ["BOT_USERNAME"] = BOT_USERNAME
    log.info(f"Bot started: @{BOT_USERNAME} | Author: @{_AUTHOR}")

    # ── Channels pre-resolve karo — peer id invalid fix ─────────
    channels_to_resolve = set()
    channels_to_resolve.add(DB_CHANNEL)
    channels_to_resolve.add(ADMIN_CHANNEL)
    channels_to_resolve.add(LOG_CHANNEL)

    try:
        fs_channels = db.get_all_forcesub_channels()
        for ch in fs_channels:
            channels_to_resolve.add(ch["channel_id"])
    except Exception:
        pass

    for ch_id in channels_to_resolve:
        if not ch_id or ch_id == 0:
            continue
        try:
            await app.get_chat(ch_id)
            log.info(f"Channel resolved OK: {ch_id}")
        except Exception as e:
            log.warning(f"Channel resolve issue {ch_id}: {e} — bot channel ka admin hai?")

    sched.set_client(app)
    scheduler = sched.build_scheduler()
    scheduler.start()
    log.info("Scheduler started. Bot running!")

    # ── Deploy startup message — LOG_CHANNEL ko batao ────────────
    try:
        stats       = db.get_user_stats()
        fs_channels = db.get_all_forcesub_channels()
        fs_list     = "\n".join(
            [f"  • {c.get('title','?')} ({c['channel_id']})" for c in fs_channels]
        ) or "  • Koi nahi set"

        startup_text = (
            f"🚀 <b>Bot Deploy Ho Gaya!</b>\n\n"
            f"🤖 Bot: @{BOT_USERNAME}\n"
            f"👥 Total Users: <b>{stats.get('total', 0)}</b>\n"
            f"✅ Active Users: <b>{stats.get('active', 0)}</b>\n\n"
            f"📡 <b>Force-Sub Channels:</b>\n{fs_list}\n\n"
            f"⏱ Broadcast Interval: <b>{sched.POST_INTERVAL} min</b>\n"
            f"🔄 Mega-Broadcast: <b>{sched.MEGA_TIMES}</b>\n\n"
            f"✅ <b>Sab set hai — bot ready hai!</b>\n"
            f"👨‍💻 Dev: @asbhaibsr"
        )
        await app.send_message(
            LOG_CHANNEL,
            startup_text,
            parse_mode=enums.ParseMode.HTML
        )
        log.info("Startup message sent to log channel.")
    except Exception as e:
        log.warning(f"Startup message send failed: {e}")
    # ──────────────────────────────────────────────────────────────

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
