import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
)
from pyrogram.errors import FloodWait

import scheduler as sched
import database as db
from utils.forcesub import check_subscription, build_join_buttons

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ─── Bot Client ────────────────────────────────────────────────────
app = Client(
    "viral_bot",
    api_id   = os.getenv("API_ID"),
    api_hash = os.getenv("API_HASH"),
    bot_token= os.getenv("BOT_TOKEN"),
)

OWNER_ID       = int(os.getenv("OWNER_ID", 0))
ADMIN_CHANNEL  = int(os.getenv("ADMIN_CHANNEL_ID", 0))
DB_CHANNEL     = int(os.getenv("DATABASE_CHANNEL_ID", 0))
WEBAPP_URL     = os.getenv("WEBAPP_URL", "https://yourserver.com")   # Mini App URL


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


# ─── Helpers ───────────────────────────────────────────────────────
def mini_app_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Open Dashboard", web_app={"url": WEBAPP_URL})
    ]])


async def force_sub_gate(client: Client, user_id: int) -> bool:
    """Returns True if user passes all force-sub checks."""
    passed, missing = await check_subscription(client, user_id)
    if not passed:
        kb = build_join_buttons(missing)
        await client.send_message(
            user_id,
            "⛔ **Pehle in channels ko join karo!**\n\n"
            "Join karne ke baad '🔄 I've Joined' button dabao.",
            reply_markup=kb
        )
    return passed


# ═══════════════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════════════

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

    existing = db.get_user(user.id)
    db.get_or_create_user(user.id, user.username or "", user.full_name or "")

    if not existing and referred_by and referred_by != user.id:
        unlocked = db.add_referral(referred_by, user.id)
        if unlocked:
            await client.send_message(
                referred_by,
                "🎉 **Congratulations!** 10 referrals complete!\n"
                "✅ 1 Free Ad unlocked! Dashboard check karo."
            )

    # Force-sub check
    if not await force_sub_gate(client, user.id):
        return

    # Lalach message 😄
    await message.reply(
        f"**Namaste {user.first_name}! 👋**\n\n"
        "🚀 **10,000+ Followers/Clicks BILKUL FREE!**\n\n"
        "Yahan pe sirf ek kaam karo:\n"
        "✅ Roz check-in karo → **Streak badhao**\n"
        "✅ 10 dost refer karo → **1 Free Ad**\n"
        "✅ Apna ad banao → **Hum promote karte hain**\n\n"
        "🔥 Abhi dashboard kholo aur apni **7-day streak** shuru karo!",
        reply_markup=mini_app_button()
    )


