"""SQLite database operations."""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Global database instance
_db_instance: Optional['Database'] = None


def get_db() -> 'Database':
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        data_dir = os.getenv("WALLBOT_DATA_DIR", "./data")
        db_path = os.path.join(data_dir, "db.sqlite")
        _db_instance = Database(db_path)
    return _db_instance


class Database:
    """SQLite database handler."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Search table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    min_price INTEGER,
                    max_price INTEGER,
                    category_ids TEXT,
                    distance INTEGER DEFAULT 400,
                    order_by TEXT DEFAULT 'newest',
                    active INTEGER DEFAULT 1,
                    last_item_id TEXT,
                    required_words TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Migration: add required_words column if it doesn't exist
            cursor.execute("PRAGMA table_info(search)")
            columns = [col[1] for col in cursor.fetchall()]
            if "required_words" not in columns:
                cursor.execute("ALTER TABLE search ADD COLUMN required_words TEXT")

            # Item table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallapop_id TEXT NOT NULL,
                    search_id INTEGER NOT NULL,
                    title TEXT,
                    price INTEGER,
                    price_history TEXT,
                    web_slug TEXT,
                    image_url TEXT,
                    location TEXT,
                    seller_id TEXT,
                    published_date TEXT,
                    first_seen TEXT DEFAULT (datetime('now')),
                    last_updated TEXT DEFAULT (datetime('now')),
                    notified INTEGER DEFAULT 0,
                    UNIQUE(wallapop_id, search_id),
                    FOREIGN KEY(search_id) REFERENCES search(id) ON DELETE CASCADE
                )
            """)

            # Migration: add published_date column if it doesn't exist
            cursor.execute("PRAGMA table_info(item)")
            item_columns = [col[1] for col in cursor.fetchall()]
            if "published_date" not in item_columns:
                cursor.execute("ALTER TABLE item ADD COLUMN published_date TEXT")

            # Config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Initialize default config values
            cursor.execute("""
                INSERT OR IGNORE INTO config (key, value) VALUES
                ('search_interval', '300'),
                ('rotation_interval', '10'),
                ('items_count', '20'),
                ('time_filter', 'all')
            """)

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_search ON item(search_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_wallapop ON item(wallapop_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_active ON search(active)")

    # ==================== SEARCH OPERATIONS ====================

    def create_search(self, name: str, keywords: str, min_price: Optional[int] = None,
                      max_price: Optional[int] = None, category_ids: Optional[str] = None,
                      distance: int = 400, active: bool = True,
                      required_words: Optional[str] = None) -> Dict[str, Any]:
        """Create a new search."""
        now = datetime.utcnow().isoformat() + "Z"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search (name, keywords, min_price, max_price, category_ids,
                                   distance, active, required_words, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, keywords, min_price, max_price, category_ids,
                  distance, 1 if active else 0, required_words, now, now))

            search_id = cursor.lastrowid
            return self.get_search(search_id)

    def get_search(self, search_id: int) -> Optional[Dict[str, Any]]:
        """Get a search by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*,
                       (SELECT COUNT(*) FROM item WHERE search_id = s.id) as items_count
                FROM search s
                WHERE s.id = ?
            """, (search_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_search_dict(row)
            return None

    def get_all_searches(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get all searches."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("""
                    SELECT s.*,
                           (SELECT COUNT(*) FROM item WHERE search_id = s.id) as items_count
                    FROM search s
                    WHERE s.active = 1
                    ORDER BY s.created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT s.*,
                           (SELECT COUNT(*) FROM item WHERE search_id = s.id) as items_count
                    FROM search s
                    ORDER BY s.created_at DESC
                """)
            rows = cursor.fetchall()
            return [self._row_to_search_dict(row) for row in rows]

    def update_search(self, search_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a search."""
        allowed_fields = {'name', 'keywords', 'min_price', 'max_price',
                         'category_ids', 'distance', 'active', 'last_item_id',
                         'required_words'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return self.get_search(search_id)

        updates['updated_at'] = datetime.utcnow().isoformat() + "Z"

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [search_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE search SET {set_clause} WHERE id = ?
            """, values)

        return self.get_search(search_id)

    def delete_search(self, search_id: int) -> bool:
        """Delete a search and its items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM item WHERE search_id = ?", (search_id,))
            cursor.execute("DELETE FROM search WHERE id = ?", (search_id,))
            return cursor.rowcount > 0

    def delete_items_for_search(self, search_id: int) -> int:
        """Delete all items for a search (reset)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM item WHERE search_id = ?", (search_id,))
            return cursor.rowcount

    def delete_all_data(self) -> Dict[str, int]:
        """Delete all searches and items from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM item")
            items_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM search")
            searches_count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM item")
            cursor.execute("DELETE FROM search")
            return {"items_deleted": items_count, "searches_deleted": searches_count}

    def _row_to_search_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a search dictionary."""
        return {
            "id": row["id"],
            "name": row["name"],
            "keywords": row["keywords"],
            "min_price": row["min_price"],
            "max_price": row["max_price"],
            "category_ids": row["category_ids"],
            "distance": row["distance"],
            "order_by": row["order_by"],
            "active": bool(row["active"]),
            "last_item_id": row["last_item_id"],
            "required_words": row["required_words"] if "required_words" in row.keys() else None,
            "items_count": row["items_count"] if "items_count" in row.keys() else 0,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    # ==================== ITEM OPERATIONS ====================

    def create_item(self, wallapop_id: str, search_id: int, title: str,
                    price: int, web_slug: str, image_url: str,
                    location: str, seller_id: str,
                    published_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new item (or ignore if duplicate)."""
        now = datetime.utcnow().isoformat() + "Z"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO item (wallapop_id, search_id, title, price, web_slug,
                                     image_url, location, seller_id, published_date, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (wallapop_id, search_id, title, price, web_slug,
                      image_url, location, seller_id, published_date, now, now))
                return self.get_item(cursor.lastrowid)
            except sqlite3.IntegrityError:
                # Duplicate - return existing
                return self.get_item_by_wallapop_id(wallapop_id, search_id)

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM item WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_item_dict(row)
            return None

    def get_item_by_wallapop_id(self, wallapop_id: str, search_id: int) -> Optional[Dict[str, Any]]:
        """Get an item by Wallapop ID and search ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM item
                WHERE wallapop_id = ? AND search_id = ?
            """, (wallapop_id, search_id))
            row = cursor.fetchone()
            if row:
                return self._row_to_item_dict(row)
            return None

    def get_items_for_search(self, search_id: int, limit: int = 50,
                             offset: int = 0) -> List[Dict[str, Any]]:
        """Get items for a search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Order by id DESC - newest inserted items first
            cursor.execute("""
                SELECT * FROM item
                WHERE search_id = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (search_id, limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_item_dict(row) for row in rows]

    def get_latest_item(self, search_id: int) -> Optional[Dict[str, Any]]:
        """Get the latest item for a search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM item
                WHERE search_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (search_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_item_dict(row)
            return None

    def get_items_count(self, search_id: int) -> int:
        """Get total items count for a search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM item WHERE search_id = ?", (search_id,))
            return cursor.fetchone()[0]

    def update_item_price(self, item_id: int, new_price: int,
                          price_history: str) -> Optional[Dict[str, Any]]:
        """Update item price and history."""
        now = datetime.utcnow().isoformat() + "Z"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE item
                SET price = ?, price_history = ?, last_updated = ?
                WHERE id = ?
            """, (new_price, price_history, now, item_id))
        return self.get_item(item_id)

    def _row_to_item_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to an item dictionary."""
        return {
            "id": row["id"],
            "wallapop_id": row["wallapop_id"],
            "search_id": row["search_id"],
            "title": row["title"],
            "price": row["price"],
            "price_history": row["price_history"],
            "web_slug": row["web_slug"],
            "image_url": row["image_url"],
            "location": row["location"],
            "seller_id": row["seller_id"],
            "published_date": row["published_date"] if "published_date" in row.keys() else None,
            "first_seen": row["first_seen"],
            "last_updated": row["last_updated"],
            "notified": bool(row["notified"]),
            "wallapop_url": f"https://es.wallapop.com/item/{row['web_slug']}" if row['web_slug'] else None
        }

    # ==================== CONFIG OPERATIONS ====================

    def get_config(self, key: str, default: str = "") -> str:
        """Get a config value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def set_config(self, key: str, value: str) -> None:
        """Set a config value."""
        now = datetime.utcnow().isoformat() + "Z"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))

    def get_all_config(self) -> Dict[str, str]:
        """Get all config values."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}
