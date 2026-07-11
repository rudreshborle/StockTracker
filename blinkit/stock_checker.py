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
        page = None

        try:
            logger.info("Getting browser page for product: %s", url)
            page = await self.browser_manager.get_page()
            logger.info("Browser page created successfully")

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            logger.info(
                "Blinkit page loaded. HTTP status=%s URL=%s",
                response.status if response else "None",
                page.url
            )

            await page.wait_for_timeout(8000)

            title = await page.title()
            logger.info("Page title: %r", title)

            current_url = page.url

            if (
                "login" in title.lower()
                or current_url.endswith("/login")
                or "login" in current_url.lower()
            ):
                session_manager.invalidate()
                raise SessionExpiredException("Session expired")

            # Prefer actual product heading
            heading = page.locator("h1, h2").first

            if await heading.count() > 0:
                product_name = (await heading.inner_text()).strip()
            else:
                product_name = title

                if " - Blinkit" in product_name:
                    product_name = product_name.split(" - Blinkit")[0]

                product_name = product_name.replace("Buy ", "")
                product_name = product_name.split(" Online at Best Price")[0]
                product_name = product_name.split(" Price")[0]
                product_name = product_name.strip()

            body_text = await page.locator("body").inner_text()

            logger.info(
                "Product extracted: name=%r, body_length=%d",
                product_name,
                len(body_text)
            )

            match = re.search(
                r'(?:₹|rs\.?)\s*(\d+)',
                body_text,
                re.IGNORECASE
            )

            price = int(match.group(1)) if match else 0

            logger.info(
                "Product details successfully extracted: %s | ₹%s",
                product_name,
                price
            )

            return product_name, price

        except SessionExpiredException:
            raise

        except Exception:
            logger.exception("FAILED to retrieve product details for %s", url)

            if page:
                try:
                    os.makedirs("errors", exist_ok=True)
                    screenshot_path = (
                        f"errors/error_details_{int(time.time())}.png"
                    )
                    await page.screenshot(path=screenshot_path)
                    logger.info("Error screenshot saved: %s", screenshot_path)
                except Exception:
                    logger.exception("Could not save error screenshot")

            raise  # IMPORTANT: don't silently return Unknown Product

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