# ═══════════════════════════════════════════════════════════════════
#  Force-Sub Check Callback
# ═══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("^check_sub$"))
async def cb_check_sub(client: Client, cq: CallbackQuery):
    passed, missing = await check_subscription(client, cq.from_user.id)
    if passed:
        await cq.message.delete()
        await client.send_message(
            cq.from_user.id,
            "✅ Sab channels join ho gaye! Ab bot use kar sakte ho.",
            reply_markup=mini_app_button()
        )
    else:
        await cq.answer("❌ Abhi bhi kuch channels missing hain!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: /addforcesub <channel_id>
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addforcesub") & filters.private)
async def cmd_add_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Sirf owner use kar sakta hai!")

    args = message.command[1:]
    if not args:
        return await message.reply(
            "**Usage:** `/addforcesub -100xxxxxxxxxx`\n\n"
            "Bot ko us channel ka admin banana mat bhoolna!"
        )

    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply("❌ Invalid channel ID. Format: `-100xxxxxxxxxx`")

    # Try to get channel info
    try:
        chat = await client.get_chat(ch_id)
        title = chat.title or str(ch_id)

        # Create invite link (join request type for private channels)
        try:
            link_obj = await client.create_chat_invite_link(
                ch_id,
                creates_join_request=True,    # Admin approval required
                name="ForceSub Link",
            )
            invite_link = link_obj.invite_link
        except Exception:
            invite_link = chat.invite_link or ""

    except Exception as e:
        return await message.reply(f"❌ Channel info nahi mili: {e}\nBot ko admin banao.")

    added = db.add_forcesub_channel(ch_id, invite_link, title)
    if added:
        await message.reply(
            f"✅ **Force-Sub Channel Added!**\n\n"
            f"📢 Channel: `{title}`\n"
            f"🔗 Join Link (Request): `{invite_link}`\n"
            f"🆔 ID: `{ch_id}`\n\n"
            f"Ab naye users ko pehle is channel ko join request bhejna hoga."
        )
    else:
        await message.reply("⚠️ Yeh channel already added hai!")


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: /removefchannel <channel_id>
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("removefchannel") & filters.private)
async def cmd_remove_forcesub(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply("❌ Sirf owner use kar sakta hai!")

    args = message.command[1:]
    if not args:
        channels = db.get_all_forcesub_channels()
        if not channels:
            return await message.reply("📭 Koi force-sub channel set nahi hai.")
        text = "**Active Force-Sub Channels:**\n\n"
        for ch in channels:
            text += f"• `{ch['channel_id']}` — {ch.get('title','Unknown')}\n"
        text += "\n**Remove karne ke liye:** `/removefchannel -100xxxxxxxxxx`"
        return await message.reply(text)

    try:
        ch_id = int(args[0])
    except ValueError:
        return await message.reply("❌ Invalid channel ID.")

    removed = db.remove_forcesub_channel(ch_id)
    if removed:
        await message.reply(f"✅ Channel `{ch_id}` force-sub list se hata diya gaya!")
    else:
        await message.reply("❌ Yeh channel list mein nahi tha.")


# ═══════════════════════════════════════════════════════════════════
#  /search — Inline button results
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("search") & filters.private)
async def cmd_search(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply(
            "🔍 **Search karo:**\n"
            "Usage: `/search <query>`\n\n"
            "Example: `/search kalki movie` ya `/search tech gadgets`"
        )

    query = " ".join(args)
    results = db.search_ads(query, limit=5)

    if not results:
        return await message.reply(
            f"😕 '**{query}**' ke liye koi post nahi mila.\n"
            "Kisi doosre keyword se try karo!"
        )

    # Build inline buttons — each button links to the DB channel message
    buttons = []
    for ad in results:
        caption_preview = (ad.get("caption", "") or "")[:40].strip()
        tags = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        label = f"{caption_preview} {tags}".strip()[:60] or "View Post"

        # Direct link to DB channel message
        msg_id = ad.get("db_channel_msg_id")
        ch_id  = str(DB_CHANNEL).replace("-100", "")
        url    = f"https://t.me/c/{ch_id}/{msg_id}" if msg_id else "https://t.me"

        buttons.append([InlineKeyboardButton(f"📌 {label}", url=url)])

    buttons.append([InlineKeyboardButton("🔍 Search Again", switch_inline_query_current_chat=query)])

    await message.reply(
        f"🔍 **'{query}'** ke liye {len(results)} result(s) mile:\n\n"
        "Kisi bhi button pe click karke post dekho 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ═══════════════════════════════════════════════════════════════════
#  INLINE SEARCH (@bot query)
# ═══════════════════════════════════════════════════════════════════

@app.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    q = query.query.strip()
    if not q:
        return

    results_db = db.search_ads(q, limit=5)
    inline_results = []
    ch_id = str(DB_CHANNEL).replace("-100", "")

    for ad in results_db:
        caption  = (ad.get("caption", "") or "")[:200]
        tags     = " ".join([f"#{h}" for h in ad.get("hashtags", [])])
        msg_id   = ad.get("db_channel_msg_id")
        post_url = f"https://t.me/c/{ch_id}/{msg_id}" if msg_id else "https://t.me"

        inline_results.append(
            InlineQueryResultArticle(
                title     = caption[:50] or q,
                description = tags,
                input_message_content=InputTextMessageContent(
                    f"**{caption[:100]}**\n\n{tags}\n\n[📌 Post dekho]({post_url})"
                ),
            )
        )

    await query.answer(inline_results, cache_time=30)


# ═══════════════════════════════════════════════════════════════════
#  AD CREATION FLOW  (triggered from Mini App via deep link)
#  Deep link: t.me/bot?start=create_ad
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("createad") & filters.private)
async def cmd_create_ad(client: Client, message: Message):
    if not await force_sub_gate(client, message.from_user.id):
        return

    db.save_ad_session(message.from_user.id, {"step": "media"})
    await message.reply(
        "🎨 **New Ad Banana Shuru Karo!**\n\n"
        "**Step 1/4:** Apni Photo ya Video bhejo 📸\n\n"
        "_(Sirf media bhejo, koi text mat likho abhi)_"
    )


@app.on_message(
    filters.private &
    (filters.photo | filters.video | filters.animation | filters.text) &
    ~filters.command(["start","search","addforcesub","removefchannel","createad","stats","broadcast","deletead"])
)
async def handle_ad_creation(client: Client, message: Message):
    """Multi-step ad creation state machine."""
    user_id = message.from_user.id
    session = db.get_ad_session(user_id)
    if not session:
        return

    step = session.get("step", "")

    # ── Step 1: Collect Media ──────────────────────────────────────
    if step == "media":
        if message.photo:
            media_type = "photo"
            file_id    = message.photo.file_id
        elif message.video:
            media_type = "video"
            file_id    = message.video.file_id
        elif message.animation:
            media_type = "animation"
            file_id    = message.animation.file_id
        else:
            return await message.reply("❌ Pehle photo ya video bhejo!")

        db.save_ad_session(user_id, {
            "step": "caption",
            "media_type": media_type,
            "file_id": file_id,
        })
        await message.reply(
            "✅ Media mil gaya!\n\n"
            "**Step 2/4:** Ab apna caption likho ✏️\n"
            "_(Max 1024 characters)_"
        )

    # ── Step 2: Caption ────────────────────────────────────────────
    elif step == "caption":
        if not message.text:
            return await message.reply("❌ Sirf text mein caption likho.")
        db.save_ad_session(user_id, {"step": "hashtags", "caption": message.text[:1024]})
        await message.reply(
            "✅ Caption save!\n\n"
            "**Step 3/4:** 2 Hashtags likho 🏷️\n"
            "Format: `#topic1 #topic2`\n"
            "Example: `#techgadgets #deals`"
        )

    # ── Step 3: Hashtags ────────────────────────────────────────────
    elif step == "hashtags":
        if not message.text:
            return await message.reply("❌ Hashtags text mein likho.")
        tags = [t.lstrip("#").lower() for t in message.text.split() if t.startswith("#")]
        if len(tags) < 1:
            return await message.reply("❌ Kam se kam 1 hashtag chahiye. (#example)")
        tags = tags[:5]
        db.save_ad_session(user_id, {"step": "buttons", "hashtags": tags})
        await message.reply(
            "✅ Hashtags: " + " ".join([f"#{t}" for t in tags]) + "\n\n"
            "**Step 4/4:** Inline buttons add karo (optional) 🔗\n\n"
            "Format: `Button Title | https://link.com`\n"
            "Ek line = ek button. Max 3 buttons.\n\n"
            "_(Skip karne ke liye `/done` likho)_",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭️ Skip Buttons", callback_data="skip_buttons")
            ]])
        )

    # ── Step 4: Buttons ────────────────────────────────────────────
    elif step == "buttons":
        if message.text:
            rows = []
            for line in message.text.strip().splitlines()[:3]:
                if "|" in line:
                    parts = line.split("|", 1)
                    btn_text = parts[0].strip()
                    btn_url  = parts[1].strip()
                    if btn_text and btn_url.startswith("http"):
                        rows.append([{"text": btn_text, "url": btn_url}])
            db.save_ad_session(user_id, {"step": "position", "buttons": rows})
            await _show_position_editor(client, user_id, rows)

    # ── /done shortcut ──────────────────────────────────────────────
    elif step == "position" and message.text and message.text.strip() == "/done":
        await _finalize_ad(client, message.from_user, session)


