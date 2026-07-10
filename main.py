import os
import base64
import asyncio
import logging
from database.database import init_db
from bot.bot import build_app
from scheduler.monitor import monitor_loop

# Configure logging globally
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress verbose getUpdates and external http logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

bot_app = None
monitor_task = None


async def start_services():
    global bot_app, monitor_task
    
    # Base64 decode BLINKIT_STORAGE if it is set in environment variables
    storage_env = os.environ.get("BLINKIT_STORAGE")
    if storage_env:
        logger.info("Decoding BLINKIT_STORAGE environment variable into storage.json...")
        try:
            decoded_data = base64.b64decode(storage_env.strip())
            with open("storage.json", "wb") as f:
                f.write(decoded_data)
            logger.info("storage.json successfully written from environment variable.")
        except Exception as e:
            logger.error(f"Failed to decode BLINKIT_STORAGE: {e}")

    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")

    # Build the Telegram Bot application
    bot_app = build_app()

    # Initialize the application, updater, and start polling asynchronously
    await bot_app.initialize()
    await bot_app.updater.start_polling()
    await bot_app.start()
    logger.info("Blinkit Stock Bot Polling Started.")

    # Spawn the background stock monitoring task in the event loop
    monitor_task = asyncio.create_task(monitor_loop())
    logger.info("Background monitor loop started.")


async def stop_services():
    global bot_app, monitor_task
    logger.info("Shutting down bot and cleaning up...")
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    logger.info("Shutdown complete.")


async def main_async():
    await start_services()
    try:
        # Keep the program running
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping application...")
    finally:
        await stop_services()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")


if __name__ == "__main__":
    main()
