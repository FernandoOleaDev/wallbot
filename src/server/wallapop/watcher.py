"""Wallapop watcher - periodically searches and saves new items."""
import logging
import os
import threading
import time
from typing import Optional, Dict, Any, Callable

from server.database import get_db
from server.wallapop.client import WallapopClient

logger = logging.getLogger(__name__)

# Global watcher instance
_watcher_instance: Optional['Watcher'] = None


def get_watcher() -> 'Watcher':
    """Get the global watcher instance."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = Watcher()
    return _watcher_instance


class Watcher:
    """Watches Wallapop for new items matching saved searches."""

    def __init__(self):
        self.client = WallapopClient()
        # Load interval from database, fallback to env var, then default
        db = get_db()
        db_interval = db.get_config("search_interval", "")
        if db_interval:
            self.interval = int(db_interval)
        else:
            self.interval = int(os.getenv("WALLBOT_SEARCH_INTERVAL", "300"))
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: float = 0
        self._on_new_item: Optional[Callable] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_run(self) -> float:
        return self._last_run

    def set_on_new_item_callback(self, callback: Callable):
        """Set callback to be called when new item is found."""
        self._on_new_item = callback

    def start(self):
        """Start the watcher in a background thread."""
        if self._running:
            logger.warning("Watcher already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Watcher started (interval: {self.interval}s)")

    def stop(self):
        """Stop the watcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Watcher stopped")

    def run_once(self) -> Dict[str, Any]:
        """Run a single search cycle manually.

        Returns:
            Summary of what was found
        """
        return self._search_cycle()

    def search_single(self, search_id: int) -> Dict[str, Any]:
        """Run search for a single search ID.

        Returns:
            Summary of results
        """
        db = get_db()
        search = db.get_search(search_id)

        if not search:
            return {"error": "Search not found", "search_id": search_id}

        if not search["active"]:
            return {"error": "Search is not active", "search_id": search_id}

        return self._process_search(search)

    def _run_loop(self):
        """Main loop running in background thread."""
        # Initial delay to let server start
        time.sleep(5)

        while self._running:
            try:
                self._search_cycle()
            except Exception as e:
                logger.error(f"Error in watcher cycle: {e}")

            # Sleep in small increments to allow quick shutdown
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def _search_cycle(self) -> Dict[str, Any]:
        """Execute one search cycle for all active searches."""
        self._last_run = time.time()
        db = get_db()
        searches = db.get_all_searches(active_only=True)

        results = {
            "timestamp": self._last_run,
            "searches_processed": 0,
            "total_items_found": 0,
            "new_items_saved": 0,
            "searches": []
        }

        logger.info(f"Starting search cycle for {len(searches)} active searches")

        for search in searches:
            try:
                search_result = self._process_search(search)
                results["searches"].append(search_result)
                results["searches_processed"] += 1
                results["total_items_found"] += search_result.get("items_found", 0)
                results["new_items_saved"] += search_result.get("new_items", 0)
            except Exception as e:
                logger.error(f"Error processing search {search['id']}: {e}")
                results["searches"].append({
                    "search_id": search["id"],
                    "error": str(e)
                })

        logger.info(f"Search cycle complete: {results['new_items_saved']} new items from {results['searches_processed']} searches")
        return results

    def _process_search(self, search: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single search."""
        db = get_db()

        result = {
            "search_id": search["id"],
            "search_name": search["name"],
            "items_found": 0,
            "new_items": 0,
            "updated_items": 0
        }

        # Get config options
        items_count = int(db.get_config("items_count", "20"))
        time_filter = db.get_config("time_filter", "all")

        # Call Wallapop API
        items = self.client.search(
            keywords=search["keywords"],
            min_price=search.get("min_price"),
            max_price=search.get("max_price"),
            category_ids=search.get("category_ids"),
            distance=search.get("distance", 400),
            order_by=search.get("order_by", "newest"),
            items_count=items_count,
            time_filter=time_filter
        )

        if items is None:
            result["error"] = "API request failed"
            return result

        result["items_found"] = len(items)
        print(f"  [Search] '{search['name']}': Wallapop returned {len(items)} items")
        logger.debug(f"Search '{search['name']}': found {len(items)} items")

        # Get required words filter
        required_words = search.get("required_words")
        required_words_list = []
        if required_words:
            required_words_list = [w.strip().lower() for w in required_words.split(",") if w.strip()]
            print(f"  [Filter] Required words: {required_words_list}")

        filtered_count = 0

        matched_count = 0

        # Debug: show all titles if filtering
        if required_words_list and items:
            print(f"  [Debug] Titles from API:")
            for i, item in enumerate(items[:10]):  # Show first 10
                print(f"    {i+1}. {item.get('title', 'N/A')[:70]}")

        # Process each item
        for item in items:
            try:
                # Check required words filter
                if required_words_list:
                    title_lower = (item.get("title") or "").lower()
                    missing_words = [w for w in required_words_list if w not in title_lower]
                    if missing_words:
                        # Skip this item - doesn't contain all required words
                        filtered_count += 1
                        continue
                    else:
                        matched_count += 1
                        print(f"  [Filter] MATCH: '{item.get('title', 'N/A')[:60]}'")

                existing = db.get_item_by_wallapop_id(item["wallapop_id"], search["id"])

                if existing is None:
                    # New item - save it
                    db.create_item(
                        wallapop_id=item["wallapop_id"],
                        search_id=search["id"],
                        title=item["title"],
                        price=item["price"],
                        web_slug=item["web_slug"],
                        image_url=item["image_url"],
                        location=item["location"],
                        seller_id=item["seller_id"],
                        created_at=item.get("created_at"),
                        modified_at=item.get("modified_at")
                    )
                    result["new_items"] += 1

                    # Update last_item_id on search
                    if result["new_items"] == 1:
                        db.update_search(search["id"], last_item_id=item["wallapop_id"])

                    # Call callback if set
                    if self._on_new_item:
                        try:
                            self._on_new_item(search, item)
                        except Exception as e:
                            logger.error(f"Error in on_new_item callback: {e}")

                else:
                    # Existing item - check for price change
                    if item["price"] < existing["price"]:
                        # Price dropped!
                        old_price = existing["price"]
                        history = f"{old_price}"
                        if existing.get("price_history"):
                            history += f" < {existing['price_history']}"

                        db.update_item_price(existing["id"], item["price"], history)
                        result["updated_items"] += 1
                        logger.info(f"Price drop: {item['title']} - {old_price} -> {item['price']}")

            except Exception as e:
                logger.error(f"Error processing item {item.get('wallapop_id')}: {e}")

        if required_words_list:
            print(f"  [Filter] Result: {matched_count} matched, {filtered_count} filtered out")

        if result["new_items"] > 0:
            logger.info(f"Search '{search['name']}': {result['new_items']} new items saved")

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get watcher status."""
        return {
            "running": self._running,
            "interval_seconds": self.interval,
            "last_run": self._last_run,
            "seconds_since_last_run": int(time.time() - self._last_run) if self._last_run > 0 else None
        }
