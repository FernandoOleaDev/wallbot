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
    all_spain: Optional[str] = Form(None)
):
    """Handle form submission to create search."""
    db = get_db()

    # Handle "Toda Espana" toggle
    if all_spain == "on":
        distance = 0

    # Parse prices (convert empty strings to None)
    min_price_int = int(min_price) if min_price and min_price.strip() else None
    max_price_int = int(max_price) if max_price and max_price.strip() else None

    # Clean category_ids
    category_ids_clean = category_ids.strip() if category_ids and category_ids.strip() else None

    db.create_search(
        name=name,
        keywords=keywords,
        min_price=min_price_int,
        max_price=max_price_int,
        category_ids=category_ids_clean,
        distance=distance,
        active=True
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
    all_spain: Optional[str] = Form(None)
):
    """Handle form submission to update search."""
    db = get_db()

    existing = db.get_search(search_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    # Handle "Toda Espana" toggle
    if all_spain == "on":
        distance = 0

    # Parse prices
    min_price_int = int(min_price) if min_price and min_price.strip() else None
    max_price_int = int(max_price) if max_price and max_price.strip() else None

    # Clean category_ids
    category_ids_clean = category_ids.strip() if category_ids and category_ids.strip() else None

    db.update_search(
        search_id,
        name=name,
        keywords=keywords,
        min_price=min_price_int,
        max_price=max_price_int,
        category_ids=category_ids_clean,
        distance=distance
    )

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
