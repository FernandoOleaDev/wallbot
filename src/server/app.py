"""
Wallbot HTTP Server - FastAPI Application

Run with:
    python -m server.app

Or:
    uvicorn src.server.app:app --host 0.0.0.0 --port 9500 --reload
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from server.api.routes import router as api_router
from server.web.views import router as web_router

# Configuration
HOST = os.getenv("WALLBOT_HOST", "0.0.0.0")
PORT = int(os.getenv("WALLBOT_PORT", "9500"))
ENV = os.getenv("WALLBOT_ENV", "development")
DATA_DIR = os.getenv("WALLBOT_DATA_DIR", "./data")

# Ensure data directories exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(f"{DATA_DIR}/cache").mkdir(parents=True, exist_ok=True)
Path(f"{DATA_DIR}/renders").mkdir(parents=True, exist_ok=True)
Path(f"{DATA_DIR}/logs").mkdir(parents=True, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="FerWallBot API",
    description="Monitor de busquedas en Wallapop con renderizado de imagenes para ESP32",
    version="0.17.0"
)

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Include routers
app.include_router(api_router)
app.include_router(web_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - Web UI."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Wallbot"}
    )


def on_new_item_callback(search: dict, item: dict):
    """Called when watcher finds a new item - regenerate image."""
    from server.renderer import get_renderer
    from server.database import get_db

    renderer = get_renderer()
    db = get_db()

    # Get the latest item (which should be the one just added)
    latest = db.get_latest_item(search["id"])

    # Render and cache the image
    if latest:
        image_bytes = renderer.render_search_latest(search, latest)
        renderer.save_render(search["id"], image_bytes)
        print(f"  [Watcher] New item found: {item.get('title', 'N/A')[:40]} - Image rendered")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    from server.wallapop.watcher import get_watcher

    print(f"")
    print(f"  FerWallBot v0.17")
    print(f"  ===============")
    print(f"  Environment: {ENV}")
    print(f"  Data directory: {DATA_DIR}")
    print(f"")
    print(f"  Web UI:  http://{HOST}:{PORT}")
    print(f"  API:     http://{HOST}:{PORT}/api/v1")
    print(f"  Swagger: http://{HOST}:{PORT}/docs")
    print(f"")

    # Start the watcher
    watcher = get_watcher()
    watcher.set_on_new_item_callback(on_new_item_callback)
    watcher.start()
    print(f"  [Watcher] Started (interval: {watcher.interval}s)")
    print(f"")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from server.wallapop.watcher import get_watcher

    print("Shutting down FerWallBot server...")
    watcher = get_watcher()
    watcher.stop()


def main():
    """Entry point for python -m server.app"""
    uvicorn.run(
        "server.app:app",
        host=HOST,
        port=PORT,
        reload=(ENV == "development")
    )


if __name__ == "__main__":
    main()
