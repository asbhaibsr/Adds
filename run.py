# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import asyncio
import threading
import logging
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("runner")

# ─── Config ───────────────────────────────────────────────────────
PORT         = int(os.getenv("PORT", 8080))
APP_URL      = os.getenv("APP_URL", "https://desirable-eel-asmwasearchbot-5fb40cc5.koyeb.app")        # .env mein apni Koyeb URL daalo
PING_INTERVAL = int(os.getenv("PING_INTERVAL_SECONDS", 270))  # 4.5 min


# ═══════════════════════════════════════════════════════════════════
#  SELF-PING — bot ko jaag ta rakhta hai
# ═══════════════════════════════════════════════════════════════════

def self_ping_loop():
    """
    Har PING_INTERVAL seconds mein apni hi /health URL ping karo.
    Isse Koyeb/UptimeRobot dono milke bot ko kabhi sleep nahi karne denge.
    APP_URL .env mein set karo — jaise: https://your-app.koyeb.app
    """
    # Agar APP_URL nahi diya toh localhost ping karo
    ping_url = f"{APP_URL.rstrip('/')}/health" if APP_URL else f"http://localhost:{PORT}/health"

    # Bot ke start hone tak thoda wait karo
    time.sleep(20)
    log.info(f"Self-ping started — URL: {ping_url} | Interval: {PING_INTERVAL}s")

    consecutive_failures = 0
    while True:
        try:
            r = requests.get(ping_url, timeout=10)
            if r.status_code == 200:
                log.info(f"Self-ping OK — bot awake!")
                consecutive_failures = 0
            else:
                log.warning(f"Self-ping got status {r.status_code}")
                consecutive_failures += 1
        except Exception as e:
            log.warning(f"Self-ping failed: {e}")
            consecutive_failures += 1

        # 5 baar lagaataar fail hone par log karo
        if consecutive_failures >= 5:
            log.error(f"Self-ping failed {consecutive_failures} times in a row!")

        time.sleep(PING_INTERVAL)


# ═══════════════════════════════════════════════════════════════════
#  FLASK — health check + mini app
# ═══════════════════════════════════════════════════════════════════

def start_flask():
    try:
        from app import app
        log.info(f"Flask starting on port {PORT}")
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        log.error(f"Flask crashed: {e}")


# ═══════════════════════════════════════════════════════════════════
#  BOT
# ═══════════════════════════════════════════════════════════════════

async def start_bot():
    import main as bot_main
    await bot_main.main()


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. Flask thread — health checks + mini app
    flask_thread = threading.Thread(target=start_flask, daemon=True, name="Flask")
    flask_thread.start()
    log.info("Flask thread started.")

    # 2. Self-ping thread — bot jaaga rahe
    ping_thread = threading.Thread(target=self_ping_loop, daemon=True, name="SelfPing")
    ping_thread.start()
    log.info("Self-ping thread started.")

    # 3. Bot — main loop
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
    except Exception as e:
        log.error(f"Bot crashed: {e}")
