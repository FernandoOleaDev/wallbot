"""Web UI views."""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from server.database import get_db

router = APIRouter(tags=["web"])

templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def parse_euro_to_cents(value: Optional[str]) -> Optional[int]:
    """Convert euro string (e.g., '89,50' or '89.50') to cents integer."""
    if not value or not value.strip():
        return None
    # Replace comma with dot for float parsing
    value = value.strip().replace(',', '.')
    try:
        euros = float(value)
        return int(euros * 100)
    except ValueError:
        return None


@router.get("/searches/new", response_class=HTMLResponse)
async def new_search_form(request: Request):
    """Form to create a new search."""
    return templates.TemplateResponse(
        "search_form.html",
        {"request": request, "title": "Nueva Busqueda", "search": None, "edit_mode": False}
    )


@router.post("/searches/new")
async def create_search_form(
    request: Request,
    name: str = Form(...),
    keywords: str = Form(...),
    min_price: Optional[str] = Form(None),
    max_price: Optional[str] = Form(None),
    category_ids: Optional[str] = Form(None),
    distance: int = Form(400),
    all_spain: Optional[str] = Form(None),
    required_words: Optional[str] = Form(None)
):
    """Handle form submission to create search."""
    db = get_db()

    # Handle "Toda Espana" toggle
    if all_spain == "on":
        distance = 0

    # Parse prices (euros to cents)
    min_price_int = parse_euro_to_cents(min_price)
    max_price_int = parse_euro_to_cents(max_price)

    # Clean category_ids and required_words
    category_ids_clean = category_ids.strip() if category_ids and category_ids.strip() else None
    required_words_clean = required_words.strip() if required_words and required_words.strip() else None

    db.create_search(
        name=name,
        keywords=keywords,
        min_price=min_price_int,
        max_price=max_price_int,
        category_ids=category_ids_clean,
        distance=distance,
        active=True,
        required_words=required_words_clean
    )

    return RedirectResponse(url="/", status_code=303)


@router.get("/searches/{search_id}/edit", response_class=HTMLResponse)
async def edit_search_form(request: Request, search_id: int):
    """Form to edit an existing search."""
    db = get_db()
    search = db.get_search(search_id)

    if not search:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    return templates.TemplateResponse(
        "search_form.html",
        {"request": request, "title": "Editar Busqueda", "search": search, "edit_mode": True}
    )


@router.post("/searches/{search_id}/edit")
async def update_search_form(
    request: Request,
    search_id: int,
    name: str = Form(...),
    keywords: str = Form(...),
    min_price: Optional[str] = Form(None),
    max_price: Optional[str] = Form(None),
    category_ids: Optional[str] = Form(None),
    distance: int = Form(400),
    all_spain: Optional[str] = Form(None),
    reset_items: Optional[str] = Form(None),
    required_words: Optional[str] = Form(None)
):
    """Handle form submission to update search."""
    db = get_db()

    existing = db.get_search(search_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    # Handle "Toda Espana" toggle
    if all_spain == "on":
        distance = 0

    # Parse prices (euros to cents)
    min_price_int = parse_euro_to_cents(min_price)
    max_price_int = parse_euro_to_cents(max_price)

    # Clean category_ids and required_words
    category_ids_clean = category_ids.strip() if category_ids and category_ids.strip() else None
    required_words_clean = required_words.strip() if required_words and required_words.strip() else None

    # Reset items if requested
    if reset_items == "on":
        db.delete_items_for_search(search_id)
        db.update_search(search_id, last_item_id=None)

    db.update_search(
        search_id,
        name=name,
        keywords=keywords,
        min_price=min_price_int,
        max_price=max_price_int,
        category_ids=category_ids_clean,
        distance=distance,
        required_words=required_words_clean
    )

    # Invalidate cached render so image regenerates with new parameters
    from server.renderer import get_renderer
    import os
    renderer = get_renderer()
    cache_path = renderer.renders_dir / f"search_{search_id}.jpg"
    if cache_path.exists():
        os.remove(cache_path)

    return RedirectResponse(url="/", status_code=303)


@router.post("/searches/{search_id}/delete")
async def delete_search_form(request: Request, search_id: int):
    """Handle search deletion from web UI."""
    db = get_db()
    db.delete_search(search_id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/searches/{search_id}/toggle")
async def toggle_search_active(request: Request, search_id: int):
    """Toggle search active/inactive state."""
    db = get_db()
    search = db.get_search(search_id)

    if search:
        db.update_search(search_id, active=not search["active"])

    return RedirectResponse(url="/", status_code=303)


@router.get("/searches/{search_id}/preview", response_class=HTMLResponse)
async def preview_search(request: Request, search_id: int):
    """Preview the rendered image for a search."""
    db = get_db()
    search = db.get_search(search_id)

    if not search:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    latest_item = db.get_latest_item(search_id)

    return templates.TemplateResponse(
        "search_preview.html",
        {
            "request": request,
            "title": "Preview ESP32",
            "search": search,
            "search_id": search_id,
            "latest_item": latest_item
        }
    )


@router.get("/screen", response_class=HTMLResponse)
async def screen_view(request: Request):
    """Live view of ESP32 screen with rotation status."""
    return templates.TemplateResponse(
        "screen.html",
        {"request": request, "title": "Pantalla ESP32"}
    )


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page."""
    db = get_db()
    config = {
        "search_interval": int(db.get_config("search_interval", "300")),
        "rotation_interval": int(db.get_config("rotation_interval", "10")),
        "items_count": int(db.get_config("items_count", "20")),
        "time_filter": db.get_config("time_filter", "all")
    }
    return templates.TemplateResponse(
        "config.html",
        {"request": request, "title": "Configuracion", "config": config}
    )


@router.post("/config")
async def save_config(
    request: Request,
    search_interval: int = Form(...),
    rotation_interval: int = Form(...),
    items_count: int = Form(...),
    time_filter: str = Form(...)
):
    """Save configuration changes."""
    from server.wallapop.watcher import get_watcher
    from server.screen_rotator import get_rotator

    db = get_db()

    # Validate and clamp values
    search_interval = max(60, min(3600, search_interval))
    rotation_interval = max(5, min(300, rotation_interval))
    items_count = max(5, min(100, items_count))

    # Validate time_filter
    if time_filter not in ("today", "week", "all"):
        time_filter = "all"

    # Save to database
    db.set_config("search_interval", str(search_interval))
    db.set_config("rotation_interval", str(rotation_interval))
    db.set_config("items_count", str(items_count))
    db.set_config("time_filter", time_filter)

    # Update running services
    watcher = get_watcher()
    watcher.interval = search_interval

    rotator = get_rotator()
    rotator.rotation_interval = rotation_interval

    return RedirectResponse(url="/config?saved=1", status_code=303)
