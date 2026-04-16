import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
)

import scheduler as sched
import database as db
from utils.forcesub import check_subscription, build_join_buttons

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

# ── Bot Client ─────────────────────────────────────────────────────
app = Client(
    "viral_bot",
    api_id    = os.getenv("API_ID", "29970536"),
    api_hash  = os.getenv("API_HASH", "f4bfdcdd4a5c1b7328a7e4f25f024a09"),
    bot_token = os.getenv("BOT_TOKEN"),
    in_memory = True,
)

OWNER_ID      = int(os.getenv("OWNER_ID", "7315805581"))
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL_ID", "-1002717243409"))
DB_CHANNEL    = int(os.getenv("DATABASE_CHANNEL_ID", "-1002717243409"))
BOT_USERNAME  = os.getenv("BOT_USERNAME", "AdManagerfreebot")
_koyeb_domain = os.getenv("KOYEB_PUBLIC_DOMAIN", "desirable-eel-asmwasearchbot-5fb40cc5.koyeb.app")
WEBAPP_URL    = os.getenv("WEBAPP_URL", f"https://{_koyeb_domain}")
COPYRIGHT_MINS = os.getenv("COPYRIGHT_DELETE_MINUTES", "7")


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


# ── Keyboard Helpers ───────────────────────────────────────────────

def kb_dashboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Dashboard Kholo / Open Dashboard", web_app={"url": WEBAPP_URL})
    ]])


def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Dashboard Kholo", web_app={"url": WEBAPP_URL})],
        [InlineKeyboardButton("📢 Ad Banao / Create Ad", callback_data="start_create_ad")],
        [InlineKeyboardButton("👥 Refer Karo / Referral Link", callback_data="show_referral")],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="show_help")],
    ])


async def force_sub_gate(client: Client, user_id: int) -> bool:
    try:
        passed, missing = await check_subscription(client, user_id)
    except Exception as e:
        log.warning(f"force_sub_gate error for {user_id}: {e}")
        return True  # on error, let user through

    if not passed:
        try:
            kb = build_join_buttons(missing)
            await client.send_message(
                user_id,
                "⛔ **Ruko! Pehle Yeh Channels Join Karo**\n"
                "*(Wait! First join these channels)*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 Is bot ko use karne ke liye neeche diye gaye channels join karna zaroori hai.\n"
                "*(Joining the channels below is required to use this bot.)*\n\n"
                "✅ Har channel join karo\n"
                "✅ Phir '🔄 Maine Join Kar Liya' button dabao\n\n"
                "*(Join each channel, then press the check button below)*",
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

    # Referral tracking
    referred_by = None
    if args.startswith("ref_"):
        try:
            referred_by = int(args.split("_")[1])
        except (ValueError, IndexError):
            pass
    elif args == "create_ad":
        # Deep link from Mini App "Create Ad" button
        pass

    existing = db.get_user(user.id)
    full_name = (user.first_name or "") + (" " + user.last_name if getattr(user, "last_name", None) else "")
    db.get_or_create_user(user.id, user.username or "", full_name.strip() or "")

    if not existing and referred_by and referred_by != user.id:
        unlocked = db.add_referral(referred_by, user.id)
        if unlocked:
            try:
                referrer = db.get_user(referred_by)
                await client.send_message(
                    referred_by,
                    "🎉 **10 Referrals Complete! Mubarak Ho!**\n"
                    "*(Congratulations! 10 Referrals Done!)*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎁 **1 Free Ad Slot Unlock Ho Gaya!**\n"
                    "*(1 Free Ad Slot has been unlocked!)*\n\n"
                    "Ab apna ad banao aur 50,000+ users tak pahuncho!\n"
                    "*(Now create your ad and reach 50,000+ users!)*",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 Abhi Ad Banao!", callback_data="start_create_ad")],
                        [InlineKeyboardButton("🚀 Dashboard Dekho", web_app={"url": WEBAPP_URL})],
                    ])
                )
            except Exception:
                pass

    if not await force_sub_gate(client, user.id):
        return

    # Deep link → direct to ad creation
    if args == "create_ad":
        db.save_ad_session(user.id, {"step": "media"})
        return await message.reply(
            "🎨 **Ad Banana Shuru Karo! / Let's Create Your Ad!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Step 1 of 4 — Media Bhejo / Send Media** 📸\n\n"
            "📷 Photo bhejo → Image ad banega\n"
            "🎬 Video bhejo → Video ad banega\n"
            "*(Send a photo for image ad, or video for video ad)*\n\n"
            "💡 **Tip:** High quality image ya video se zyada clicks milte hain!\n"
            "*(High quality media gets more clicks!)*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")
            ]])
        )

    is_new = not existing
    await message.reply(
        f"{'🎉 **Swaagat Hai! / Welcome!**' if is_new else '👋 **Wapas Aao! / Welcome Back!**'} "
        f"**{user.first_name}** 🙌\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 **50,000+ USERS TAK PAHUNCHO — BILKUL FREE!**\n"
        "*(Reach 50,000+ Users — Absolutely FREE!)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📢 **Yeh Bot Kya Karta Hai? / What does this bot do?**\n"
        "Aapka content — channel, post, product, link — hum broadcasting karke "
        "**50,000+ active Telegram users** tak pahunchate hain. FREE mein!\n"
        "*(We broadcast your content to 50,000+ active users. For free!)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 **Free Ad Kaise Milega? / How to get a Free Ad?**\n\n"
        "🔥 **Tarika 1 — Daily Streak:**\n"
        "   Har roz bot pe check-in karo\n"
        "   7 din lagatar → **1 Free Ad Slot!**\n"
        "   *(Check-in daily for 7 days → Free Ad)*\n\n"
        "👥 **Tarika 2 — Refer Karo:**\n"
        "   10 dosto ko bot use karwao\n"
        "   → **1 Instant Free Ad!**\n"
        "   *(Get 10 friends to join → Instant Free Ad)*\n\n"
        "✅ **Tarika 3 — Direct Ad Banao:**\n"
        "   Neeche button dabao → Media + Text bhejo\n"
        "   → Admin approve karega → Live ho jaayega! 📡\n"
        "   *(Press button → Send media + text → Goes live after approval)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 **Live Numbers:** 50k+ Users | 10k+ Reach/Ad | 100+ Daily Posts\n\n"
        "⬇️ **Shuru Karo! / Get Started!**",
        reply_markup=kb_main_menu()
    )


