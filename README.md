<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=180&section=header&text=AdManager%20Bot&fontSize=42&fontColor=fff&animation=twinkling&fontAlignY=32&desc=50%2C000%2B%20Users%20Tak%20Pahuncho%20%E2%80%94%20Bilkul%20FREE!&descAlignY=55&descSize=18" width="100%"/>

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/AdManagerfreebot)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-blue?style=for-the-badge)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT%20%2B%20Attribution-orange?style=for-the-badge)](LICENSE)
[![Author](https://img.shields.io/badge/Author-%40asbhaibsr-red?style=for-the-badge&logo=telegram)](https://t.me/asbhaibsr)

![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=500&color=FF6B35&center=true&vCenter=true&multiline=true&width=600&height=100&lines=Telegram+Ad+Broadcasting+Bot;50%2C000+Users+Reach+—+FREE!;Made+with+❤️+by+@asbhaibsr)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📢 Ad Broadcasting
- **50,000+** active users tak pahuncho
- **2-Round System**: Aaj + Agle din
- Naye users bhi Round 2 mein cover hote hain
- Auto-queue with flood protection
- Har ad ke saath **poster ka naam, streak aur strikes** dikhta hai

</td>
<td width="50%">

### 🎯 Smart Earning System
- **Daily Streak**: 7 din = 1 Free Ad
- **Weekly Streak**: 10 weekly streaks complete = 2 Extra Free Ads
- **Referral System**: 10 refers = 1 Free Ad
- **Redeem Codes**: Owner special codes generate kare
- Like / Unlike posts

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Admin Controls
- Approve / Reject / Copyright flag
- **🔞 18+ Approve** — blurred spoiler ke saath jaata hai, 30 min baad auto-delete
- **Copyright** — 2 ghante baad sabhi users ke paas se auto-delete
- **Strike System** — Copyright/18+ par user ko strike milti hai
- Force-Subscribe (normal + request channels)
- Redeem code generate karo
- Manual broadcast trigger
- **Blocked users ka data ek click mein clear karo**

</td>
<td width="50%">

### 📊 Mini App Dashboard
- Animated live reach counter
- Streak tracker with animation
- Latest posts & search with buttons
- My Ads management

</td>
</tr>
</table>

---


## 🚀 Deploy Karo

### Step 1 — Prerequisites
```
Python 3.11+
MongoDB Atlas (free tier)
Telegram Bot Token (@BotFather se)
Telegram API ID & Hash (my.telegram.org se)
Koyeb account (free tier)
```

### Step 2 — Environment Variables

`.env` file:
```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
BOT_USERNAME=YourBotUsername
OWNER_ID=your_telegram_id
MONGO_URI=mongodb+srv://...

DATABASE_CHANNEL_ID=-100xxxxxxxxxx
ADMIN_CHANNEL_ID=-100xxxxxxxxxx

APP_URL=https://your-app.koyeb.app
WEBAPP_URL=https://your-app.koyeb.app

POST_INTERVAL_MINUTES=10
ROUND2_AFTER_HOURS=24
COPYRIGHT_DELETE_MINUTES=120
ADULT_DELETE_MINUTES=30
MEGA_BROADCAST_TIMES=09:00,21:00
ADMIN_PASSWORD=apna_strong_password
LOG_CHANNEL_ID=-100xxxxxxxxxx
```

> ⚠️ `COPYRIGHT_DELETE_MINUTES=120` = 2 ghante baad delete
> ⚠️ `ADULT_DELETE_MINUTES=30` = 30 minute baad delete

### Step 3 — Koyeb Deploy
```bash
# 1. GitHub pe fork karo: https://github.com/asbhaibsr/Adds
# 2. koyeb.com pe account banao
# 3. "Create App" → GitHub repo connect karo
# 4. Environment variables set karo
# 5. Deploy!
```

Local run:
```bash
pip install -r requirements.txt
python run.py
```

---

## 🔐 Admin Dashboard

Browser se `https://your-app.koyeb.app/admin_panel` kholo.

Password = `.env` mein jo **`ADMIN_PASSWORD`** set kiya hai.

---

## 📁 File Structure

```
Adds/
├── main.py              Bot handlers & commands
├── database.py          MongoDB operations
├── scheduler.py         Background jobs, broadcasting, auto-delete
├── app.py               Flask API & Mini App backend
├── run.py               Entry point
├── requirements.txt     Dependencies
├── koyeb.yaml           Koyeb config
├── .env                 Environment variables
├── templates/
│   ├── index.html       User Dashboard (Mini App)
│   └── admin.html       Admin Panel
└── utils/
    ├── broadcaster.py   Ad sending logic (blur, user info)
    └── forcesub.py      Force subscribe
```

---

## 🎮 Bot Commands — Puri List

### 👥 User Commands
```
/start              — Bot shuru karo / main menu
/createad           — Naya ad banao
/myposts            — Apni saari posts dekho
/search <keyword>   — Posts search karo
/done               — Ad session finalize karo
```

**Redeem Code:**
```
#redeem ADMS-XXXXXX
```
Bot PM mein likho → 1 Free Ad turant account mein!

> BotFather ke liye:
```
start - Bot shuru karo
createad - Naya ad banao
myposts - Apni posts dekho
search - Posts search karo
done - Ad session finalize karo
```

---

### 🛡️ Owner / Admin Commands

```
/admin              — Admin panel + redeem button
/stats              — Bot statistics + blocked users clear button
/broadcast          — Manual mega-broadcast trigger
/send_broadcast     — Custom message sabko bhejo
/cancel_broadcast   — Broadcast cancel karo
/addforcesub -100xx — Force-sub channel add karo
/removefchannel     — Force-sub channel hatao
/deletead <ad_id>   — Koi bhi ad delete karo
/gencode            — 1-use redeem code generate karo
/gencode 3          — 3-use redeem code generate karo
```

> BotFather ke liye:
```
admin - Admin panel kholo
stats - Bot statistics dekho
broadcast - Manual broadcast trigger
send_broadcast - Custom message bhejo
cancel_broadcast - Broadcast cancel karo
addforcesub - Force-sub channel add karo
removefchannel - Force-sub channel hatao
deletead - Ad delete karo
gencode - Redeem code generate karo
```

---

## 🎟️ Redeem Code System

**Owner code kaise banaye:**
- `/admin` → **🎟 Redeem Code Generate Karo** button
- Ya `/gencode` — 1 use wala
- Ya `/gencode 5` — 5 users use kar sakein

**Code format:** `ADMS-ABC123`

**User kaise use kare:**
```
#redeem ADMS-ABC123
```
→ 1 Free Ad turant milega → `/createad` se use karo

**Rules:**
- Ek user ek code sirf **1 baar** use kar sakta hai
- Limit khatam → auto deactivate
- Redeem ke baad **pehli ad bhi free** hogi ✅

---

## 🔢 Strike System

| Action | Strike |
|--------|--------|
| Copyright content | ⚠️ +1 Strike |
| 18+ content | ⚠️ +1 Strike |

Strikes profile mein dikhti hain aur har broadcast mein bhi.

---

## 🕐 Auto-Delete Timings

| Content Type | Delete After |
|-------------|-------------|
| 🚫 Copyright | 2 ghante (120 min) |
| 🔞 18+ Content | 30 minute |

> Dono cases mein **sabhi users ke paas se** message delete hota hai, sirf DB se nahi.

---

## 🔄 2-Round Broadcast System

```
Ad Approved
    │
    ▼
Round 1 — Turant
    │  Sabhi current users ko jaata hai
    │
24 ghante baad...
    │
    ▼
Round 2 — Agle Din
    │  Naaye users bhi cover hote hain
    │
    ▼
Completed — Archive
```

---

## 📅 Weekly Streak Reward

```
Roz check-in karo
    │
    ▼
7 din streak → 1 Free Ad + 1 Weekly Streak
    │
10 Weekly Streaks complete?
    │
    ▼
🏆 2 Extra Free Ads Bonus!
```

---

## 📌 Force Subscribe

**Normal public channel:**
```
/addforcesub -100xxxxxxxxxx
```

**Request/Private channel:**
```
/addforcesub -100xxxxxxxxxx
```
Bot automatically detect karta hai. Dono ke liye alag check hota hai.

---

## 💡 Important Notes

**DATABASE_CHANNEL** — Private channel banao, bot ko admin banao, ID daalo.

**ADMIN_PASSWORD** — `.env` mein strong password rakho. Admin dashboard ka yahi password hai.

**Blocked Users** — `/stats` → "Blocked Users Clear Karo" button se time-to-time cleanup karo taaki broadcasts fast rahein.

**UptimeRobot** — `https://your-app.koyeb.app/health` add karo free monitoring ke liye.

**Force Sub Request Channel** — Bot ko **"Manage Members"** permission do.

---

## 📜 License

```
MIT License with Attribution Requirement
Copyright (c) 2025 @asbhaibsr

Allowed     : Use, modify, deploy
Not Allowed : Remove @asbhaibsr credit, resell without permission
```

Full details: [LICENSE](LICENSE)

---

<div align="center">

**Contact: [@asbhaibsr](https://t.me/asbhaibsr) on Telegram**

**GitHub: [github.com/asbhaibsr/Adds](https://github.com/asbhaibsr/Adds)**

⭐ **Agar useful laga toh star dena!**

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer&animation=twinkling" width="100%"/>

<sub>Made with love by <a href="https://t.me/asbhaibsr">@asbhaibsr</a></sub>

</div>
