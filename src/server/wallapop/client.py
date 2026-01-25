"""Wallapop API client."""
import logging
import os
import time
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus
import requests

logger = logging.getLogger(__name__)

WALLAPOP_API_URL = "https://api.wallapop.com/api/v3/search"

# Default coordinates (Madrid center) - used when distance filtering is enabled
DEFAULT_LATITUDE = 40.416775
DEFAULT_LONGITUDE = -3.703790


class WallapopClient:
    """Client for Wallapop search API."""

    def __init__(self):
        self.base_url = WALLAPOP_API_URL
        # Headers that mimic a real browser request to avoid CloudFront blocking
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Host': 'api.wallapop.com',
            'Origin': 'https://es.wallapop.com',
            'Pragma': 'no-cache',
            'Referer': 'https://es.wallapop.com/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-DeviceOS': '0',
        }
        self.timeout = int(os.getenv("WALLBOT_WALLAPOP_TIMEOUT", "30"))
        # Configurable default location
        self.default_latitude = float(os.getenv("WALLBOT_LATITUDE", str(DEFAULT_LATITUDE)))
        self.default_longitude = float(os.getenv("WALLBOT_LONGITUDE", str(DEFAULT_LONGITUDE)))
        # Session for connection reuse
        self._session = None

    def search(self, keywords: str, min_price: Optional[int] = None,
               max_price: Optional[int] = None, category_ids: Optional[str] = None,
               distance: int = 400, order_by: str = "newest",
               items_count: int = 20, time_filter: str = "today") -> Optional[List[Dict[str, Any]]]:
        """
        Search for items on Wallapop with pagination support.

        Args:
            keywords: Search terms
            min_price: Minimum price in cents (will be converted to euros)
            max_price: Maximum price in cents (will be converted to euros)
            category_ids: Comma-separated category IDs
            distance: Search radius in km (0 = all Spain)
            order_by: Sort order (newest, price_low_to_high, etc.)
            items_count: Number of items to request (default 20)
            time_filter: Time filter (today, week, all) - empty for no filter

        Returns:
            List of items or None on error
        """
        # Use session for connection reuse
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.headers)

        all_items = []
        next_page = None
        max_pages = (items_count // 5) + 1  # API returns ~5 items per page

        for page in range(max_pages):
            # Build URL for this page
            if next_page:
                url = f"{self.base_url}?next_page={next_page}"
            else:
                url = self._build_url(keywords, min_price, max_price, category_ids, distance, order_by, items_count, time_filter)

            if page == 0:
                print(f"  [API] URL: {url[:100]}...")

            try:
                response = self._session.get(url, timeout=self.timeout)

                # Handle specific HTTP errors
                if response.status_code == 403:
                    print(f"  [API] ERROR 403: Blocked by CloudFront/WAF")
                    logger.error("Wallapop API returned 403 Forbidden")
                    break

                response.raise_for_status()
                data = response.json()

                # Parse items from this page
                page_items = self._parse_response(data)
                all_items.extend(page_items)

                print(f"  [API] Page {page + 1}: {len(page_items)} items (total: {len(all_items)})")

                # Check for next page
                next_page = data.get("meta", {}).get("next_page")
                if not next_page or len(all_items) >= items_count:
                    break

                # Small delay between pages to avoid rate limiting
                time.sleep(0.3)

            except requests.Timeout as e:
                print(f"  [API] ERROR: Timeout after {self.timeout}s")
                logger.error(f"Wallapop API timeout: {e}")
                break
            except requests.RequestException as e:
                print(f"  [API] ERROR: {e}")
                logger.error(f"Wallapop API error: {e}")
                break
            except (KeyError, ValueError) as e:
                print(f"  [API] ERROR parsing response: {e}")
                logger.error(f"Wallapop response parsing error: {e}")
                break

        print(f"  [API] Total: {len(all_items)} items from {page + 1} pages")
        return all_items if all_items else None

    def _build_url(self, keywords: str, min_price: Optional[int],
                   max_price: Optional[int], category_ids: Optional[str],
                   distance: int, order_by: str, items_count: int = 20,
                   time_filter: str = "today") -> str:
        """Build the search URL with parameters."""
        # Convert keywords to URL format (proper encoding)
        keywords_encoded = quote_plus(keywords)

        url = f"{self.base_url}?source=search_box"
        url += f"&keywords={keywords_encoded}"

        # Time filter mapping (API uses different values)
        time_filter_map = {
            "today": "today",
            "week": "lastWeek",  # API uses "lastWeek" not "week"
            "all": None
        }
        api_time_filter = time_filter_map.get(time_filter)
        if api_time_filter:
            url += f"&time_filter={api_time_filter}"

        # Items count - try multiple parameter names
        # API might use 'step' or 'limit' instead of 'items_count'
        url += f"&step={items_count}"

        if category_ids:
            url += f"&category_ids={category_ids}"

        # Convert cents to euros for API
        if min_price:
            url += f"&min_sale_price={min_price // 100}"
        if max_price:
            url += f"&max_sale_price={max_price // 100}"

        # Distance and location (0 means all Spain - don't add location params)
        if distance and distance > 0:
            # Add coordinates for location-based search
            url += f"&latitude={self.default_latitude}"
            url += f"&longitude={self.default_longitude}"
            url += f"&distance={distance}000"  # Convert km to meters

        if order_by:
            url += f"&order_by={order_by}"

        return url

    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse the API response and extract items."""
        items = []

        try:
            # Try multiple possible paths for items in the response
            search_objects = []

            # Path 1: data.section.payload.items (current)
            section = data.get("data", {}).get("section", {})
            if section:
                payload = section.get("payload", {})
                search_objects = payload.get("items", [])
                print(f"  [API] Path data.section.payload.items: {len(search_objects)} items")

            # Path 2: data.search_objects (alternative)
            if not search_objects:
                search_objects = data.get("data", {}).get("search_objects", [])
                if search_objects:
                    print(f"  [API] Path data.search_objects: {len(search_objects)} items")

            # Path 3: search_objects at root
            if not search_objects:
                search_objects = data.get("search_objects", [])
                if search_objects:
                    print(f"  [API] Path search_objects: {len(search_objects)} items")

            # Debug: if still no items, show structure
            if not search_objects:
                print(f"  [API] WARNING: No items found! Response structure:")
                if "data" in data:
                    d = data["data"]
                    if isinstance(d, dict):
                        for k, v in d.items():
                            vtype = type(v).__name__
                            vlen = len(v) if isinstance(v, (list, dict)) else "N/A"
                            print(f"    data.{k}: {vtype} (len={vlen})")

            for obj in search_objects:
                item = self._parse_item(obj)
                if item:
                    items.append(item)

        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing Wallapop response: {e}")
            import traceback
            traceback.print_exc()

        return items

    def _parse_item(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single item from the response."""
        try:
            # Extract price
            price_obj = obj.get("price", {})
            price_cents = int(float(price_obj.get("amount", 0)) * 100)

            # Extract image URL
            images = obj.get("images", [])
            image_url = None
            if images:
                # Get medium size image
                image_url = images[0].get("urls", {}).get("medium")
                if not image_url:
                    image_url = images[0].get("urls", {}).get("small")

            # Extract location
            location = obj.get("location", {})
            city = location.get("city", "")

            # Extract publication date if available
            published_date = obj.get("creation_date") or obj.get("modified_date") or obj.get("publish_date")

            return {
                "wallapop_id": obj.get("id"),
                "title": obj.get("title", ""),
                "price": price_cents,
                "web_slug": obj.get("web_slug", ""),
                "image_url": image_url,
                "location": city,
                "seller_id": obj.get("user", {}).get("id", ""),
                "description": obj.get("description", "")[:200] if obj.get("description") else None,
                "published_date": published_date
            }
        except Exception as e:
            logger.error(f"Error parsing item: {e}")
            return None
