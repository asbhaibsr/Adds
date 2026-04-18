<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=180&section=header&text=AdManager%20Bot&fontSize=42&fontColor=fff&animation=twinkling&fontAlignY=32&desc=50%2C000%2B%20Users%20Tak%20Pahuncho%20%E2%80%94%20Bilkul%20FREE!&descAlignY=55&descSize=18" width="100%"/>

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/AdManagerfreebot)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-blue?style=for-the-badge)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT%20%2B%20Attribution-orange?style=for-the-badge)](LICENSE)
[![Author](https://img.shields.io/badge/Author-%40asbhaibsr-red?style=for-the-badge&logo=telegram)](https://t.me/asbhaibsr)

<br/>

![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=500&color=FF6B35&center=true&vCenter=true&multiline=true&width=600&height=100&lines=Telegram+Ad+Broadcasting+Bot;50%2C000+Users+Reach+—+FREE!;Made+with+❤️+by+@asbhaibsr)

</div>

---

<div align="center">

## ✨ Features

</div>

<table>
<tr>
<td width="50%">

### 📢 Ad Broadcasting
- **50,000+** active users tak pahuncho
- **2-Round System**: Aaj + Agle din
- Naye users bhi Round 2 mein cover hote hain
- Auto-queue with flood protection

</td>
<td width="50%">

### 🎯 Smart Earning System
- **Daily Streak**: 7 din = 1 Free Ad
- **Referral System**: 10 refers = 1 Free Ad
- Like / Unlike posts
- Browse posts with navigation

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Admin Controls
- Approve / Reject / Copyright flag
- Force-Subscribe channels
- Manual broadcast trigger
- Auto-delete copyright posts

</td>
<td width="50%">

### 📊 Mini App Dashboard
- Live reach counter
- Streak tracker with animation
- Referral stats & link
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
API_ID=29970536
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
BOT_USERNAME=YourBotUsername
OWNER_ID=your_telegram_id
MONGO_URI=mongodb+srv://...

DATABASE_CHANNEL_ID=-100xxxxxxxxxx
ADMIN_CHANNEL_ID=-100xxxxxxxxxx

APP_URL=https://your-app.koyeb.app
WEBAPP_URL=https://your-app.koyeb.app

POST_INTERVAL_MINUTES=30
ROUND2_AFTER_HOURS=24
COPYRIGHT_DELETE_MINUTES=7
ADMIN_SECRET=your_dashboard_password
MEGA_BROADCAST_TIMES=09:00,21:00
```

### Step 3 — Koyeb Deploy
```bash
# 1. GitHub pe fork karo: https://github.com/asbhaibsr/Adds
# 2. koyeb.com pe account banao
# 3. "Create App" -> GitHub repo connect karo
# 4. Environment variables set karo
# 5. Deploy!
```

Local run:
```bash
pip install -r requirements.txt
python run.py
```

---

## 📁 File Structure

```
Adds/
├── main.py           Bot handlers & commands
├── database.py       MongoDB operations
├── scheduler.py      Background jobs & broadcasting
├── app.py            Flask API & Mini App backend
├── run.py            Entry point
├── requirements.txt  Dependencies
├── koyeb.yaml        Koyeb config
├── templates/
│   ├── index.html    User Dashboard
│   └── admin.html    Admin Panel
└── utils/
    ├── broadcaster.py  Ad sending
    └── forcesub.py     Force subscribe
```

---

## 🎮 Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Bot shuru karo | Everyone |
| `/createad` | Naya ad banao | Everyone |
| `/myposts` | Apni posts dekho | Everyone |
| `/search keyword` | Posts search | Everyone |
| `/done` | Ad finalize | Everyone |
| `/stats` | Bot statistics | Owner |
| `/broadcast` | Manual broadcast | Owner |
| `/addforcesub -100xxx` | Force sub add | Owner |
| `/removefchannel -100xxx` | Force sub remove | Owner |
| `/deletead id` | Ad delete | Owner |
| `/admin` | Admin panel | Owner |

---

## 🔄 2-Round Broadcast System

```
Approval
   |
   v
Round 1 (Aaj — Turant)
   |  Sabhi current users ko jaata hai
   |
24 ghante baad...
   |
   v
Round 2 (Agle Din)
   |  Naaye users bhi cover hote hain
   |
   v
Completed — Archive
```

---

## 💡 Important Notes

**DATABASE_CHANNEL** — Private channel banao, bot ko admin banao, ID daalo. Sab ads yahan store hote hain.

**Redeploy** — Bot startup pe channel check karta hai. `Peer id invalid` aaye toh channel mein bot ko dobara admin banao.

**UptimeRobot** — `https://your-app.koyeb.app/health` add karo monitoring mein. Self-ping bhi built-in hai.

**Admin Dashboard** — Browser se `https://your-app.koyeb.app/admin_panel` kholo, `ADMIN_SECRET` password daalo.

---

## 📜 License

```
MIT License with Attribution Requirement
Copyright (c) 2025 @asbhaibsr

Allowed  : Use, modify, deploy
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
