import asyncio
import threading
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("runner")


def start_flask():
    """Run Flask on a separate thread for health checks."""
    try:
        from app import app
        port = int(os.getenv("PORT", os.getenv("FLASK_PORT", 8080)))
        log.info(f"Flask starting on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        log.error(f"Flask crashed: {e}")


async def start_bot():
    """Run Pyrogram bot — movie bot style (in_memory, no session file issues)."""
    import main as bot_main
    await bot_main.main()


if __name__ == "__main__":
    # Flask → separate thread (health checks)
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    log.info("Flask thread started.")

    # Bot → main async loop
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
    except Exception as e:
        log.error(f"Bot crashed: {e}")