@app.on_message(filters.command("done") & filters.private)
async def cmd_done(client: Client, message: Message):
    session = db.get_ad_session(message.from_user.id)
    if session and session.get("step") in ("buttons", "position"):
        await _finalize_ad(client, message.from_user, session)
    else:
        await message.reply("❌ Koi active ad creation session nahi hai.")


@app.on_callback_query(filters.regex("^skip_buttons$"))
async def cb_skip_buttons(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expired.", show_alert=True)
    db.save_ad_session(cq.from_user.id, {"step": "position", "buttons": []})
    await cq.message.edit_text(
        "✅ Buttons skip kiya.\n\n"
        "Ab **/done** type karo ya 'Submit' dabao 👇",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Submit Ad", callback_data="submit_ad")
        ]])
    )


@app.on_callback_query(filters.regex("^submit_ad$"))
async def cb_submit_ad(client: Client, cq: CallbackQuery):
    session = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expired.", show_alert=True)
    await _finalize_ad(client, cq.from_user, session)
    await cq.message.delete()


async def _show_position_editor(client: Client, user_id: int, buttons: list):
    """Show button arrangement with Up/Down/Left/Right controls."""
    await client.send_message(
        user_id,
        f"🔧 **Button Positioning**\n\n"
        f"Current layout:\n{_render_button_layout(buttons)}\n\n"
        f"Controls → kabhi bhi **/done** type karo submit karne ke liye.",
        reply_markup=_position_keyboard(buttons, 0)
    )


