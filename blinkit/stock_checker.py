import os
import re
import time
import logging
import asyncio
from curl_cffi.requests import AsyncSession
from utils.link_parser import extract_product_id

logger = logging.getLogger(__name__)


class SessionExpiredException(Exception):
    """Custom exception raised when the Blinkit session/cookies expire."""
    pass


class StockChecker:

    def __init__(self):
        pass

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

        # Configurable lat and lon
        lat = os.getenv("BLINKIT_LAT", "18.663293")
        lon = os.getenv("BLINKIT_LON", "73.79792499999999")

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,hi;q=0.8",
            "app_client": "consumer_web",
            "app_version": "1010101011",
            "content-length": "0",
            "content-type": "application/json",
            "dnt": "1",
            "is-response-compression-enabled": "false",
            "lat": lat,
            "lon": lon,
            "origin": "https://blinkit.com",
            "priority": "u=1, i",
            "rn_bundle_version": "1009003012",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "web_app_version": "1008010016",
            "x-age-consent-granted": "false",
        }

        # Optional session/authentication credentials from env
        access_token = os.getenv("BLINKIT_ACCESS_TOKEN")
        auth_key = os.getenv("BLINKIT_AUTH_KEY")
        device_id = os.getenv("BLINKIT_DEVICE_ID")
        session_uuid = os.getenv("BLINKIT_SESSION_UUID")
        cookie = os.getenv("BLINKIT_COOKIE")

        if access_token:
            headers["access_token"] = access_token
        if auth_key:
            headers["auth_key"] = auth_key
        if device_id:
            headers["device_id"] = device_id
        if session_uuid:
            headers["session_uuid"] = session_uuid
        if cookie:
            # Strip quotes if they were added in .env file
            if cookie.startswith('"') and cookie.endswith('"'):
                cookie = cookie[1:-1]
            elif cookie.startswith("'") and cookie.endswith("'"):
                cookie = cookie[1:-1]
            headers["cookie"] = cookie

        # Log configuration details without exposing keys or credentials
        logger.info(
            "Fetching Blinkit product %s via Layout API. "
            "Location: lat=%s, lon=%s. "
            "Credentials present: access_token=%s, auth_key=%s, device_id=%s, "
            "session_uuid=%s, cookie=%s",
            product_id,
            lat,
            lon,
            bool(access_token),
            bool(auth_key),
            bool(device_id),
            bool(session_uuid),
            bool(cookie)
        )

        async with AsyncSession(impersonate="chrome") as session:
            response = await session.post(api_url, headers=headers, timeout=30)

            logger.info(
                "Blinkit Layout API response for product %s: HTTP %s",
                product_id,
                response.status_code
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
        product_id = extract_product_id(url)
        product = await self._fetch_product(product_id)

        name = product.get("name", "Unknown Product")
        price = product.get("price", 0)

        logger.info(
            "Product details extracted: name=%r, price=₹%s",
            name,
            price
        )

        return name, price

    async def is_available(self, url):
        product_id = extract_product_id(url)
        product = await self._fetch_product(product_id)

        state = product.get("state", "")
        inventory = product.get("inventory", 0)

        available = (
            state == "available"
            and inventory > 0
        )

        logger.info(
            "Product availability checked: product_id=%s, state=%r, inventory=%d, available=%s",
            product_id,
            state,
            inventory,
            available
        )

        return available, None
