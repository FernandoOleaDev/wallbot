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
        is_large_screen = width >= 320 and height >= 480

        # Create base image
        img = Image.new('RGB', (width, height), BG_COLOR)
        draw = ImageDraw.Draw(img)

        if is_large_screen:
            # === LARGE SCREEN LAYOUT (320x480) ===
            self._render_large_screen(img, draw, item, fonts, width, height)
        else:
            # === SMALL/MEDIUM SCREEN LAYOUT ===
            self._render_small_screen(img, draw, item, fonts, width, height, scale)

        # Convert to JPG bytes
        return self._image_to_jpg_bytes(img)

    def _render_large_screen(self, img: Image.Image, draw: ImageDraw.Draw,
                              item: Dict[str, Any], fonts: Dict, width: int, height: int):
        """Render layout for large screens (320x480) with QR code."""
        # Layout constants for 320x480
        PADDING = 12
        IMAGE_H = 200
        QR_SIZE = 80
        QR_SECTION_H = 100

        # Colors
        ACCENT = (19, 193, 172)  # Teal

        # === 1. PRODUCT IMAGE (top) ===
        product_img = self._fetch_and_resize_image(item.get("image_url"), width, IMAGE_H)
        if product_img:
            x_offset = (width - product_img.width) // 2
            img.paste(product_img, (x_offset, 0))
        else:
            draw.rectangle([0, 0, width, IMAGE_H], fill=(35, 35, 55))
            draw.text((width // 2, IMAGE_H // 2), "Sin imagen",
                     fill=SECONDARY_COLOR, anchor="mm", font=fonts["title"])

        # === 2. INFO SECTION (middle) ===
        info_top = IMAGE_H + PADDING
        info_bottom = height - QR_SECTION_H
        text_width = width - (PADDING * 2)

        y = info_top

        # Price row: [R] [E] 450 EUR
        price = item.get("price", 0)
        price_text = f"{price / 100:.0f} EUR" if price else "Gratis"

        # Draw price large
        price_font = self._load_font(32)
        draw.text((PADDING, y), price_text, fill=ACCENT, font=price_font)

        # Status badges to the right of price
        price_bbox = price_font.getbbox(price_text)
        badge_x = PADDING + price_bbox[2] + 12

        badge_font = self._load_font(14)
        if item.get("has_shipping"):
            draw.rounded_rectangle([badge_x, y + 6, badge_x + 50, y + 26],
                                   radius=4, fill=(30, 64, 120))
            draw.text((badge_x + 25, y + 16), "Envío", fill=(100, 160, 255),
                     anchor="mm", font=badge_font)
            badge_x += 58
        if item.get("reserved"):
            draw.rounded_rectangle([badge_x, y + 6, badge_x + 70, y + 26],
                                   radius=4, fill=(100, 30, 30))
            draw.text((badge_x + 35, y + 16), "Reservado", fill=(255, 120, 120),
                     anchor="mm", font=badge_font)

        y += 44

        # Title (multiple lines)
        title = item.get("title", "Sin título")
        title_font = self._load_font(18)
        title_lines = self._wrap_text(title, text_width, title_font)

        for line in title_lines[:2]:  # Max 2 lines for title
            if y > info_bottom - 70:
                break
            draw.text((PADDING, y), line, fill=TEXT_COLOR, font=title_font)
            y += 24

        # Description (if available)
        description = item.get("description", "")
        if description:
            y += 4
            desc_font = self._load_font(13)
            desc_lines = self._wrap_text(description, text_width, desc_font)
            desc_color = (180, 180, 180)  # Lighter gray for description

            for line in desc_lines[:2]:  # Max 2 lines for description
                if y > info_bottom - 30:
                    break
                draw.text((PADDING, y), line, fill=desc_color, font=desc_font)
                y += 18

        # Location and date
        y += 4
        location = item.get("location", "")
        date_str = self._get_most_recent_date_str(item)
        meta_font = self._load_font(14)

        if location:
            loc_text = self._truncate_text(location, text_width - 100, meta_font)
            draw.text((PADDING, y), f"📍 {loc_text}", fill=SECONDARY_COLOR, font=meta_font)

        if date_str:
            draw.text((width - PADDING, y), date_str, fill=SECONDARY_COLOR,
                     anchor="ra", font=meta_font)

        # === 3. QR SECTION (bottom) ===
        qr_section_top = height - QR_SECTION_H

        # Separator line
        draw.line([(PADDING, qr_section_top), (width - PADDING, qr_section_top)],
                 fill=(50, 50, 70), width=1)

        wallapop_url = item.get("wallapop_url")
        if wallapop_url:
            qr_img = self._generate_qr_code(wallapop_url, QR_SIZE)
            if qr_img:
                # QR on the right
                qr_x = width - PADDING - QR_SIZE
                qr_y = qr_section_top + (QR_SECTION_H - QR_SIZE) // 2
                img.paste(qr_img, (qr_x, qr_y))

                # Text on the left of QR
                text_x = PADDING
                text_y = qr_section_top + QR_SECTION_H // 2

                cta_font = self._load_font(16)
                small_font = self._load_font(12)

                draw.text((text_x, text_y - 12), "Abrir en Wallapop",
                         fill=TEXT_COLOR, font=cta_font)
                draw.text((text_x, text_y + 10), "Escanea el código QR",
                         fill=SECONDARY_COLOR, font=small_font)

    def _render_small_screen(self, img: Image.Image, draw: ImageDraw.Draw,
                              item: Dict[str, Any], fonts: Dict,
                              width: int, height: int, scale: float):
        """Render layout for small/medium screens (128x160, 240x320)."""
        padding = int(4 * scale)
        image_height = int(height * IMAGE_HEIGHT_RATIO)
        line_spacing = int(12 * scale)
        price_spacing = int(20 * scale)
        text_max_width = width - (padding * 2)

        # Product image
        product_img = self._fetch_and_resize_image(item.get("image_url"), width, image_height)
        if product_img:
            x_offset = (width - product_img.width) // 2
            img.paste(product_img, (x_offset, 0))
        else:
            draw.rectangle([0, 0, width, image_height], fill=(40, 40, 60))
            draw.text((width // 2, image_height // 2), "Sin imagen",
                     fill=SECONDARY_COLOR, anchor="mm", font=fonts["small"])

        y_pos = image_height + padding

        # Price + status icons
        price = item.get("price", 0)
        price_text = f"{price / 100:.0f} EUR" if price else "N/A"

        icon_spacing = int(22 * scale)
        x_pos = padding
        if item.get("reserved"):
            draw.text((x_pos, y_pos), "[R]", fill=(239, 68, 68), font=fonts["small"])
            x_pos += icon_spacing
        if item.get("has_shipping"):
            draw.text((x_pos, y_pos), "[E]", fill=(59, 130, 246), font=fonts["small"])
            x_pos += icon_spacing
        draw.text((x_pos, y_pos), price_text, fill=PRICE_COLOR, font=fonts["price"])
        y_pos += price_spacing

        # Title
        title = item.get("title", "Sin titulo")
        title_line1 = self._truncate_text(title, text_max_width, fonts["small"])
        draw.text((padding, y_pos), title_line1, fill=TEXT_COLOR, font=fonts["small"])
        y_pos += line_spacing

        if width >= 240 and len(title) > len(title_line1.replace("...", "")):
            remaining = title[len(title_line1.replace("...", "")):]
            if remaining:
                remaining = self._truncate_text(remaining.strip(), text_max_width, fonts["small"])
                draw.text((padding, y_pos), remaining, fill=TEXT_COLOR, font=fonts["small"])
                y_pos += line_spacing

        # Location + Date
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
            loc_date = self._truncate_text(loc_date, text_max_width, fonts["small"])
            draw.text((padding, y_pos), loc_date, fill=SECONDARY_COLOR, font=fonts["small"])

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

    def _wrap_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> list:
        """Wrap text into multiple lines that fit within max_width pixels.

        Args:
            text: Text to wrap
            max_width: Maximum width in pixels per line
            font: Font to use for measuring

        Returns:
            List of text lines
        """
        if not text:
            return []

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except Exception:
                text_width = len(test_line) * 8

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

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