# ══════════════════════════════════════════════════════════════════
#  Force-Sub Check Callback
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("^check_sub$"))
async def cb_check_sub(client: Client, cq: CallbackQuery):
    passed, missing = await check_subscription(client, cq.from_user.id)
    if passed:
        await cq.message.delete()
        await client.send_message(
            cq.from_user.id,
            "✅ **Sab Channels Join Ho Gaye!**\n"
            "*(All channels joined successfully!)*\n\n"
            "Ab aap bot ka poora faida utha sakte ho!\n"
            "*(You can now use all bot features!)*",
            reply_markup=kb_main_menu()
        )
    else:
        await cq.answer(
            f"❌ Abhi bhi {len(missing)} channel(s) baaki hain! Pehle join karo.",
            show_alert=True
        )


# ══════════════════════════════════════════════════════════════════
#  Start Menu Callbacks
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("^show_referral$"))
async def cb_show_referral(client: Client, cq: CallbackQuery):
    user   = db.get_user(cq.from_user.id)
    if not user:
        return await cq.answer("User not found", show_alert=True)

    uid        = cq.from_user.id
    ref_count  = user.get("referral_count", 0)
    free_ads   = user.get("free_ads_earned", 0)
    next_in    = 10 - (ref_count % 10)
    ref_link   = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

    await cq.message.edit_text(
        "👥 **Referral Program / Refer Karo Kamao!**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Tumhara Score / Your Score:**\n"
        f"   🔗 Total Referrals: **{ref_count}**\n"
        f"   🎁 Free Ads Earned: **{free_ads}**\n"
        f"   ⏳ Next Free Ad: **{next_in} aur refers chahiye**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **Tumhara Referral Link / Your Link:**\n"
        f"`{ref_link}`\n\n"
        "*(Is link ko copy karke dosto ko bhejo)*\n"
        "*(Copy this link and share with friends)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 **Kaise Kaam Karta Hai? / How it works?**\n\n"
        "1️⃣ Apna link dosto ko share karo\n"
        "    *(Share your link with friends)*\n"
        "2️⃣ Dost link se bot start kare\n"
        "    *(Friend starts bot using your link)*\n"
        "3️⃣ Tumhara referral count +1 ho jaata hai\n"
        "    *(Your count goes up by 1)*\n"
        "4️⃣ **10 refers = 1 Free Ad Slot! 🎁**\n"
        "    *(Every 10 refers = 1 Free Ad Slot)*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Dosto Ko Share Karo", url=f"https://t.me/share/url?url={ref_link}&text=🚀+Yeh+bot+se+FREE+promotion+milta+hai!")],
            [InlineKeyboardButton("🚀 Dashboard Dekho", web_app={"url": WEBAPP_URL})],
            [InlineKeyboardButton("🔙 Wapas / Back", callback_data="back_to_menu")],
        ])
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^show_help$"))
async def cb_show_help(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(
        "❓ **Help & Commands / Madad aur Commands**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 **User Commands:**\n\n"
        "▶️ `/start` — Bot start karo\n"
        "    *(Start the bot)*\n\n"
        "📢 `/createad` — Naya ad banao\n"
        "    *(Create a new advertisement)*\n\n"
        "🔍 `/search <keyword>` — Posts search karo\n"
        "    Example: `/search bollywood` ya `/search tech`\n"
        "    *(Search posts by keyword)*\n\n"
        "✅ `/done` — Ad finalize karo (creation ke time)\n"
        "    *(Finalize your ad during creation)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ **Admin Only Commands:**\n\n"
        "📊 `/stats` — Bot statistics dekho\n"
        "➕ `/addforcesub -100xxxxx` — Force-sub channel add karo\n"
        "➖ `/removefchannel -100xxxxx` — Channel remove karo\n"
        "🗑️ `/deletead <id>` — Koi bhi ad delete karo\n"
        "📡 `/broadcast` — Manual mega-broadcast\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Tips / Sujhaav:**\n\n"
        "• Roz check-in karo streak banao → Free ads pao\n"
        "  *(Daily check-in builds streak → earns Free Ads)*\n"
        "• High quality image/video use karo ads mein\n"
        "  *(Use high quality media for better results)*\n"
        "• Copyright content mat daalo — auto-delete hoga\n"
        "  *(No copyright content — gets auto-deleted)*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Ad Banao", callback_data="start_create_ad")],
            [InlineKeyboardButton("🔙 Wapas / Back", callback_data="back_to_menu")],
        ])
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^back_to_menu$"))
async def cb_back_menu(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(
        "🏠 **Main Menu / Mukhya Menu**\n\n"
        "Neeche se choose karo / Choose from below:",
        reply_markup=kb_main_menu()
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^cancel_ad$"))
async def cb_cancel_ad(client: Client, cq: CallbackQuery):
    db.clear_ad_session(cq.from_user.id)
    await cq.message.edit_text(
        "❌ **Ad Creation Cancel Ho Gaya**\n"
        "*(Ad creation has been cancelled)*\n\n"
        "Jab chahein dobara shuru kar sakte ho!\n"
        "*(You can restart anytime!)*",
        reply_markup=kb_main_menu()
    )
    await cq.answer("Cancelled!")


# ══════════════════════════════════════════════════════════════════
#  ADMIN: /addforcesub
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addforcesub") & filters.private)
async def cmd_add_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply(
            "❌ **Permission Denied!**\n"
            "Yeh command sirf bot owner use kar sakta hai.\n"
            "*(Only the bot owner can use this command.)*"
        )

    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        ch_list  = "\n".join([f"  • `{c['channel_id']}` — {c.get('title','?')}" for c in channels]) or "  _(Koi nahi / None)_"
        return await message.reply(
            "📢 **Force-Sub Channel Add Karo**\n"
            "*(Add a Force-Subscribe Channel)*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Usage / Tarika:**\n"
            "`/addforcesub -100xxxxxxxxxx`\n\n"
            "**Zaroori Steps / Required Steps:**\n"
            "1️⃣ Bot ko us channel ka **Admin** banao\n"
            "    *(Make bot admin in that channel)*\n"
            "2️⃣ Bot ko **Invite Users** permission do\n"
            "    *(Give bot 'Invite Users' permission)*\n"
            "3️⃣ Phir yeh command chalao\n"
            "    *(Then run this command)*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Abhi Active Channels / Currently Active:**\n{ch_list}"
        )

    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply(
            "❌ **Galat ID Format!**\n"
            "*(Wrong ID format!)*\n\n"
            "Sahi format: `-100xxxxxxxxxx`\n"
            "Example: `/addforcesub -1001234567890`"
        )

    await message.reply("⏳ Channel check ho raha hai... *(Checking channel...)*")

    try:
        chat  = await client.get_chat(ch_id)
        title = chat.title or str(ch_id)
        try:
            link_obj    = await client.create_chat_invite_link(
                ch_id, creates_join_request=True, name="ForceSub Link"
            )
            invite_link = link_obj.invite_link
        except Exception:
            invite_link = getattr(chat, "invite_link", "") or ""
    except Exception as e:
        return await message.reply(
            f"❌ **Channel Info Nahi Mili!**\n"
            f"*(Could not fetch channel info!)*\n\n"
            f"Error: `{e}`\n\n"
            f"**Confirm karo:**\n"
            f"✅ Bot us channel mein admin hai?\n"
            f"✅ Channel ID sahi hai? (`-100` se shuru hona chahiye)\n"
            f"*(Make sure bot is admin and channel ID starts with -100)*"
        )

    added = db.add_forcesub_channel(ch_id, invite_link, title)
    if added:
        await message.reply(
            f"✅ **Force-Sub Channel Add Ho Gaya!**\n"
            f"*(Force-Sub Channel Added Successfully!)*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **Channel:** {title}\n"
            f"🆔 **ID:** `{ch_id}`\n"
            f"🔗 **Join Request Link:**\n`{invite_link}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ Ab naye users ko pehle is channel mein join request bhejna hoga.\n"
            f"*(New users must send join request to this channel first.)*\n\n"
            f"📝 **Note:** Private channel hai to admin manually requests approve karega.\n"
            f"*(For private channels, admin approves requests manually.)*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➖ Remove Karo", callback_data=f"remove_fsub_{ch_id}")
            ]])
        )
    else:
        await message.reply(
            f"⚠️ **Yeh Channel Pehle Se Add Hai!**\n"
            f"*(This channel is already in the force-sub list!)*\n\n"
            f"Channel: **{title}** (`{ch_id}`)\n\n"
            f"Remove karne ke liye:\n`/removefchannel {ch_id}`"
        )


