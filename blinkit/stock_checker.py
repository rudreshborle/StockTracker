import os
import re
import time
import logging
import asyncio
from blinkit.browser import BrowserManager
from blinkit.session_manager import session_manager
from utils.link_parser import extract_product_id

logger = logging.getLogger(__name__)


class SessionExpiredException(Exception):
    """Custom exception raised when the Blinkit session/cookies expire."""
    pass


class StockChecker:

    def __init__(self):
        self.browser_manager = BrowserManager()

    async def is_available(self, url):
        product_id = extract_product_id(url) or "temp"
        # Retry loop for robust stock checking
        for attempt in range(3):
            try:
                available, screenshot_path = await self._check_stock_once(url, product_id)
                return available, screenshot_path
            except SessionExpiredException:
                # Do not retry on session expiration, raise immediately
                raise
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/3 failed for {url}: {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
        
        # If all 3 attempts fail
        logger.error(f"All 3 stock check attempts failed for {url}")
        return False, None

    async def _check_stock_once(self, url, product_id):
        page = await self.browser_manager.get_page()
        available = False
        screenshot_path = None

        try:
            await page.goto(url)
            await page.wait_for_timeout(8000)

            # Check for session expiration
            title = await page.title()
            current_url = page.url
            if "login" in title.lower() or current_url.endswith("/login") or "login" in current_url.lower():
                # Invalidate session in global manager
                session_manager.invalidate()
                
                # Take screenshot of login screen for debugging
                os.makedirs("errors", exist_ok=True)
                await page.screenshot(path=f"errors/login_expired_{int(time.time())}.png")
                logger.error("Blinkit session expired or redirected to login.")
                raise SessionExpiredException("Session expired")

            # Find the stock action button using our robust first-match logic
            controls = page.locator("button, [role='button']")
            count = await controls.count()

            for i in range(count):
                btn = controls.nth(i)
                if await btn.is_visible():
                    text = (await btn.inner_text()).strip().lower()
                    if text in ["add to cart", "add", "out of stock", "notify me"]:
                        if text in ["add to cart", "add"]:
                            available = True
                            # Capture page screenshot upon finding in-stock button
                            os.makedirs("errors", exist_ok=True)
                            screenshot_path = f"errors/restock_{product_id}_{int(time.time())}.png"
                            await page.screenshot(path=screenshot_path)
                        break
            
            return available, screenshot_path

        except SessionExpiredException:
            raise
        except Exception as e:
            # Capture screenshot on unexpected error
            os.makedirs("errors", exist_ok=True)
            screenshot_path = f"errors/error_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.error(f"Unexpected error in _check_stock_once: {e}. Screenshot saved to {screenshot_path}")
            raise e
        finally:
            try:
                await page.close()
            except Exception:
                pass

    async def get_product_details(self, url):
        page = await self.browser_manager.get_page()
        product_name = "Unknown Product"
        price = 0

        try:
            await page.goto(url)
            await page.wait_for_timeout(8000)

            title = await page.title()
            current_url = page.url
            if "login" in title.lower() or current_url.endswith("/login") or "login" in current_url.lower():
                session_manager.invalidate()
                os.makedirs("errors", exist_ok=True)
                await page.screenshot(path=f"errors/login_expired_{int(time.time())}.png")
                raise SessionExpiredException("Session expired")

            if " - Blinkit" in title:
                title = title.split(" - Blinkit")[0]
            if "Buy " in title:
                title = title.replace("Buy ", "")
            if " Online at Best Price" in title:
                title = title.replace(" Online at Best Price", "")
            if " Price" in title:
                title = title.split(" Price")[0]
            
            product_name = title.strip()

            body_text = await page.locator("body").inner_text()
            match = re.search(r'(?:₹|rs\.?)\s*(\d+)', body_text, re.IGNORECASE)
            if match:
                price = int(match.group(1))
            else:
                match = re.search(r'(?:pc|unit|g|kg)\s*\n\s*(\d+)', body_text, re.IGNORECASE)
                if match:
                    price = int(match.group(1))
        except SessionExpiredException:
            raise
        except Exception as e:
            os.makedirs("errors", exist_ok=True)
            screenshot_path = f"errors/error_details_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.error(f"Unexpected error in get_product_details: {e}. Screenshot saved to {screenshot_path}")
        finally:
            try:
                await page.close()
            except Exception:
                pass

        return product_name, price
