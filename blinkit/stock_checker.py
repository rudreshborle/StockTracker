import os
import re
import time
import logging
import asyncio
import httpx
from utils.link_parser import extract_product_id

logger = logging.getLogger(__name__)


class SessionExpiredException(Exception):
    """Custom exception raised when the Blinkit session/cookies expire."""
    pass


class StockChecker:

    def __init__(self):
        self.headers = {
            "accept": "*/*",
            "app_client": "consumer_web",
            "app_version": "1010101011",
            "content-type": "application/json",
            "origin": "https://blinkit.com",
            "referer": "https://blinkit.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),

            # Set these to the location you want to monitor
            "lat": "18.663293",
            "lon": "73.797925",
        }

    def _find_product(self, obj, product_id):
        """Recursively search Blinkit's JSON for the requested product."""

        if isinstance(obj, dict):
            attrs = obj.get("common_attributes")

            if isinstance(attrs, dict):
                if str(attrs.get("product_id")) == str(product_id):
                    if "state" in attrs or "inventory" in attrs:
                        return attrs

            for value in obj.values():
                result = self._find_product(value, product_id)
                if result:
                    return result

        elif isinstance(obj, list):
            for item in obj:
                result = self._find_product(item, product_id)
                if result:
                    return result

        return None

    async def _fetch_product(self, product_id):
        api_url = f"https://blinkit.com/v1/layout/product/{product_id}"

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=30,
            follow_redirects=True
        ) as client:

            response = await client.post(api_url)

            logger.info(
                f"Blinkit API response for {product_id}: "
                f"HTTP {response.status_code}"
            )

            response.raise_for_status()

            data = response.json()

        product = self._find_product(data, product_id)

        if not product:
            raise RuntimeError(
                f"Product {product_id} not found in Blinkit API response"
            )

        return product

    async def get_product_details(self, url):
        from utils.link_parser import extract_product_id

        product_id = extract_product_id(url)

        product = await self._fetch_product(product_id)

        name = product.get("name", "Unknown Product")
        price = product.get("price", 0)

        logger.info(
            f"Product details: {name} | ₹{price}"
        )

        return name, price

    async def is_available(self, url):
        from utils.link_parser import extract_product_id

        product_id = extract_product_id(url)

        product = await self._fetch_product(product_id)

        state = product.get("state", "")
        inventory = product.get("inventory", 0)

        available = (
            state == "available"
            and inventory > 0
        )

        logger.info(
            f"Stock check {product_id}: "
            f"state={state}, inventory={inventory}, "
            f"available={available}"
        )

        return available, None
