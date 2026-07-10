import os
import asyncio
import random
import logging
from datetime import datetime, timedelta
from telegram import Bot
from dotenv import load_dotenv
from database.database import get_all_products, update_stock
from blinkit.stock_checker import StockChecker, SessionExpiredException
from blinkit.session_manager import session_manager
from utils.stats import stats

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_INTERVAL = 60  # 1 minute in seconds

logger = logging.getLogger(__name__)

# Duplicate alert protection: in-memory cache of sent alert times
# Maps: product_id -> last_sent_datetime
last_alert_sent = {}


async def send_restock_alert(bot: Bot, product_name: str, price: int, url: str, screenshot_path: str = None):
    timestamp = datetime.now().strftime("%I:%M %p")
    message = (
        f"🚨 *HOT WHEELS RESTOCK!*\n\n"
        f"🚗 *{product_name}*\n"
        f"💰 *Price:* ₹{price if price > 0 else 'N/A'}\n"
        f"✅ *Status:* Now Available\n"
        f"🕒 *Time:* {timestamp}\n\n"
        f"🔗 [Open Blinkit]({url})"
    )
    try:
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=photo,
                    caption=message,
                    parse_mode="Markdown"
                )
            logger.info(f"Telegram photo alert sent for {product_name}")
        else:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            logger.info(f"Telegram text notification sent for {product_name}")
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")


async def send_session_expired_alert(bot: Bot):
    message = "⚠️ *Blinkit session expired.*\nPlease run `python blinkit/login.py` again."
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.warning("Sent session expired notification to Telegram")
    except Exception as e:
        logger.error(f"Error sending session expired Telegram alert: {e}")


async def monitor_loop():
    logger.info("Starting background stock monitor loop...")
    bot = Bot(token=TOKEN)
    checker = StockChecker()

    # Track storage.json mtime to auto-detect updates
    storage_path = "storage.json"
    last_mtime = os.path.getmtime(storage_path) if os.path.exists(storage_path) else 0

    while True:
        # 1. Check for storage.json updates
        if os.path.exists(storage_path):
            current_mtime = os.path.getmtime(storage_path)
            if last_mtime != 0 and current_mtime != last_mtime:
                logger.info("Detected update in storage.json. Reloading browser context...")
                try:
                    await checker.browser_manager.init()
                    session_manager.restore()
                    stats["session_valid"] = True
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text="✅ *Blinkit session restored.* Resuming stock monitoring...",
                        parse_mode="Markdown"
                    )
                    logger.info("Session restored and browser context reloaded.")
                except Exception as e:
                    logger.error(f"Failed to reload browser context: {e}")
                last_mtime = current_mtime
            elif last_mtime == 0:
                last_mtime = current_mtime

        # 2. Pause loop if session is invalid
        if not session_manager.is_valid():
            logger.info("Session is invalid. Pausing stock monitoring...")
            stats["status"] = "Paused (Session Expired)"
            stats["session_valid"] = False
            # Sleep 30 seconds before checking file mtime again
            await asyncio.sleep(30)
            continue

        sleep_time = BASE_INTERVAL
        try:
            # 3. Update stats for /health command
            stats["status"] = "Running"
            stats["last_check"] = datetime.now()
            
            products = await get_all_products()
            if not products:
                logger.info("Tracking 0 products. Sleeping...")
                sleep_time = 30
                stats["next_check"] = datetime.now() + timedelta(seconds=sleep_time)
                await asyncio.sleep(sleep_time)
                continue

            logger.info(f"Tracking {len(products)} products")
            stats["browser_healthy"] = True
            stats["session_valid"] = True

            for product in products:
                # Re-check session validity inside loop in case a previous check invalidated it
                if not session_manager.is_valid():
                    break

                product_id = product["product_id"]
                name = product["name"]
                url = product["url"]
                last_stock = product["last_stock"]

                try:
                    is_in_stock, screenshot_path = await checker.is_available(url)
                    current_stock = 1 if is_in_stock else 0

                    status_text = "IN STOCK" if is_in_stock else "OUT OF STOCK"
                    logger.info(f"{name} -> {status_text}")

                    # Transition detection (0 -> 1)
                    if current_stock == 1 and last_stock == 0:
                        # Duplicate notification check: skip if sent within 3 minutes (180s)
                        last_sent = last_alert_sent.get(product_id)
                        if last_sent and (datetime.now() - last_sent).total_seconds() < 180:
                            logger.info(f"Duplicate alert prevented for {name}. Already sent recently.")
                        else:
                            _, price = await checker.get_product_details(url)
                            await send_restock_alert(bot, name, price, url, screenshot_path)
                            last_alert_sent[product_id] = datetime.now()

                    # Update DB
                    await update_stock(product_id, current_stock)

                except SessionExpiredException:
                    logger.error("Session expired during check.")
                    stats["session_valid"] = False
                    await send_session_expired_alert(bot)
                    break
                except Exception as e:
                    logger.error(f"Failed to check product {name}: {e}")
                    stats["browser_healthy"] = False

        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            stats["browser_healthy"] = False

        if not session_manager.is_valid():
            continue

        # Randomize check interval (1 minute with jitter)
        jitter = random.randint(-5, 10)
        sleep_time = max(30, BASE_INTERVAL + jitter)
        stats["next_check"] = datetime.now() + timedelta(seconds=sleep_time)
        logger.info(f"Monitor check complete. Sleeping for {sleep_time} seconds...")
        await asyncio.sleep(sleep_time)