def _render_button_layout(buttons: list) -> str:
    text = ""
    for i, row in enumerate(buttons):
        text += f"Row {i+1}: " + " | ".join([b["text"] for b in row]) + "\n"
    return text or "_(No buttons)_"


def _position_keyboard(buttons: list, selected: int) -> InlineKeyboardMarkup:
    controls = [
        [InlineKeyboardButton("⬆️ Move Up",    callback_data=f"btn_up_{selected}")],
        [
            InlineKeyboardButton("⬅️ Left",    callback_data=f"btn_left_{selected}"),
            InlineKeyboardButton("➡️ Right",   callback_data=f"btn_right_{selected}"),
        ],
        [InlineKeyboardButton("⬇️ Move Down",  callback_data=f"btn_down_{selected}")],
        [InlineKeyboardButton("✅ Done / Submit", callback_data="submit_ad")],
    ]
    return InlineKeyboardMarkup(controls)


@app.on_callback_query(filters.regex(r"^btn_(up|down|left|right)_(\d+)$"))
async def cb_position(client: Client, cq: CallbackQuery):
    direction = cq.matches[0].group(1)
    idx       = int(cq.matches[0].group(2))
    session   = db.get_ad_session(cq.from_user.id)
    if not session:
        return await cq.answer("Session expired.", show_alert=True)

    buttons = session.get("buttons", [])

    if direction == "up" and idx > 0:
        buttons[idx], buttons[idx-1] = buttons[idx-1], buttons[idx]
        idx -= 1
    elif direction == "down" and idx < len(buttons) - 1:
        buttons[idx], buttons[idx+1] = buttons[idx+1], buttons[idx]
        idx += 1
    elif direction == "left" and idx < len(buttons):
        row = buttons[idx]
        if len(row) > 1:
            row.insert(0, row.pop())            # rotate right button to left
    elif direction == "right" and idx < len(buttons):
        row = buttons[idx]
        if len(row) > 1:
            row.append(row.pop(0))              # rotate left button to right

    db.save_ad_session(cq.from_user.id, {"buttons": buttons})
    await cq.message.edit_text(
        f"🔧 **Button Layout Updated:**\n\n{_render_button_layout(buttons)}\n\n"
        "✅ Done? 'Submit' dabao!",
        reply_markup=_position_keyboard(buttons, idx)
    )
    await cq.answer()