@app.on_callback_query(filters.regex(r"^remove_fsub_(-\d+)$"))
async def cb_remove_fsub_quick(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Owner only!", show_alert=True)
    ch_id = int(cq.matches[0].group(1))
    removed = db.remove_forcesub_channel(ch_id)
    if removed:
        await cq.message.edit_text(
            f"✅ Channel `{ch_id}` force-sub list se hata diya gaya!\n"
            f"*(Channel removed from force-sub list!)*"
        )
        await cq.answer("Removed!")
    else:
        await cq.answer("Already removed!", show_alert=True)


# ══════════════════════════════════════════════════════════════════
#  ADMIN: /removefchannel
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("removefchannel") & filters.private)
async def cmd_remove_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Sirf owner use kar sakta hai! *(Owner only!)*")

    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        if not channels:
            return await message.reply(
                "📭 **Koi Force-Sub Channel Set Nahi Hai**\n"
                "*(No force-sub channels configured)*\n\n"
                "Add karne ke liye:\n`/addforcesub -100xxxxxxxxxx`"
            )
        lines = "\n".join([f"  • `{c['channel_id']}` — **{c.get('title','?')}**" for c in channels])
        return await message.reply(
            "📋 **Active Force-Sub Channels:**\n\n"
            f"{lines}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Remove karne ke liye / To remove:**\n"
            "`/removefchannel -100xxxxxxxxxx`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"❌ Remove: {c.get('title','?')}", callback_data=f"remove_fsub_{c['channel_id']}")]
                for c in channels
            ])
        )

    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply("❌ Galat ID! *(Wrong ID!)*\nFormat: `-100xxxxxxxxxx`")

    removed = db.remove_forcesub_channel(ch_id)
    if removed:
        await message.reply(
            f"✅ **Channel Remove Ho Gaya!**\n"
            f"*(Channel removed successfully!)*\n\n"
            f"🆔 ID: `{ch_id}`\n\n"
            f"Ab users ko is channel ko join karna zaroori nahi hoga.\n"
            f"*(Users no longer need to join this channel.)*"
        )
    else:
        await message.reply(
            f"❌ **Channel Nahi Mila List Mein!**\n"
            f"*(Channel not found in the list!)*\n\n"
            f"ID: `{ch_id}`\n\n"
            f"Active channels dekhne ke liye: `/removefchannel`"
        )


