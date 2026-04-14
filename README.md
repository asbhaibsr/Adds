# 🚀 Viral Streak Bot — Complete Setup Guide

## Project Structure
```
viral_streak_bot/
├── main.py          # Pyrogram bot (all handlers)
├── app.py           # Flask Mini App server
├── database.py      # MongoDB CRUD operations
├── scheduler.py     # Background tasks (queue, broadcast, flood-wait)
├── run.py           # Launch both Flask + Bot together
├── requirements.txt
├── .env.example     # Copy to .env and fill values
├── utils/
│   ├── broadcaster.py   # Send ad to user
│   └── forcesub.py      # Force-sub channel checker
└── templates/
    ├── index.html       # Mini App (User Dashboard)
    └── admin.html       # Mini App (Admin Panel)
```

---

## ⚙️ Setup Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```bash
cp .env.example .env
# Fill in all values in .env
```

Required values:
| Variable | Kahan se milega |
|---|---|
| `API_ID` / `API_HASH` | https://my.telegram.org |
| `BOT_TOKEN` | @BotFather |
| `OWNER_ID` | @userinfobot se apna ID |
| `ADMIN_CHANNEL_ID` | Private channel ka ID (bot ko admin banao) |
| `DATABASE_CHANNEL_ID` | Private DB channel (bot ko admin banao) |
| `MONGO_URI` | MongoDB Atlas → Connect → Python |

### 3. MongoDB Atlas Setup
1. [MongoDB Atlas](https://cloud.mongodb.com) pe free cluster banao
2. Network Access → 0.0.0.0/0 allow karo
3. Connection string `.env` mein daalo

### 4. Telegram Channels Setup
- **Admin Channel**: Private channel banao, bot ko admin banao (post+delete rights)
- **DB Channel**: Alag private channel, bot ko admin banao
- Dono channel IDs ko `.env` mein daalo

### 5. Mini App Setup (BotFather)
```
/newapp → apna bot select karo → Web App URL daalo
URL format: https://yourserver.com/
```

### 6. Run Karo
```bash
python run.py
```

---

## 🤖 Bot Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Bot start, referral tracking |
| `/createad` | Ad creation wizard shuru |
| `/search <query>` | Posts search, inline button results |
| `/done` | Ad finalize karo |

### Owner-Only Commands
| Command | Description |
|---|---|
| `/addforcesub -100xxxxx` | Force-sub channel add (join-request link) |
| `/removefchannel -100xxxxx` | Force-sub channel remove |
| `/stats` | User statistics |
| `/deletead <ad_id>` | Koi bhi ad delete karo |
| `/broadcast` | Manual mega-broadcast trigger |

---

## 📱 Mini App Features

### User Dashboard (index.html)
- **🔥 Streak Tab**: Daily check-in button, 7-day progress
- **👥 Referral Tab**: Unique link, progress bar, share button
- **🔍 Search Tab**: Real-time post search with clickable results
- **📢 My Ads Tab**: Status, reach, delete option

### Admin Panel (admin_panel route)
- User stats (total/active/blocked)
- Delete any ad by ID
- Trigger manual broadcast
- View all force-sub channels

---

## 📡 API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/api/userinfo` | User ka data fetch |
| POST | `/api/checkin` | Daily check-in |
| GET | `/api/my_ads` | User ke ads |
| POST | `/api/delete_ad` | User apna ad delete kare |
| GET | `/api/search?q=query` | Posts search |
| POST | `/api/report_ad` | Post report karo |
| GET | `/api/admin/stats` | Admin: stats |
| POST | `/api/admin/delete_ad` | Admin: koi bhi ad delete |
| POST | `/api/admin/broadcast` | Admin: broadcast trigger |

---

## ⚡ Advanced Features

### Flood Wait Handling
- Telegram FloodWait error aane par → **10-20 minute Deep Sleep**
- Sleep ke baad queue se continue karta hai
- `/stats` mein "Deep Sleep: Yes/No" dikhta hai

### Smart Queue
- 1 post every `POST_INTERVAL_MINUTES` (default: 10 min)
- Mega-Broadcast: 2x daily at configured times
- Queue order: First In, First Out

### Copyright Auto-Delete
- Admin ya user copyright flag kare
- `COPYRIGHT_DELETE_MINUTES` ke baad auto-delete DB channel se
- User ko notification milta hai

### Force-Sub System
- Private channels: Join Request link generate hota hai
- Bot admin approves request (manually ya auto)
- User "I've Joined" dabaane par re-check hota hai

### Search System
- `/search kalki movie` → 5 results as inline buttons
- Har button = direct link to DB channel post
- `@bot kalki` → inline query support

---

## 🛡️ Safety Features

1. **User Report**: Koi bhi user kisi bhi post ko report kar sakta hai
2. **Copyright Flag**: Admin approval screen pe "Copyright" button
3. **Auto-Delete**: Flagged posts auto-delete after N minutes
4. **Blocked User Cleanup**: Weekly cleanup (Sunday 02:00 UTC)
5. **Deep Sleep**: Bot account ko protect karta hai FloodWait se

---

## 🚀 Deployment (Free Options)

### Railway.app (Recommended)
```bash
# railway.toml
[build]
builder = "NIXPACKS"
[deploy]
startCommand = "python run.py"
```

### Render.com
- Web Service banao, `python run.py` start command

### VPS (DigitalOcean/Hetzner)
```bash
pip install supervisor
# supervisord config se both processes manage karo
```

---

## 📞 Support

Koi issue aaye to:
1. `.env` values double-check karo
2. Bot channels mein admin hai ya nahi verify karo
3. MongoDB Atlas IP whitelist check karo
