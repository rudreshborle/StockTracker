import os
import re
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from utils.link_parser import extract_product_id
from database.database import add_product, get_all_products, remove_product
from blinkit.stock_checker import StockChecker, SessionExpiredException
from blinkit.session_manager import session_manager
from utils.stats import stats

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logger = logging.getLogger(__name__)


def get_last_login_info():
    if not os.path.exists("last_login.json"):
        return "Never logged in"
    try:
        with open("last_login.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        login_time = datetime.fromisoformat(data["time"])
        abs_time = login_time.strftime("%d %b %Y %H:%M")
        
        # Calculate relative time difference
        delta = datetime.now() - login_time
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            rel_time = "just now"
        elif minutes < 60:
            rel_time = f"{minutes} min ago"
        elif minutes < 1440:
            rel_time = f"{minutes // 60} hours ago"
        else:
            rel_time = f"{minutes // 1440} days ago"
            
        return f"{abs_time} ({rel_time})"
    except Exception as e:
        logger.error(f"Error parsing last_login.json: {e}")
        return "Unknown"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User '{user}' invoked /start command.")
    welcome_text = (
        "👋 Welcome to the *Blinkit Stock Bot*!\n\n"
        "Send me a Blinkit product link (e.g., `https://blinkit.com/prn/...`) to start tracking it.\n\n"
        "Available commands:\n"
        "📋 /list - Show all currently tracked products\n"
        "❌ /remove <id> - Stop tracking a product\n"
        "🔄 /reload - Reload the browser context manually\n"
        "📊 /health - Check system health diagnostics\n"
        "🔑 /loginstatus - View Blinkit session status details"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User '{user}' invoked /list command.")
    products = await get_all_products()
    if not products:
        await update.message.reply_text(
            "📋 *Currently tracking 0 products.* Send me a Blinkit link to start!",
            parse_mode="Markdown"
        )
        return

    msg = "📋 *Currently Tracking*\n\n"
    emoji_nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, p in enumerate(products):
        emoji_num = emoji_nums[idx] if idx < len(emoji_nums) else f"{idx + 1}."
        status_emoji = (
            "🟢 In Stock"
            if p["last_stock"] == 1
            else "🔴 Out of Stock"
            if p["last_stock"] == 0
            else "⚪ Unchecked"
        )
        msg += f"{emoji_num} *{p['name']}*\n{status_emoji}\n`ID: {p['product_id']}`\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    if not context.args:
        await update.message.reply_text(
            "❌ Please specify the product ID to remove. Example: `/remove 771901`",
            parse_mode="Markdown"
        )
        return

    product_id = context.args[0].strip()
    logger.info(f"User '{user}' requested removal of product ID {product_id}.")
    await remove_product(product_id)
    await update.message.reply_text(
        f"✅ Stopped tracking product with ID `{product_id}`",
        parse_mode="Markdown"
    )


async def handle_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User '{user}' requested /health status.")
    
    products = await get_all_products()
    product_count = len(products)

    last_check_str = stats["last_check"].strftime("%H:%M:%S") if stats["last_check"] else "Never"
    
    if stats["next_check"]:
        delta = stats["next_check"] - datetime.now()
        seconds_left = int(delta.total_seconds())
        if seconds_left <= 0:
            next_check_str = "Checking now..."
        elif seconds_left < 60:
            next_check_str = f"{seconds_left} sec"
        else:
            next_check_str = f"{seconds_left // 60} min {seconds_left % 60} sec"
    else:
        next_check_str = "N/A"

    browser_status = "Healthy" if stats["browser_healthy"] else "⚠️ Unhealthy"
    session_status = "Valid" if session_manager.is_valid() else "⚠️ Expired"

    try:
        with open("VERSION", "r", encoding="utf-8") as f:
            v = f.read().strip()
    except Exception:
        v = "1.0.0"

    health_msg = (
        f"✅ *Blinkit Stock Bot*\n\n"
        f"*Status:* {stats['status']}\n"
        f"*Tracked Products:* {product_count}\n\n"
        f"*Last Check:*\n{last_check_str}\n\n"
        f"*Browser:*\n{browser_status}\n\n"
        f"*Session:*\n{session_status}\n\n"
        f"*Last Login:*\n{get_last_login_info()}\n\n"
        f"*Next Check:*\n{next_check_str}\n\n"
        f"*Version:*\n{v}"
    )
    await update.message.reply_text(health_msg, parse_mode="Markdown")


async def handle_loginstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User '{user}' requested /loginstatus.")
    
    session_status = "✅ Valid" if session_manager.is_valid() else "❌ Expired"
    browser_status = "Healthy" if stats["browser_healthy"] else "Unhealthy"
    
    status_msg = (
        f"🔑 *Blinkit Session Status*\n\n"
        f"*Status*\n{session_status}\n\n"
        f"*Last Login*\n{get_last_login_info()}\n\n"
        f"*Browser*\n{browser_status}"
    )
    await update.message.reply_text(status_msg, parse_mode="Markdown")


async def handle_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User '{user}' invoked /reload command.")
    status_msg = await update.message.reply_text("🔄 Reloading browser context...")
    try:
        from blinkit.browser import BrowserManager
        bm = BrowserManager()
        await bm.init()
        session_manager.restore()
        stats["session_valid"] = True
        await status_msg.edit_text("✅ Browser context reloaded and session restored.")
        logger.info(f"Context reloaded successfully for user '{user}'.")
    except Exception as e:
        logger.error(f"Failed to reload context: {e}")
        await status_msg.edit_text(f"❌ Failed to reload browser context: {e}")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    text = update.message.text.strip()

    if "blinkit.com" not in text:
        await update.message.reply_text("❌ Please send a valid Blinkit product link.")
        return

    url_match = re.search(r"(https?://[^\s]+)", text)
    if not url_match:
        await update.message.reply_text("❌ Could not extract URL from message.")
        return

    url = url_match.group(1)
    product_id = extract_product_id(url)

    if not product_id:
        await update.message.reply_text(
            "❌ Could not extract product ID from the link. Make sure the URL has `/prid/`."
        )
        return

    logger.info(f"User '{user}' sent link for product ID {product_id}.")
    status_msg = await update.message.reply_text(
        "🔍 Extracting product details and setting up tracking..."
    )

    checker = StockChecker()

    try:
        logger.info("STEP 1: Getting product details for %s", product_id)
        name, price = await checker.get_product_details(url)
        logger.info("STEP 1 SUCCESS: name=%r price=%s", name, price)

        logger.info("STEP 2: Checking stock for %s", product_id)
        is_in_stock, _ = await checker.is_available(url)
        logger.info("STEP 2 SUCCESS: in_stock=%s", is_in_stock)

    except SessionExpiredException:
        logger.exception("Blinkit session expired while adding %s", product_id)
        await status_msg.edit_text(
            "⚠️ Blinkit session expired.",
        )
        return

    except Exception:
        logger.exception("Failed to process product %s", product_id)
        await status_msg.edit_text(
            "❌ Failed to retrieve product details. Please try again later."
        )
        return

    stock_val = 1 if is_in_stock else 0
    await add_product(product_id, name, url, stock_val)

    status_emoji = "🟢 In Stock" if is_in_stock else "🔴 Out of Stock"
    reply = (
        f"✅ *Tracking Started*\n\n"
        f"🚗 *{name}*\n\n"
        f"Current Status:\n"
        f"{status_emoji}\n\n"
        f"I'll notify you the next time it changes from\n"
        f"Out of Stock → In Stock."
    )

    await status_msg.edit_text(reply, parse_mode="Markdown")
    logger.info(f"Successfully started tracking '{name}' (ID: {product_id}) for user '{user}'.")


def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("remove", handle_remove))
    app.add_handler(CommandHandler("health", handle_health))
    app.add_handler(CommandHandler("loginstatus", handle_loginstatus))
    app.add_handler(CommandHandler("reload", handle_reload))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link))
    return app