# ══════════════════════════════════════════════════════════════════
#  /search
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("search") & filters.private)
async def cmd_search(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply(
            "🔍 **Search Karo / Search Posts**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Usage / Tarika:**\n"
            "`/search <keyword>`\n\n"
            "**Examples / Udaharan:**\n"
            "• `/search kalki movie`\n"
            "• `/search tech gadgets`\n"
            "• `/search bollywood songs`\n"
            "• `/search business tips`\n\n"
            "🔎 Inline mode bhi use kar sakte ho:\n"
            f"*(You can also use inline mode:)*\n"
            f"`@{BOT_USERNAME} kalki`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Inline Search Try Karo",
                    switch_inline_query_current_chat="")
            ]])
        )

    query   = " ".join(args)
    results = db.search_ads(query, limit=5)

    if not results:
        return await message.reply(
            f"😕 **Koi Result Nahi Mila!**\n"
            f"*(No results found!)*\n\n"
            f"🔍 Search: **\"{query}\"**\n\n"
            f"**Suggestions / Sujhaav:**\n"
            f"• Alag keyword try karo *(Try a different keyword)*\n"
            f"• Chota keyword likho *(Use shorter keyword)*\n"
            f"• Hashtag try karo *(Try a hashtag)*\n\n"
            f"Example: `/search movie` ya `/search tech`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Dobara Search Karo",
                    switch_inline_query_current_chat=query)
            ]])
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

    buttons.append([InlineKeyboardButton(
        "🔍 Aur Search Karo / Search More",
        switch_inline_query_current_chat=query
    )])

    await message.reply(
        f"🔍 **Search Results / Khoj Nateeja**\n\n"
        f"Query: **\"{query}\"**\n"
        f"Found: **{len(results)} post(s)**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Neeche diye buttons pe click karke post dekho 👇\n"
        f"*(Click the buttons below to view posts)*\n\n"
        f"⚠️ **Note:** Copyright posts auto-delete ho jaate hain.\n"
        f"*(Copyright posts are auto-deleted.)*",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ══════════════════════════════════════════════════════════════════
#  Inline Query
# ══════════════════════════════════════════════════════════════════

@app.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    q = query.query.strip()
    if not q:
        await query.answer(
            results=[],
            switch_pm_text="🔍 Kuch type karo search karne ke liye",
            switch_pm_parameter="help",
            cache_time=5
        )
        return

    results_db    = db.search_ads(q, limit=5)
    ch_str        = str(DB_CHANNEL).replace("-100", "")
    inline_results = []

    for ad in results_db:
        caption  = (ad.get("caption", "") or "")[:200]
        tags     = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        msg_id   = ad.get("db_channel_msg_id")
        post_url = f"https://t.me/c/{ch_str}/{msg_id}" if msg_id else "https://t.me"

        inline_results.append(
            InlineQueryResultArticle(
                title       = caption[:60] or q,
                description = tags or "Post dekho / View post",
                input_message_content=InputTextMessageContent(
                    f"📌 **{caption[:150]}**\n\n"
                    f"🏷️ {tags}\n\n"
                    f"[➡️ Post Dekho / View Post]({post_url})"
                ),
            )
        )

    if not inline_results:
        await query.answer(
            results=[],
            switch_pm_text=f"❌ '{q}' ke liye koi result nahi",
            switch_pm_parameter="search",
            cache_time=5
        )
        return

    await query.answer(inline_results, cache_time=30)


# ══════════════════════════════════════════════════════════════════
#  AD CREATION FLOW
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("createad") & filters.private)
@app.on_callback_query(filters.regex("^start_create_ad$"))
async def cmd_create_ad(client, update):
    """Handle both /createad command and button callback."""
    is_cb = isinstance(update, CallbackQuery)
    user  = update.from_user

    if not await force_sub_gate(client, user.id):
        if is_cb:
            await update.answer()
        return

    db.save_ad_session(user.id, {"step": "media"})

    text = (
        "🎨 **Ad Banana Shuru Karo! / Let's Create Your Ad!**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Step 1 of 4 — Media Bhejo / Send Media** 📸\n\n"
        "📷 **Photo bhejo** → Image ad banega\n"
        "   *(Send a photo → creates image ad)*\n"
        "🎬 **Video bhejo** → Video ad banega\n"
        "   *(Send a video → creates video ad)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Tips:**\n"
        "• Clear, attractive image use karo\n"
        "• 1:1 ya 16:9 ratio best hota hai\n"
        "• *(Use clear images, 1:1 or 16:9 ratio works best)*"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")
    ]])

    if is_cb:
        await update.message.edit_text(text, reply_markup=kb)
        await update.answer()
    else:
        await update.reply(text, reply_markup=kb)


