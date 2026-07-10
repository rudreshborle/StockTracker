import time
from fastapi import FastAPI
from contextlib import asynccontextmanager

from main import start_services, stop_services
from blinkit.browser import BrowserManager
from blinkit.session_manager import session_manager
from database.database import get_all_products
from utils.stats import stats

startup_time = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_time
    startup_time = time.time()
    
    # Start database, bot polling, and background monitor loop
    await start_services()
    
    yield
    
    # Perform clean shutdown on exit
    await stop_services()


app = FastAPI(lifespan=lifespan)


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
