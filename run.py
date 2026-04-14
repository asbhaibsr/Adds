import asyncio
import threading
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def start_flask():
    from app import app
    port = int(os.getenv("FLASK_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


async def start_bot():
    import main as bot_main
    await bot_main.main()


if __name__ == "__main__":
    # Flask in separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Bot in main asyncio loop
    asyncio.run(start_bot())