@app.on_message(
    filters.private
    & (filters.photo | filters.video | filters.animation | filters.text)
    & ~filters.command(["start","search","addforcesub","removefchannel",
                        "createad","stats","broadcast","deletead","done"])
)
async def handle_ad_creation(client: Client, message: Message):
    """Multi-step ad creation state machine."""
    uid     = message.from_user.id
    session = db.get_ad_session(uid)
    if not session:
        return

    step = session.get("step", "")

    # ── Step 1: Media ─────────────────────────────────────────────
    if step == "media":
        if message.photo:
            media_type, file_id = "photo",     message.photo.file_id
        elif message.video:
            media_type, file_id = "video",     message.video.file_id
        elif message.animation:
            media_type, file_id = "animation", message.animation.file_id
        else:
            return await message.reply(
                "❌ **Sirf Photo ya Video Bhejo!**\n"
                "*(Please send only a photo or video!)*\n\n"
                "Text messages is step mein accept nahi hote.\n"
                "*(Text messages are not accepted in this step.)*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")
                ]])
            )
        db.save_ad_session(uid, {"step": "caption", "media_type": media_type, "file_id": file_id})
        await message.reply(
            f"✅ **{media_type.title()} Mil Gaya! / {media_type.title()} Received!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Step 2 of 4 — Caption Likho / Write Caption** ✏️\n\n"
            "📝 Apne ad ka text likho:\n"
            "*(Write the text for your ad:)*\n\n"
            "• Kya promote kar rahe ho? *(What are you promoting?)*\n"
            "• Link ya contact bhi daal sakte ho\n"
            "  *(You can include a link or contact)*\n"
            "• Max **1024 characters**\n\n"
            "💡 **Achi Caption = Zyada Clicks!**\n"
            "*(Good caption = More clicks!)*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")
            ]])
        )

    # ── Step 2: Caption ───────────────────────────────────────────
    elif step == "caption":
        if not message.text:
            return await message.reply(
                "❌ **Text Mein Caption Likho!**\n"
                "*(Please write caption as text!)*\n\n"
                "Media ya sticker nahi, sirf text chahiye.\n"
                "*(No media or stickers, text only please.)*"
            )
        caption = message.text[:1024]
        db.save_ad_session(uid, {"step": "hashtags", "caption": caption})
        await message.reply(
            f"✅ **Caption Save Ho Gaya! / Caption Saved!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Step 3 of 4 — Hashtags Daalo / Add Hashtags** 🏷️\n\n"
            f"1-5 hashtags likho (space se alag karo):\n"
            f"*(Write 1-5 hashtags, separated by spaces):*\n\n"
            f"**Format:** `#tag1 #tag2 #tag3`\n\n"
            f"**Examples / Udaharan:**\n"
            f"• `#bollywood #movie #entertainment`\n"
            f"• `#techgadgets #deals #offer`\n"
            f"• `#business #startup #india`\n\n"
            f"💡 Sahi hashtag se zyada log tumhara ad dekhenge!\n"
            f"*(Right hashtags help more people find your ad!)*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")
            ]])
        )

    # ── Step 3: Hashtags ──────────────────────────────────────────
    elif step == "hashtags":
        if not message.text:
            return await message.reply(
                "❌ **Hashtags Text Mein Likho!**\n"
                "*(Please write hashtags as text!)*\n\n"
                "Format: `#tag1 #tag2`"
            )
        tags = [t.lstrip("#").lower().strip() for t in message.text.split() if t.startswith("#") and len(t) > 1]
        if not tags:
            return await message.reply(
                "❌ **Koi Valid Hashtag Nahi Mila!**\n"
                "*(No valid hashtag found!)*\n\n"
                "Hashtag `#` se shuru hona chahiye.\n"
                "*(Hashtags must start with #)*\n\n"
                "Example: `#movie #tech #deals`"
            )
        tags = tags[:5]
        tags_display = " ".join([f"**#{t}**" for t in tags])
        db.save_ad_session(uid, {"step": "buttons", "hashtags": tags})
        await message.reply(
            f"✅ **Hashtags Save! / Hashtags Saved!**\n"
            f"Tags: {tags_display}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Step 4 of 4 — Inline Buttons (Optional) / Buttons** 🔗\n\n"
            f"Apne ad mein clickable buttons add karo.\n"
            f"*(Add clickable buttons to your ad.)*\n\n"
            f"**Format / Tarika:**\n"
            f"`Button ka naam | https://yourlink.com`\n"
            f"Ek line = ek button (max 3)\n\n"
            f"**Example:**\n"
            f"`Channel Join Karo | https://t.me/yourchannel`\n"
            f"`Website Dekho | https://yourwebsite.com`\n\n"
            f"Buttons nahi chahiye? Neeche 'Skip' dabao.\n"
            f"*(Don't want buttons? Press Skip below.)*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Skip Buttons / Buttons Mat Add Karo", callback_data="skip_buttons")],
                [InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")],
            ])
        )

    # ── Step 4: Buttons ───────────────────────────────────────────
    elif step == "buttons":
        if not message.text:
            return await message.reply(
                "❌ **Text Mein Buttons Likho!**\n"
                "Format: `Title | https://link.com`\n"
                "Ya skip karo neeche button se."
            )
        rows = []
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
                "❌ **Galat Format!** *(Wrong format!)*\n\n"
                "Sahi format:\n`Button Name | https://link.com`\n\n"
                f"Tumhari line: `{errors[0]}`\n\n"
                "Link `https://` se shuru hona chahiye.\n"
                "*(Link must start with https://)*"
            )

        db.save_ad_session(uid, {"step": "position", "buttons": rows})
        await _show_position_editor(client, uid, rows)

    # ── Done shortcut via text ────────────────────────────────────
    elif step == "position":
        pass  # handled by /done command


