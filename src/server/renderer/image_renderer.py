"""Image renderer for ESP32 TFT screens (128x160, 240x320, 320x480 pixels)."""
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Default screen dimensions (ST7735 128x160)
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 160

# Layout ratios (for scaling)
IMAGE_HEIGHT_RATIO = 0.625  # 100/160 = 62.5% for image
INFO_HEIGHT_RATIO = 0.375   # 60/160 = 37.5% for info

# Supported screen sizes
SCREEN_SIZES = {
    "small": (128, 160),   # ST7735 (ESP32-CAM)
    "medium": (240, 320),  # ILI9341 (Freenove ESP32-S3)
    "large": (320, 480),   # ILI9488
}

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
    """Renders item data to JPG images for ESP32 TFT screens (multiple sizes supported)."""

    def __init__(self):
        self.data_dir = Path(os.getenv("WALLBOT_DATA_DIR", "./data"))
        self.renders_dir = self.data_dir / "renders"
        self.renders_dir.mkdir(parents=True, exist_ok=True)
        # Default fonts for 128x160
        self.font_regular = self._load_font(12)
        self.font_small = self._load_font(10)
        self.font_price = self._load_font(16)
        # Fonts cache for different sizes
        self._fonts_cache: Dict[Tuple[int, int], Dict[str, ImageFont.FreeTypeFont]] = {}

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

    def _get_fonts_for_size(self, width: int, height: int) -> Dict[str, ImageFont.FreeTypeFont]:
        """Get appropriately scaled fonts for given screen size."""
        key = (width, height)
        if key in self._fonts_cache:
            return self._fonts_cache[key]

        # Calculate scale factor based on screen height (160 is the base)
        scale = height / 160

        fonts = {
            "regular": self._load_font(int(12 * scale)),
            "small": self._load_font(int(10 * scale)),
            "price": self._load_font(int(16 * scale)),
            "title": self._load_font(int(14 * scale)),
        }
        self._fonts_cache[key] = fonts
        return fonts

    def render_item(self, item: Dict[str, Any], search_name: str = "",
                    width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT) -> bytes:
        """Render an item to a JPG image.

        Args:
            item: Item data with title, price, image_url, location
            search_name: Optional search name to display
            width: Screen width (default 128)
            height: Screen height (default 160)

        Returns:
            JPG image as bytes
        """
        # Get fonts scaled for this screen size
        fonts = self._get_fonts_for_size(width, height)
        scale = height / 160

        # Calculate layout dimensions
        image_height = int(height * IMAGE_HEIGHT_RATIO)
        padding = int(4 * scale)
        line_spacing = int(12 * scale)
        price_spacing = int(20 * scale)

        # Create base image
        img = Image.new('RGB', (width, height), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Draw product image (top section)
        product_img = self._fetch_and_resize_image(item.get("image_url"), width, image_height)
        if product_img:
            # Center the product image
            x_offset = (width - product_img.width) // 2
            img.paste(product_img, (x_offset, 0))
        else:
            # No image - draw placeholder
            draw.rectangle([0, 0, width, image_height], fill=(40, 40, 60))
            draw.text((width // 2, image_height // 2), "Sin imagen",
                     fill=SECONDARY_COLOR, anchor="mm", font=fonts["small"])

        # Draw info section (bottom)
        y_pos = image_height + padding

        # Price (big, colored) + status icons
        price = item.get("price", 0)
        price_text = f"{price / 100:.0f} EUR" if price else "N/A"

        # Add status indicators
        status_icons = ""
        if item.get("reserved"):
            status_icons += "[R] "
        if item.get("has_shipping"):
            status_icons += "[E] "

        icon_spacing = int(22 * scale)
        if status_icons:
            # Draw status icons in different colors
            x_pos = padding
            if item.get("reserved"):
                draw.text((x_pos, y_pos), "[R]", fill=(239, 68, 68), font=fonts["small"])
                x_pos += icon_spacing
            if item.get("has_shipping"):
                draw.text((x_pos, y_pos), "[E]", fill=(59, 130, 246), font=fonts["small"])
                x_pos += icon_spacing
            draw.text((x_pos, y_pos), price_text, fill=PRICE_COLOR, font=fonts["price"])
        else:
            draw.text((padding, y_pos), price_text, fill=PRICE_COLOR, font=fonts["price"])
        y_pos += price_spacing

        # Title (truncated)
        title = item.get("title", "Sin titulo")
        title = self._truncate_text(title, width - (padding * 2), fonts["small"])
        draw.text((padding, y_pos), title, fill=TEXT_COLOR, font=fonts["small"])
        y_pos += line_spacing

        # Second line of title for larger screens
        if width >= 240 and len(item.get("title", "")) > 30:
            remaining = item.get("title", "")[len(title.replace("...", "")):]
            if remaining:
                remaining = self._truncate_text(remaining.strip(), width - (padding * 2), fonts["small"])
                draw.text((padding, y_pos), remaining, fill=TEXT_COLOR, font=fonts["small"])
                y_pos += line_spacing

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
            loc_date = self._truncate_text(loc_date, width - (padding * 2), fonts["small"])
            draw.text((padding, y_pos), loc_date, fill=SECONDARY_COLOR, font=fonts["small"])
            y_pos += line_spacing

        # QR Code for large screens (320x480 or bigger)
        if width >= 320 and height >= 480:
            wallapop_url = item.get("wallapop_url")
            if wallapop_url:
                qr_size = int(70 * scale)
                qr_img = self._generate_qr_code(wallapop_url, qr_size)
                if qr_img:
                    # Position QR in bottom-right, with label above
                    qr_x = width - qr_size - padding
                    qr_y = height - qr_size - padding
                    img.paste(qr_img, (qr_x, qr_y))
                    # Label above QR
                    label_y = qr_y - int(14 * scale)
                    draw.text((qr_x + qr_size // 2, label_y), "Abrir en",
                             fill=SECONDARY_COLOR, anchor="mm", font=fonts["small"])

        # Convert to JPG bytes
        return self._image_to_jpg_bytes(img)

    def render_search_latest(self, search: Dict[str, Any], latest_item: Optional[Dict[str, Any]],
                             width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT) -> bytes:
        """Render the latest item from a search.

        Args:
            search: Search data
            latest_item: Latest item or None
            width: Screen width (default 128)
            height: Screen height (default 160)

        Returns:
            JPG image as bytes
        """
        if latest_item:
            return self.render_item(latest_item, search.get("name", ""), width, height)
        else:
            return self.render_no_items(search.get("name", "Busqueda"), width, height)

    def render_no_items(self, search_name: str = "",
                        width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT) -> bytes:
        """Render a 'no items' placeholder image."""
        fonts = self._get_fonts_for_size(width, height)
        scale = height / 160

        img = Image.new('RGB', (width, height), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Draw search name at top
        if search_name:
            name = self._truncate_text(search_name, width - 8, fonts["regular"])
            draw.text((width // 2, int(20 * scale)), name, fill=PRICE_COLOR,
                     anchor="mm", font=fonts["regular"])

        # Draw "no items" message
        draw.text((width // 2, height // 2), "Sin items",
                 fill=TEXT_COLOR, anchor="mm", font=fonts["price"])
        draw.text((width // 2, height // 2 + int(25 * scale)), "Esperando...",
                 fill=SECONDARY_COLOR, anchor="mm", font=fonts["small"])

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

    def _fetch_and_resize_image(self, url: Optional[str],
                                target_width: int = SCREEN_WIDTH,
                                target_height: int = IMAGE_HEIGHT) -> Optional[Image.Image]:
        """Fetch image from URL and resize for display.

        Args:
            url: Image URL to fetch
            target_width: Target width for the image area
            target_height: Target height for the image area

        Returns:
            Resized PIL Image or None
        """
        if not url:
            return None

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            img = Image.open(io.BytesIO(response.content))
            img = img.convert('RGB')

            # Resize to fit width while maintaining aspect ratio
            ratio = target_width / img.width
            new_height = int(img.height * ratio)

            # If too tall, resize by height instead
            if new_height > target_height:
                ratio = target_height / img.height
                new_width = int(img.width * ratio)
                new_height = target_height
            else:
                new_width = target_width

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Create a centered image on the correct dimensions
            final = Image.new('RGB', (target_width, target_height), BG_COLOR)
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
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

    def _generate_qr_code(self, url: str, size: int) -> Optional[Image.Image]:
        """Generate a QR code image for the given URL.

        Args:
            url: URL to encode in the QR code
            size: Target size in pixels (width and height)

        Returns:
            PIL Image with QR code or None if generation fails
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=2,
                border=1,
            )
            qr.add_data(url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="white", back_color=BG_COLOR)
            qr_img = qr_img.convert('RGB')
            qr_img = qr_img.resize((size, size), Image.Resampling.NEAREST)
            return qr_img
        except Exception as e:
            logger.warning(f"Failed to generate QR code: {e}")
            return None

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
