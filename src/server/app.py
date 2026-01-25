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
    version="3.0.0"
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


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print(f"")
    print(f"  FerWallBot v3.0")
    print(f"  ===============")
    print(f"  Environment: {ENV}")
    print(f"  Data directory: {DATA_DIR}")
    print(f"")
    print(f"  Web UI:  http://{HOST}:{PORT}")
    print(f"  API:     http://{HOST}:{PORT}/api/v1")
    print(f"  Swagger: http://{HOST}:{PORT}/docs")
    print(f"")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("Shutting down Wallbot server...")


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
