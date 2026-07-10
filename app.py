import time
import os
import hashlib
import logging
from fastapi import FastAPI, Request, Header, HTTPException
from contextlib import asynccontextmanager

from main import start_services, stop_services
from blinkit.browser import BrowserManager
from blinkit.session_manager import session_manager
from database.database import get_all_products
from utils.stats import stats

logger = logging.getLogger(__name__)

startup_time = 0

# Webhook configuration
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

base_url = WEBHOOK_URL or RENDER_EXTERNAL_URL
use_webhook = base_url is not None

secret_token = None
webhook_endpoint_url = None

if use_webhook:
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    webhook_endpoint_url = f"{base_url.rstrip('/')}/webhook"
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if bot_token:
        secret_token = hashlib.sha256(bot_token.encode()).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_time
    startup_time = time.time()
    
    # Start database, bot (webhook/polling), and background monitor loop
    await start_services(
        use_webhook=use_webhook,
        webhook_url=webhook_endpoint_url,
        secret_token=secret_token
    )
    
    yield
    
    # Perform clean shutdown on exit
    await stop_services()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if not use_webhook:
        raise HTTPException(status_code=404, detail="Webhook not enabled")
        
    if secret_token and x_telegram_bot_api_secret_token != secret_token:
        logger.warning("Unauthorized webhook request (secret token mismatch)")
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        data = await request.json()
        from telegram import Update
        import main
        if main.bot_app:
            update = Update.de_json(data, main.bot_app.bot)
            await main.bot_app.update_queue.put(update)
        else:
            logger.error("bot_app is not initialized yet")
            raise HTTPException(status_code=500, detail="Bot not initialized")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    return {"status": "ok"}


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Blinkit Stock Bot Running"}


@app.get("/ping")
async def ping():
    return {"ok": True}


@app.get("/version")
async def version():
    try:
        with open("VERSION", "r", encoding="utf-8") as f:
            v = f.read().strip()
        return {"version": v}
    except Exception:
        return {"version": "1.0.0"}


@app.get("/health")
async def health():
    bm = BrowserManager()
    browser_connected = (
        bm._initialized 
        and hasattr(bm, "browser") 
        and bm.browser is not None 
        and bm.browser.is_connected()
    )
    
    products = await get_all_products()
    tracked_products = len(products)
    
    last_check_time = stats["last_check"].isoformat() if stats["last_check"] else "Never"
    
    uptime_sec = int(time.time() - startup_time) if startup_time > 0 else 0
    
    try:
        with open("VERSION", "r", encoding="utf-8") as f:
            v = f.read().strip()
    except Exception:
        v = "1.0.0"
    
    return {
        "status": "healthy",
        "browser": "Healthy" if browser_connected else "⚠️ Unhealthy/Offline",
        "session": "Valid" if session_manager.is_valid() else "⚠️ Expired",
        "tracked": tracked_products,
        "last_check": last_check_time,
        "uptime": f"{uptime_sec // 60}m {uptime_sec % 60}s",
        "version": v
    }
