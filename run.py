# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  Unauthorized use, resale or redistribution is prohibited.      ║
# ║  GitHub: https://github.com/asbhaibsr/Adds                      ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# © 2024 @asbhaibsr — All Rights Reserved
# _PROTECTED_AUTHOR = "asbhaibsr"  # DO NOT REMOVE
# SIG::SHA256::run::asbhaibsr::3f9b2e7c1a4d6e8b0c5f3a1d8e6b2c4f

import asyncio
import threading
import logging
import os
import sys
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

# ── Author ────────────────────────────────────────────────────────
_AUTHOR = "asbhaibsr"  # © @asbhaibsr — DO NOT REMOVE
# ──────────────────────────────────────────────────────────────────

# ─── Config ───────────────────────────────────────────────────────
PORT          = int(os.getenv("PORT", 8080))
APP_URL       = os.getenv("APP_URL", "https://desirable-eel-asmwasearchbot-5fb40cc5.koyeb.app")
PING_INTERVAL = int(os.getenv("PING_INTERVAL_SECONDS", 270))  # 4.5 min

# Auto-restart config
MAX_RETRIES       = 10          # kitni baar restart kare
RESTART_DELAY     = 5           # seconds — pehle restart ke baad wait
MAX_RESTART_DELAY = 60          # max wait between restarts
# ──────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════
#  SELF-PING — bot jaaga rahe
# ═══════════════════════════════════════════════════════════════════

def self_ping_loop():
    ping_url = f"{APP_URL.rstrip('/')}/health" if APP_URL else f"http://localhost:{PORT}/health"
    time.sleep(20)
    log.info(f"Self-ping started — URL: {ping_url} | Interval: {PING_INTERVAL}s")

    consecutive_failures = 0
    while True:
        try:
            r = requests.get(ping_url, timeout=10)
            if r.status_code == 200:
                log.info("Self-ping OK — bot awake!")
                consecutive_failures = 0
            else:
                log.warning(f"Self-ping got status {r.status_code}")
                consecutive_failures += 1
        except Exception as e:
            log.warning(f"Self-ping failed: {e}")
            consecutive_failures += 1

        if consecutive_failures >= 5:
            log.error(f"Self-ping failed {consecutive_failures} times in a row!")

        time.sleep(PING_INTERVAL)


# ═══════════════════════════════════════════════════════════════════
#  FLASK — health check
# ═══════════════════════════════════════════════════════════════════

def start_flask():
    try:
        from app import app
        log.info(f"Flask starting on port {PORT}")
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        log.error(f"Flask crashed: {e}")


# ═══════════════════════════════════════════════════════════════════
#  BOT — auto-restart on crash
# ═══════════════════════════════════════════════════════════════════

async def start_bot():
    """
    Bot ko start karo with auto-restart.
    Agar crash ho to exponential backoff se restart karo.
    © @asbhaibsr
    """
    import main as bot_main

    attempt      = 0
    restart_wait = RESTART_DELAY

    while attempt < MAX_RETRIES:
        try:
            if attempt > 0:
                log.warning(f"Bot restart attempt {attempt}/{MAX_RETRIES} — waiting {restart_wait}s ...")
                await asyncio.sleep(restart_wait)
                # Exponential backoff — har baar double, max tak
                restart_wait = min(restart_wait * 2, MAX_RESTART_DELAY)
                # Module reload — fresh state
                import importlib
                importlib.reload(bot_main)

            log.info(f"Bot starting (attempt {attempt + 1}) ...")
            await bot_main.main()

            # Agar main() return kare (normal stop) — loop band karo
            log.info("Bot stopped normally.")
            break

        except KeyboardInterrupt:
            log.info("Bot stopped by user (KeyboardInterrupt).")
            break

        except asyncio.CancelledError:
            log.info("Bot task cancelled.")
            break

        except Exception as e:
            err = str(e)
            attempt += 1
            log.error(f"Bot crashed (attempt {attempt}): {err}")

            # Known fatal errors — restart mat karo
            fatal_keywords = [
                "BOT_TOKEN_INVALID",
                "AUTH_KEY_INVALID",
                "API_ID_INVALID",
                "ACCESS_TOKEN_INVALID",
            ]
            if any(kw in err for kw in fatal_keywords):
                log.critical(f"Fatal error — bot restart nahi karega. Fix karo: {err}")
                break

            if attempt >= MAX_RETRIES:
                log.critical(f"Max retries ({MAX_RETRIES}) exceed ho gaye. Bot band ho raha hai.")
                break

            log.warning(f"Next restart in {restart_wait}s ...")

    log.info("Bot runner finished.")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. Flask thread
    flask_thread = threading.Thread(target=start_flask, daemon=True, name="Flask")
    flask_thread.start()
    log.info("Flask thread started.")

    # 2. Self-ping thread
    ping_thread = threading.Thread(target=self_ping_loop, daemon=True, name="SelfPing")
    ping_thread.start()
    log.info("Self-ping thread started.")

    # 3. Bot — auto-restart loop
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    except Exception as e:
        log.error(f"Runner fatal error: {e}")
