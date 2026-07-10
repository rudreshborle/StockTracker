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


async def main_async():
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")

    # Build the Telegram Bot application
    app = build_app()

    # Initialize the application, updater, and start polling asynchronously
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    logger.info("Blinkit Stock Bot Polling Started.")

    # Spawn the background stock monitoring task in the event loop
    monitor_task = asyncio.create_task(monitor_loop())
    logger.info("Background monitor loop started.")

    try:
        # Keep the program running
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping application...")
    finally:
        # Perform clean shutdown of bot resources
        logger.info("Shutting down bot and cleaning up...")
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Shutdown complete.")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")


if __name__ == "__main__":
    main()
