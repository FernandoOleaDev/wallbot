"""Screen rotator - manages which search is currently displayed on ESP32."""
import os
import time
import threading
from typing import Optional, Dict, Any

from server.database import get_db


class ScreenRotator:
    """Rotates between active searches for ESP32 display."""

    _instance: Optional['ScreenRotator'] = None

    def __init__(self):
        self._current_search_id: Optional[int] = None
        self._current_index: int = 0
        self._last_rotation: float = 0
        self._rotation_interval: int = int(os.getenv("WALLBOT_ROTATION_INTERVAL", "10"))
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'ScreenRotator':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ScreenRotator()
        return cls._instance

    @property
    def rotation_interval(self) -> int:
        """Get rotation interval in seconds."""
        return self._rotation_interval

    @rotation_interval.setter
    def rotation_interval(self, value: int):
        """Set rotation interval in seconds."""
        self._rotation_interval = max(1, value)

    def get_current_search(self) -> Optional[Dict[str, Any]]:
        """Get the currently active search for display.

        Automatically rotates to next search if interval has passed.
        """
        with self._lock:
            db = get_db()
            searches = db.get_all_searches(active_only=True)

            if not searches:
                self._current_search_id = None
                return None

            now = time.time()
            time_since_rotation = now - self._last_rotation

            # Check if we need to rotate
            if time_since_rotation >= self._rotation_interval or self._current_search_id is None:
                self._rotate(searches)
                self._last_rotation = now

            # Find current search in list (it might have been deleted/deactivated)
            current = None
            for s in searches:
                if s["id"] == self._current_search_id:
                    current = s
                    break

            # If current search no longer exists/active, rotate
            if current is None and searches:
                self._current_index = 0
                self._current_search_id = searches[0]["id"]
                current = searches[0]

            return current

    def _rotate(self, searches: list):
        """Rotate to next search."""
        if not searches:
            self._current_search_id = None
            return

        # Move to next index
        self._current_index = (self._current_index + 1) % len(searches)
        self._current_search_id = searches[self._current_index]["id"]

    def get_status(self) -> Dict[str, Any]:
        """Get current rotation status."""
        db = get_db()
        searches = db.get_all_searches(active_only=True)
        current = self.get_current_search()

        now = time.time()
        time_until_rotation = max(0, self._rotation_interval - (now - self._last_rotation))

        return {
            "current_search_id": self._current_search_id,
            "current_search_name": current["name"] if current else None,
            "current_index": self._current_index,
            "total_active_searches": len(searches),
            "rotation_interval_seconds": self._rotation_interval,
            "seconds_until_next_rotation": int(time_until_rotation),
            "active_search_ids": [s["id"] for s in searches]
        }

    def force_rotation(self):
        """Force immediate rotation to next search."""
        with self._lock:
            db = get_db()
            searches = db.get_all_searches(active_only=True)
            if searches:
                self._rotate(searches)
                self._last_rotation = time.time()

    def set_current_search(self, search_id: int) -> bool:
        """Manually set current search by ID."""
        with self._lock:
            db = get_db()
            search = db.get_search(search_id)
            if search and search["active"]:
                self._current_search_id = search_id
                self._last_rotation = time.time()
                # Update index
                searches = db.get_all_searches(active_only=True)
                for i, s in enumerate(searches):
                    if s["id"] == search_id:
                        self._current_index = i
                        break
                return True
            return False


# Convenience function
def get_rotator() -> ScreenRotator:
    """Get the screen rotator instance."""
    return ScreenRotator.get_instance()