async def _finalize_ad(client, user, session: dict):
    """Store ad in DB channel, create ad record, send to admin for approval."""
    user_id = user.id

    # 1. Store in DB channel (with hashtag for searchability)
    tags_text = " ".join([f"#{t}" for t in session.get("hashtags", [])])
    full_caption = (session.get("caption", "") + "\n\n" + tags_text).strip()
    buttons_kb = None

    from utils.broadcaster import _build_keyboard
    kb_data = session.get("buttons", [])
    if kb_data:
        buttons_kb = _build_keyboard(kb_data)

    try:
        mtype = session.get("media_type", "text")
        fid   = session.get("file_id")

        if mtype == "photo" and fid:
            db_msg = await client.send_photo(DB_CHANNEL, fid, caption=full_caption, reply_markup=buttons_kb)
        elif mtype == "video" and fid:
            db_msg = await client.send_video(DB_CHANNEL, fid, caption=full_caption, reply_markup=buttons_kb)
        else:
            db_msg = await client.send_message(DB_CHANNEL, full_caption, reply_markup=buttons_kb)
    except Exception as e:
        await client.send_message(user_id, f"❌ DB channel mein store nahi hua: {e}")
        return

    # 2. Create ad in DB
    ad_id = db.create_ad(user_id, {
        **session,
        "db_channel_msg_id": db_msg.id,
    })

    # 3. Send to admin channel for approval
    approve_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{ad_id}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{ad_id}"),
        InlineKeyboardButton("🚫 Copyright", callback_data=f"copyright_{ad_id}"),
    ]])

    await client.send_message(
        ADMIN_CHANNEL,
        f"**📢 New Ad Approval Required**\n\n"
        f"👤 User: [{user.full_name}](tg://user?id={user_id}) (`{user_id}`)\n"
        f"🆔 Ad ID: `{ad_id}`\n"
        f"📝 Caption: {session.get('caption','')[:200]}\n"
        f"🏷️ Tags: {tags_text}\n"
        f"📊 Buttons: {len(kb_data)} rows",
        reply_markup=approve_kb
    )

    db.clear_ad_session(user_id)
    await client.send_message(
        user_id,
        "🎉 **Ad submit ho gaya!**\n\n"
        "Admin approve karega, uske baad broadcasting shuru ho jayegi.\n"
        "Dashboard mein status check kar sakte ho 👇",
        reply_markup=mini_app_button()
    )


# ═══════════════════════════════════════════════════════════════════
#  ADMIN APPROVAL CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^approve_(.+)$"))
async def cb_approve(client: Client, cq: CallbackQuery):
    if cq.from_user.id != OWNER_ID:
        return await cq.answer("❌ Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.approve_ad(ad_id)
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ APPROVED", callback_data="noop")
    ]]))
    await cq.answer("✅ Ad approved & queued!")

    # Notify user
    ad = db.get_ad(ad_id)
    if ad:
        await client.send_message(
            ad["owner_id"],
            "🎊 **Tumhara ad APPROVE ho gaya!**\n"
            "Broadcasting queue mein add kar diya gaya hai. 🚀"
        )


@app.on_callback_query(filters.regex(r"^reject_(.+)$"))
async def cb_reject(client: Client, cq: CallbackQuery):
    if cq.from_user.id != OWNER_ID:
        return await cq.answer("❌ Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.reject_ad(ad_id)
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ REJECTED", callback_data="noop")
    ]]))
    await cq.answer("Ad rejected.")

    ad = db.get_ad(ad_id)
    if ad:
        await client.send_message(
            ad["owner_id"],
            "😔 Tumhara ad reject ho gaya.\n"
            "Guidelines follow karo aur dobara try karo."
        )


