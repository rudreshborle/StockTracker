import os
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class BrowserManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BrowserManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        pass

    async def init(self):
        # Close existing resources safely first
        try:
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        logger.info("Launching Chromium and reloading context state...")
        self.playwright = await async_playwright().start()
        # Headless=False is used to bypass Cloudflare protection
        self.browser = await self.playwright.chromium.launch(headless=False)
        
        storage_path = "storage.json"
        if os.path.exists(storage_path):
            self.context = await self.browser.new_context(storage_state=storage_path)
        else:
            self.context = await self.browser.new_context()
        self._initialized = True

    async def get_page(self):
        # Self-healing: Re-initialize if not initialized, browser closed, or disconnected
        if (not self._initialized 
                or not hasattr(self, 'browser') 
                or not self.browser 
                or not self.browser.is_connected()):
            logger.warning("Browser is disconnected or uninitialized. Triggering self-healing...")
            await self.init()

        try:
            return await self.context.new_page()
        except Exception as e:
            logger.warning(f"Failed to create page: {e}. Attempting browser re-init self-healing...")
            await self.init()
            return await self.context.new_page()

    async def close(self):
        if self._initialized:
            try:
                await self.browser.close()
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error closing browser manager resources: {e}")
            self._initialized = False
            BrowserManager._instance = None