@app.on_message(filters.command("done") & filters.private)
async def cmd_done(client: Client, message: Message):
    session = db.get_ad_session(message.from_user.id)
    if session and session.get("step") in ("buttons", "position"):
        await _finalize_ad(client, message.from_user, session)
    else:
        await message.reply(
            "❌ **Koi Active Ad Session Nahi Hai**\n"
            "*(No active ad creation session)*\n\n"
            "Naya ad banane ke liye:\n`/createad`"
        )


@app.on_callback_query(filters.regex("^skip_buttons$"))
async def cb_skip_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expire ho gaya. /createad se dobara shuru karo.", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "position", "buttons": []})
    await cq.message.edit_text(
        "⏭️ **Buttons Skip Kiye / Buttons Skipped**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 **Ad Almost Ready! / Ad Tayyar Hone Wala Hai!**\n\n"
        "Sab kuch theek lag raha hai? Submit karo!\n"
        "*(Everything looks good? Submit it!)*\n\n"
        "**Ad ko Submit karne ke baad:**\n"
        "1️⃣ Admin review karega *(Admin will review)*\n"
        "2️⃣ Approve hone par queue mein jaayega *(Goes to queue after approval)*\n"
        "3️⃣ 50,000+ users tak pahunchega! *(Reaches 50,000+ users!)*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Submit Ad / Bhejo!", callback_data="submit_ad")],
            [InlineKeyboardButton("❌ Cancel / Roko", callback_data="cancel_ad")],
        ])
    )
    await cq.answer()


@app.on_callback_query(filters.regex("^submit_ad$"))
async def cb_submit_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer(
            "Session expire ho gaya! /createad se dobara shuru karo.",
            show_alert=True
        )
    await cq.message.edit_text(
        "⏳ **Ad Submit Ho Raha Hai...**\n"
        "*(Submitting your ad...)*\n\n"
        "Please wait... 🔄"
    )
    await _finalize_ad(client, cq.from_user, session)


async def _show_position_editor(client: Client, user_id: int, buttons: list):
    layout = _render_button_layout(buttons)
    await client.send_message(
        user_id,
        f"🔧 **Button Arrangement / Button Position**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Current Layout / Abhi Ka Layout:**\n"
        f"{layout}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Buttons upar-neeche ya left-right move karo.\n"
        f"*(Move buttons up/down or left/right.)*\n\n"
        f"✅ Sab theek hai? Submit karo!",
        reply_markup=_position_keyboard(buttons, 0)
    )


def _render_button_layout(buttons: list) -> str:
    if not buttons:
        return "_(Koi buttons nahi / No buttons)_"
    text = ""
    for i, row in enumerate(buttons):
        names = " | ".join([f"[{b['text']}]" for b in row])
        text += f"Row {i+1}: {names}\n"
    return text


def _position_keyboard(buttons: list, selected: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬆️ Upar / Up",    callback_data=f"btn_up_{selected}")],
        [
            InlineKeyboardButton("⬅️ Baayein / Left",  callback_data=f"btn_left_{selected}"),
            InlineKeyboardButton("Daayein / Right ➡️", callback_data=f"btn_right_{selected}"),
        ],
        [InlineKeyboardButton("⬇️ Neeche / Down", callback_data=f"btn_down_{selected}")],
        [InlineKeyboardButton("🚀 Submit Karo! / Submit Ad!", callback_data="submit_ad")],
        [InlineKeyboardButton("❌ Cancel / Roko",            callback_data="cancel_ad")],
    ])


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

    if direction == "up" and idx > 0:
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
    await cq.message.edit_text(
        f"🔧 **Layout Update Ho Gaya! / Layout Updated!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{_render_button_layout(buttons)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Theek lag raha hai? Submit karo!",
        reply_markup=_position_keyboard(buttons, idx)
    )
    await cq.answer("✅ Updated!")