@app.on_callback_query(filters.regex(r"^copyright_(.+)$"))
async def cb_copyright(client: Client, cq: CallbackQuery):
    if cq.from_user.id != OWNER_ID:
        return await cq.answer("❌ Sirf owner!", show_alert=True)
    ad_id = cq.matches[0].group(1)
    db.flag_copyright(ad_id)
    db.reject_ad(ad_id)
    await cq.message.edit_reply_markup(InlineKeyboardMarkup([[
        InlineKeyboardButton("🚫 COPYRIGHT FLAGGED", callback_data="noop")
    ]]))
    await cq.answer(f"Flagged! Auto-delete in {os.getenv('COPYRIGHT_DELETE_MINUTES',7)} mins.")

    ad = db.get_ad(ad_id)
    if ad:
        await client.send_message(
            ad["owner_id"],
            "⚠️ **Copyright Issue!**\n\n"
            "Tumhare ad mein copyright content detect hua hai.\n"
            "Yeh post automatically delete ho jayega."
        )


# ═══════════════════════════════════════════════════════════════════
#  USER: Report a post
# ═══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^report_(.+)$"))
async def cb_report(client: Client, cq: CallbackQuery):
    ad_id     = cq.matches[0].group(1)
    reporter  = cq.from_user.id
    db.add_report(reporter, ad_id, "user_report")
    await cq.answer("⚠️ Report submit ho gaya! Admin review karega.", show_alert=True)
    await client.send_message(
        OWNER_ID,
        f"🚨 **User Report**\n\n"
        f"Reporter: `{reporter}`\n"
        f"Ad ID: `{ad_id}`\n"
        f"Action: Admin panel se delete kar sakte ho."
    )


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: /stats, /broadcast, /deletead
# ═══════════════════════════════════════════════════════════════════

@app.on_message(filters.command("stats") & filters.private)
async def cmd_stats(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    stats = db.get_user_stats()
    await message.reply(
        "📊 **Bot Statistics**\n\n"
        f"👥 Total Users:   `{stats['total']}`\n"
        f"✅ Active:        `{stats['active']}`\n"
        f"🚫 Blocked:       `{stats['blocked']}`\n\n"
        f"🛌 Deep Sleep:    `{'Yes' if sched.is_sleeping() else 'No'}`"
    )


@app.on_message(filters.command("deletead") & filters.private)
async def cmd_delete_ad(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    args = message.command[1:]
    if not args:
        return await message.reply("Usage: `/deletead <ad_id>`")

    ad_id = args[0]
    ad    = db.get_ad(ad_id)
    if not ad:
        return await message.reply("❌ Ad nahi mila.")

    # Delete from DB channel
    if ad.get("db_channel_msg_id"):
        try:
            await client.delete_messages(DB_CHANNEL, ad["db_channel_msg_id"])
        except Exception:
            pass

    db.delete_ad(ad_id)
    await message.reply(f"✅ Ad `{ad_id}` delete ho gaya!")

    # Notify owner of ad
    try:
        await client.send_message(ad["owner_id"], f"ℹ️ Tumhara ad (ID: `{ad_id}`) admin ne delete kar diya.")
    except Exception:
        pass


@app.on_message(filters.command("broadcast") & filters.private)
async def cmd_broadcast(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    # Re-use mega_broadcast
    await sched.mega_broadcast()
    await message.reply("✅ Mega-broadcast queue mein push kar diya!")


@app.on_callback_query(filters.regex("^noop$"))
async def cb_noop(client: Client, cq: CallbackQuery):
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    async with app:
        sched.set_client(app)
        scheduler = sched.build_scheduler()
        scheduler.start()
        log.info("✅ Viral Streak Bot is running!")
        await asyncio.Event().wait()   # Run forever


if __name__ == "__main__":
    asyncio.run(main())
