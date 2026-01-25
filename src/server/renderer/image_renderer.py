"""Image renderer for ESP32 TFT screen (128x160 pixels)."""
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Screen dimensions
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 160

# Layout
IMAGE_HEIGHT = 100
INFO_HEIGHT = 60

# Colors
BG_COLOR = (26, 26, 46)  # Dark blue background
TEXT_COLOR = (255, 255, 255)  # White text
PRICE_COLOR = (19, 193, 172)  # Teal/cyan for price
SECONDARY_COLOR = (150, 150, 150)  # Gray for secondary text

# Global renderer instance
_renderer_instance: Optional['ImageRenderer'] = None


def get_renderer() -> 'ImageRenderer':
    """Get the global renderer instance."""
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = ImageRenderer()
    return _renderer_instance


class ImageRenderer:
    """Renders item data to 128x160 JPG images for ESP32 TFT screen."""

    def __init__(self):
        self.data_dir = Path(os.getenv("WALLBOT_DATA_DIR", "./data"))
        self.renders_dir = self.data_dir / "renders"
        self.renders_dir.mkdir(parents=True, exist_ok=True)
        self.font_regular = self._load_font(12)
        self.font_small = self._load_font(10)
        self.font_price = self._load_font(16)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load a font, falling back to default if not available."""
        # Try to load a nice font, fall back to default
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue

        # Fall back to default font
        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def render_item(self, item: Dict[str, Any], search_name: str = "") -> bytes:
        """Render an item to a JPG image.

        Args:
            item: Item data with title, price, image_url, location
            search_name: Optional search name to display

        Returns:
            JPG image as bytes
        """
        # Create base image
        img = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Draw product image (top section)
        product_img = self._fetch_and_resize_image(item.get("image_url"))
        if product_img:
            # Center the product image
            x_offset = (SCREEN_WIDTH - product_img.width) // 2
            img.paste(product_img, (x_offset, 0))
        else:
            # No image - draw placeholder
            draw.rectangle([0, 0, SCREEN_WIDTH, IMAGE_HEIGHT], fill=(40, 40, 60))
            draw.text((SCREEN_WIDTH // 2, IMAGE_HEIGHT // 2), "Sin imagen",
                     fill=SECONDARY_COLOR, anchor="mm", font=self.font_small)

        # Draw info section (bottom)
        y_pos = IMAGE_HEIGHT + 5

        # Price (big, colored) + status icons
        price = item.get("price", 0)
        price_text = f"{price / 100:.0f} EUR" if price else "N/A"

        # Add status indicators
        status_icons = ""
        if item.get("reserved"):
            status_icons += "[R] "
        if item.get("has_shipping"):
            status_icons += "[E] "

        if status_icons:
            # Draw status icons in different colors
            x_pos = 4
            if item.get("reserved"):
                draw.text((x_pos, y_pos), "[R]", fill=(239, 68, 68), font=self.font_small)
                x_pos += 22
            if item.get("has_shipping"):
                draw.text((x_pos, y_pos), "[E]", fill=(59, 130, 246), font=self.font_small)
                x_pos += 22
            draw.text((x_pos, y_pos), price_text, fill=PRICE_COLOR, font=self.font_price)
        else:
            draw.text((4, y_pos), price_text, fill=PRICE_COLOR, font=self.font_price)
        y_pos += 20

        # Title (truncated, smaller font for more text)
        title = item.get("title", "Sin titulo")
        title = self._truncate_text(title, SCREEN_WIDTH - 8, self.font_small)
        draw.text((4, y_pos), title, fill=TEXT_COLOR, font=self.font_small)
        y_pos += 12

        # Location + Date on same line
        location = item.get("location", "")
        date_str = self._get_most_recent_date_str(item)

        if location and date_str:
            loc_date = f"{location} · {date_str}"
        elif location:
            loc_date = location
        elif date_str:
            loc_date = date_str
        else:
            loc_date = ""

        if loc_date:
            loc_date = self._truncate_text(loc_date, SCREEN_WIDTH - 8, self.font_small)
            draw.text((4, y_pos), loc_date, fill=SECONDARY_COLOR, font=self.font_small)

        # Convert to JPG bytes
        return self._image_to_jpg_bytes(img)

    def render_search_latest(self, search: Dict[str, Any], latest_item: Optional[Dict[str, Any]]) -> bytes:
        """Render the latest item from a search.

        Args:
            search: Search data
            latest_item: Latest item or None

        Returns:
            JPG image as bytes
        """
        if latest_item:
            return self.render_item(latest_item, search.get("name", ""))
        else:
            return self.render_no_items(search.get("name", "Busqueda"))

    def render_no_items(self, search_name: str = "") -> bytes:
        """Render a 'no items' placeholder image."""
        img = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Draw search name at top
        if search_name:
            name = self._truncate_text(search_name, SCREEN_WIDTH - 8, self.font_regular)
            draw.text((SCREEN_WIDTH // 2, 20), name, fill=PRICE_COLOR,
                     anchor="mm", font=self.font_regular)

        # Draw "no items" message
        draw.text((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), "Sin items",
                 fill=TEXT_COLOR, anchor="mm", font=self.font_price)
        draw.text((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25), "Esperando...",
                 fill=SECONDARY_COLOR, anchor="mm", font=self.font_small)

        return self._image_to_jpg_bytes(img)

    def render_error(self, message: str = "Error") -> bytes:
        """Render an error placeholder image."""
        img = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (60, 20, 20))
        draw = ImageDraw.Draw(img)

        draw.text((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), "ERROR",
                 fill=(255, 100, 100), anchor="mm", font=self.font_price)

        msg = self._truncate_text(message, SCREEN_WIDTH - 8, self.font_small)
        draw.text((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25), msg,
                 fill=SECONDARY_COLOR, anchor="mm", font=self.font_small)

        return self._image_to_jpg_bytes(img)

    def _fetch_and_resize_image(self, url: Optional[str]) -> Optional[Image.Image]:
        """Fetch image from URL and resize for display."""
        if not url:
            return None

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            img = Image.open(io.BytesIO(response.content))
            img = img.convert('RGB')

            # Resize to fit width while maintaining aspect ratio
            ratio = SCREEN_WIDTH / img.width
            new_height = int(img.height * ratio)

            # If too tall, resize by height instead
            if new_height > IMAGE_HEIGHT:
                ratio = IMAGE_HEIGHT / img.height
                new_width = int(img.width * ratio)
                new_height = IMAGE_HEIGHT
            else:
                new_width = SCREEN_WIDTH

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Create a centered image on the correct dimensions
            final = Image.new('RGB', (SCREEN_WIDTH, IMAGE_HEIGHT), BG_COLOR)
            x_offset = (SCREEN_WIDTH - new_width) // 2
            y_offset = (IMAGE_HEIGHT - new_height) // 2
            final.paste(img, (x_offset, y_offset))

            return final

        except Exception as e:
            logger.warning(f"Failed to fetch image from {url}: {e}")
            return None

    def _get_most_recent_date_str(self, item: Dict[str, Any]) -> str:
        """Get formatted string for most recent date (created or modified)."""
        published = item.get("published_date")
        modified = item.get("modified_at")

        # Find most recent date
        dates = []
        if published:
            dates.append(("Creado", published))
        if modified:
            dates.append(("Editado", modified))

        if not dates:
            return ""

        # Get the most recent one
        most_recent = max(dates, key=lambda x: x[1])
        label, date_str = most_recent

        # Format the date
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
            diff = now - dt

            days = diff.days
            hours = diff.seconds // 3600
            mins = diff.seconds // 60

            if days == 0:
                if hours == 0:
                    time_str = f"{mins}m"
                else:
                    time_str = f"{hours}h"
            elif days == 1:
                time_str = "ayer"
            elif days < 7:
                time_str = f"{days}d"
            else:
                time_str = dt.strftime("%d/%m")

            return f"{label}: {time_str}"
        except Exception:
            return ""

    def _truncate_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
        """Truncate text to fit within max_width pixels."""
        if not text:
            return ""

        # Get text width
        try:
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
        except Exception:
            # Fallback estimation
            text_width = len(text) * 7

        if text_width <= max_width:
            return text

        # Binary search for the right length
        while text_width > max_width and len(text) > 3:
            text = text[:-4] + "..."
            try:
                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
            except Exception:
                text_width = len(text) * 7

        return text

    def _image_to_jpg_bytes(self, img: Image.Image, quality: int = 85) -> bytes:
        """Convert PIL Image to JPG bytes."""
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()

    def save_render(self, search_id: int, image_bytes: bytes) -> Path:
        """Save rendered image to disk cache."""
        filepath = self.renders_dir / f"search_{search_id}.jpg"
        filepath.write_bytes(image_bytes)
        return filepath

    def get_cached_render(self, search_id: int) -> Optional[bytes]:
        """Get cached render if it exists."""
        filepath = self.renders_dir / f"search_{search_id}.jpg"
        if filepath.exists():
            return filepath.read_bytes()
        return None