async def _finalize_ad(client, user, session: dict):
    """Store in DB channel → create ad record → send to admin for approval."""
    uid       = user.id
    tags_text = " ".join([f"#{t}" for t in session.get("hashtags", [])])
    caption   = session.get("caption", "") or ""
    full_cap  = f"{caption}\n\n{tags_text}".strip()

    from utils.broadcaster import _build_keyboard
    kb_data    = session.get("buttons", [])
    buttons_kb = _build_keyboard(kb_data) if kb_data else None

    # 1. Store post in DB channel
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
        return await client.send_message(
            uid,
            f"❌ **Ad Submit Nahi Ho Saka!**\n"
            f"*(Ad could not be submitted!)*\n\n"
            f"Error: `{e}`\n\n"
            f"Dobara try karo: `/createad`"
        )

    # 2. Save ad to MongoDB
    ad_id = db.create_ad(uid, {**session, "db_channel_msg_id": db_msg.id})

    # 3. Send to admin channel for approval
    await client.send_message(
        ADMIN_CHANNEL,
        f"📢 **Naya Ad Approval Chahiye / New Ad Needs Approval**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** [{user.first_name}](tg://user?id={uid}) (`{uid}`)\n"
        f"🆔 **Ad ID:** `{ad_id}`\n"
        f"📝 **Caption:** {caption[:200]}\n"
        f"🏷️ **Tags:** {tags_text}\n"
        f"🔗 **Buttons:** {len(kb_data)} row(s)\n"
        f"📦 **Type:** {session.get('media_type','text').title()}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Approve = Queue mein jaayega\n"
        f"❌ Reject = User ko reject notification\n"
        f"🚫 Copyright = Flag + {COPYRIGHT_MINS} min mein auto-delete",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve",    callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton("❌ Reject",     callback_data=f"reject_{ad_id}"),
            InlineKeyboardButton("🚫 Copyright", callback_data=f"copyright_{ad_id}"),
        ]])
    )

    db.clear_ad_session(uid)
    await client.send_message(
        uid,
        "🎉 **Ad Submit Ho Gaya! / Ad Submitted Successfully!**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **Ad ID:** `{ad_id}`\n\n"
        "**Aage Kya Hoga? / What happens next?**\n\n"
        "1️⃣ ⏳ Admin tumhara ad review karega\n"
        "    *(Admin will review your ad)*\n"
        "2️⃣ ✅ Approve hone par queue mein add hoga\n"
        "    *(After approval, it goes to broadcast queue)*\n"
        f"3️⃣ 📡 Har {os.getenv('POST_INTERVAL_MINUTES','10')} minute mein ek post jaata hai\n"
        "    *(One post goes out every 10 minutes)*\n"
        "4️⃣ 🚀 **50,000+ users tak pahunchega!**\n"
        "    *(Reaches 50,000+ users!)*\n\n"
        "📊 Dashboard mein status track karo!\n"
        "*(Track status in your dashboard!)*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Dashboard Dekho / View Dashboard", web_app={"url": WEBAPP_URL})],
            [InlineKeyboardButton("📢 Aur Ad Banao / Create More Ads", callback_data="start_create_ad")],
        ])
    )


# ══════════════════════════════════════════════════════════════════
#  ADMIN APPROVAL CALLBACKS
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^approve_(.+)$"))
async def cb_approve(client: Client, cq: CallbackQuery):
    if not is_owner(cq.from_user.id):
        return await cq.answer("❌ Sirf owner kar sakta hai!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.approve_ad(ad_id)
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ APPROVED — Queue Mein Hai", callback_data="noop")
    ]]))
    await cq.answer("✅ Ad approved & queued!")

    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                "🎊 **Tumhara Ad APPROVE Ho Gaya! / Your Ad is APPROVED!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "✅ **Broadcasting queue mein add ho gaya!**\n"
                "*(Added to broadcasting queue!)*\n\n"
                f"⏰ Approximately har {os.getenv('POST_INTERVAL_MINUTES','10')} minute mein ek post\n"
                "*(Approx one post every 10 minutes)*\n\n"
                "🚀 Jaldi hi 50,000+ users tak pahunchega!\n"
                "*(Will reach 50,000+ users very soon!)*\n\n"
                "📊 Dashboard mein live reach track karo!\n"
                "*(Track live reach in your dashboard!)*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Reach Track Karo", web_app={"url": WEBAPP_URL})
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
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ REJECTED", callback_data="noop")
    ]]))
    await cq.answer("Ad rejected.")

    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                "😔 **Tumhara Ad Reject Ho Gaya / Your Ad Was Rejected**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "**Possible Reasons / Sambhavit Karan:**\n"
                "• Ad unclear ya low quality tha\n"
                "  *(Ad was unclear or low quality)*\n"
                "• Misleading content tha\n"
                "  *(Content was misleading)*\n"
                "• Guidelines violate ki thi\n"
                "  *(Guidelines were violated)*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔄 **Dobara Try Karo / Try Again:**\n"
                "• High quality media use karo\n"
                "• Clear aur honest caption likho\n"
                "• Copyright content mat daalo",
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
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🚫 COPYRIGHT — {COPYRIGHT_MINS}min mein DELETE", callback_data="noop")
    ]]))
    await cq.answer(f"⚠️ Flagged! Auto-delete in {COPYRIGHT_MINS} minutes.")

    ad = db.get_ad(ad_id)
    if ad:
        try:
            await client.send_message(
                ad["owner_id"],
                f"⚠️ **Copyright Warning! / Copyright Ullanghghan!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Ad ID: `{ad_id}`\n\n"
                "🚫 **Tumhare ad mein copyright content detect hua hai.**\n"
                "*(Copyright content was detected in your ad.)*\n\n"
                f"⏰ Yeh post **{COPYRIGHT_MINS} minutes** mein auto-delete ho jaayega.\n"
                f"*(This post will be auto-deleted in {COPYRIGHT_MINS} minutes.)*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📋 **Copyright Content Kya Hota Hai?**\n"
                "*(What counts as copyright content?)*\n\n"
                "• Movies, web series ke clips/posters\n"
                "• Pirated software ya apps\n"
                "• Kisi aur ka music ya video bina permission\n"
                "• *(Movie clips, pirated software, unauthorized music/video)*\n\n"
                "✅ **Agli baar original content use karo!**\n"
                "*(Use original content next time!)*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Original Ad Banao", callback_data="start_create_ad")
                ]])
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  USER: Report a Post
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^report_(.+)$"))
async def cb_report(client: Client, cq: CallbackQuery):
    ad_id    = cq.matches[0].group(1)
    reporter = cq.from_user.id
    db.add_report(reporter, ad_id, "user_report")
    await cq.answer(
        "⚠️ Report submit ho gaya! Admin 24 ghante mein review karega.\n"
        "*(Report submitted! Admin will review within 24 hours.)*",
        show_alert=True
    )
    try:
        await client.send_message(
            OWNER_ID,
            f"🚨 **User Report Aaya! / User Report Received!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Reporter:** `{reporter}`\n"
            f"🆔 **Ad ID:** `{ad_id}`\n"
            f"📋 **Reason:** User Report\n\n"
            f"**Action lene ke liye:**\n"
            f"`/deletead {ad_id}`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑️ Delete Ad", callback_data=f"admin_del_{ad_id}"),
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
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ DELETED", callback_data="noop")
    ]]))
    await cq.answer("✅ Ad deleted!")


# ══════════════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("stats") & filters.private)
async def cmd_stats(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    stats   = db.get_user_stats()
    reports = len(db.get_pending_reports())
    sleeping = sched.is_sleeping()
    await message.reply(
        "📊 **Bot Statistics / Bot Ki Jankaari**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Total Users:**      `{stats['total']}`\n"
        f"✅ **Active Users:**     `{stats['active']}`\n"
        f"🚫 **Blocked Users:**    `{stats['blocked']}`\n\n"
        f"🚨 **Pending Reports:**  `{reports}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Bot Status:**\n"
        f"🛌 Deep Sleep: `{'⚠️ YES — FloodWait!' if sleeping else '✅ No — Running'}`\n\n"
        "**Quick Actions:**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Broadcast Now", callback_data="admin_broadcast")],
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
        return await message.reply(
            "🗑️ **Ad Delete Karo / Delete an Ad**\n\n"
            "**Usage:** `/deletead <ad_id>`\n\n"
            "Ad ID dashboard se ya approval message se milega.\n"
            "*(Ad ID can be found in dashboard or approval message.)*"
        )

    ad_id = args[0]
    ad    = db.get_ad(ad_id)
    if not ad:
        return await message.reply(
            f"❌ **Ad Nahi Mila! / Ad Not Found!**\n\n"
            f"ID: `{ad_id}`\n\n"
            f"Sahi ID check karo. *(Please verify the correct ID.)*"
        )

    owner_id = ad["owner_id"]
    if ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception as e:
            log.warning(f"Could not delete DB channel message: {e}")

    db.delete_ad(ad_id)
    await message.reply(
        f"✅ **Ad Delete Ho Gaya! / Ad Deleted!**\n\n"
        f"🆔 Ad ID: `{ad_id}`\n"
        f"👤 Owner: `{owner_id}`"
    )
    try:
        await client.send_message(
            owner_id,
            f"ℹ️ **Tumhara Ad Delete Kar Diya Gaya / Your Ad Was Deleted**\n\n"
            f"🆔 Ad ID: `{ad_id}`\n\n"
            f"Admin ne guidelines violation ke karan yeh ad delete kiya.\n"
            f"*(Admin deleted this ad due to guideline violation.)*\n\n"
            f"Questions ke liye admin se contact karo.",
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
    await message.reply("⏳ Mega-broadcast queue ho raha hai... *(Queueing mega-broadcast...)*")
    await sched.mega_broadcast()
    await message.reply(
        "✅ **Mega-Broadcast Queue Ho Gaya! / Mega-Broadcast Queued!**\n\n"
        f"Saare approved ads queue mein push kar diye.\n"
        f"Har {os.getenv('POST_INTERVAL_MINUTES','10')} minute mein ek post jaayega.\n"
        f"*(All approved ads pushed to queue. One post every 10 minutes.)*"
    )


@app.on_callback_query(filters.regex("^noop$"))
async def cb_noop(client: Client, cq: CallbackQuery):
    await cq.answer()


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

async def main():
    await app.start()
    me = await app.get_me()
    log.info(f"✅ Bot started: @{me.username} (ID: {me.id})")
    sched.set_client(app)
    scheduler = sched.build_scheduler()
    scheduler.start()
    log.info("✅ Scheduler started. Bot is running!")
    # Keep bot alive (same pattern as movie bot)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
