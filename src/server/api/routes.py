"""API v1 routes."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import time
import os

from server.database import get_db

router = APIRouter(prefix="/api/v1", tags=["api"])

# Track server start time for uptime
_start_time = time.time()


# ==================== MODELS ====================

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    database: str
    watcher: str


class SearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    keywords: str = Field(..., min_length=1, max_length=200)
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)
    category_ids: Optional[str] = None
    distance: int = Field(400, ge=0, le=500)
    active: bool = True
    exclude_reserved: bool = False


class SearchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    keywords: Optional[str] = Field(None, min_length=1, max_length=200)
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)
    category_ids: Optional[str] = None
    distance: Optional[int] = Field(None, ge=0, le=500)
    active: Optional[bool] = None
    exclude_reserved: Optional[bool] = None


class SearchResponse(BaseModel):
    id: int
    name: str
    keywords: str
    min_price: Optional[int]
    max_price: Optional[int]
    category_ids: Optional[str]
    distance: int
    order_by: str
    active: bool
    exclude_reserved: bool = False
    last_item_id: Optional[str]
    items_count: int = 0
    created_at: str
    updated_at: str


class SearchListResponse(BaseModel):
    searches: List[SearchResponse]
    total: int


class ItemResponse(BaseModel):
    id: int
    wallapop_id: str
    title: Optional[str]
    price: Optional[int]
    price_formatted: Optional[str]
    price_history: Optional[str]
    web_slug: Optional[str]
    image_url: Optional[str]
    location: Optional[str]
    first_seen: str
    published_date: Optional[str]
    modified_at: Optional[str]
    reserved: bool = False
    has_shipping: bool = False
    wallapop_url: Optional[str]


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    limit: int
    offset: int


# ==================== ENDPOINTS ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    from server.wallapop.watcher import get_watcher

    uptime = int(time.time() - _start_time)
    db = get_db()
    db_status = "connected" if db else "disconnected"

    watcher = get_watcher()
    watcher_status = "running" if watcher.is_running else "stopped"

    return HealthResponse(
        status="ok",
        version="0.17.0",
        uptime_seconds=uptime,
        database=db_status,
        watcher=watcher_status
    )


@router.get("/searches", response_model=SearchListResponse)
async def list_searches(active: Optional[bool] = Query(None)):
    """List all searches."""
    db = get_db()
    active_only = active if active is not None else False
    searches = db.get_all_searches(active_only=active_only)

    return SearchListResponse(
        searches=[SearchResponse(**s) for s in searches],
        total=len(searches)
    )


@router.post("/searches", response_model=SearchResponse, status_code=201)
async def create_search(search: SearchCreate):
    """Create a new search."""
    # Validate price range
    if search.min_price and search.max_price:
        if search.min_price > search.max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price must be less than or equal to max_price"
            )

    db = get_db()
    result = db.create_search(
        name=search.name,
        keywords=search.keywords,
        min_price=search.min_price,
        max_price=search.max_price,
        category_ids=search.category_ids,
        distance=search.distance,
        active=search.active,
        exclude_reserved=search.exclude_reserved
    )

    return SearchResponse(**result)


@router.get("/searches/{search_id}", response_model=SearchResponse)
async def get_search(search_id: int):
    """Get a specific search by ID."""
    db = get_db()
    search = db.get_search(search_id)

    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    return SearchResponse(**search)


@router.put("/searches/{search_id}", response_model=SearchResponse)
async def update_search(search_id: int, search: SearchUpdate):
    """Update an existing search."""
    db = get_db()

    existing = db.get_search(search_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    # Build update dict with only provided fields
    updates = {k: v for k, v in search.model_dump().items() if v is not None}

    if not updates:
        return SearchResponse(**existing)

    result = db.update_search(search_id, **updates)
    return SearchResponse(**result)


@router.delete("/searches/{search_id}", status_code=204)
async def delete_search(search_id: int):
    """Delete a search and all its items."""
    db = get_db()

    if not db.delete_search(search_id):
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    return None


@router.get("/searches/{search_id}/items", response_model=ItemListResponse)
async def list_search_items(
    search_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List items found for a specific search."""
    db = get_db()

    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    items = db.get_items_for_search(search_id, limit=limit, offset=offset)
    total = db.get_items_count(search_id)

    # Format items
    formatted_items = []
    for item in items:
        price_formatted = None
        if item.get("price"):
            price_formatted = f"{item['price'] / 100:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")
        formatted_items.append(ItemResponse(
            id=item["id"],
            wallapop_id=item["wallapop_id"],
            title=item.get("title"),
            price=item.get("price"),
            price_formatted=price_formatted,
            price_history=item.get("price_history"),
            web_slug=item.get("web_slug"),
            image_url=item.get("image_url"),
            location=item.get("location"),
            first_seen=item.get("first_seen", ""),
            published_date=item.get("published_date"),
            modified_at=item.get("modified_at"),
            reserved=item.get("reserved", False),
            has_shipping=item.get("has_shipping", False),
            wallapop_url=item.get("wallapop_url")
        ))

    return ItemListResponse(
        items=formatted_items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/searches/{search_id}/latest", response_model=ItemResponse)
async def get_latest_item(search_id: int):
    """Get the latest item found for a search."""
    db = get_db()

    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    item = db.get_latest_item(search_id)
    if not item:
        raise HTTPException(status_code=404, detail="No items found for this search")

    price_formatted = None
    if item.get("price"):
        price_formatted = f"{item['price'] / 100:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

    return ItemResponse(
        id=item["id"],
        wallapop_id=item["wallapop_id"],
        title=item.get("title"),
        price=item.get("price"),
        price_formatted=price_formatted,
        price_history=item.get("price_history"),
        web_slug=item.get("web_slug"),
        image_url=item.get("image_url"),
        location=item.get("location"),
        first_seen=item.get("first_seen", ""),
        published_date=item.get("published_date"),
        modified_at=item.get("modified_at"),
        reserved=item.get("reserved", False),
        has_shipping=item.get("has_shipping", False),
        wallapop_url=item.get("wallapop_url")
    )


@router.get("/searches/{search_id}/screen.jpg")
async def get_screen_image(search_id: int):
    """Get the rendered 128x160 JPG image for ESP32."""
    from server.renderer import get_renderer

    db = get_db()

    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    renderer = get_renderer()

    # Check if rendered image exists in cache
    cached = renderer.get_cached_render(search_id)
    if cached:
        return Response(
            content=cached,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache"}
        )

    # Generate on-the-fly
    latest_item = db.get_latest_item(search_id)
    image_bytes = renderer.render_search_latest(search, latest_item)

    # Cache it
    renderer.save_render(search_id, image_bytes)

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache"}
    )


# ==================== ESP32 SCREEN ENDPOINTS ====================

@router.get("/screen.jpg")
async def get_esp32_screen(width: int = 128, height: int = 160):
    """Get the current screen image for ESP32.

    This is the main endpoint for ESP32 polling.
    The server automatically rotates between active searches.

    Args:
        width: Screen width in pixels (default 128 for ST7735, use 240 for ILI9341)
        height: Screen height in pixels (default 160 for ST7735, use 320 for ILI9341)
    """
    from server.screen_rotator import get_rotator
    from server.renderer import get_renderer

    # Clamp dimensions to reasonable values
    width = max(64, min(480, width))
    height = max(64, min(640, height))

    rotator = get_rotator()
    current = rotator.get_current_search()

    if not current:
        # No active searches - return placeholder
        renderer = get_renderer()
        image_bytes = renderer.render_no_items("Sin busquedas", width, height)
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

    renderer = get_renderer()
    db = get_db()

    # For non-default sizes, always generate fresh (don't use cache)
    # Cache is only for 128x160 default size
    if width == 128 and height == 160:
        cached = renderer.get_cached_render(current['id'])
        if cached:
            return Response(
                content=cached,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "X-Current-Search-Id": str(current["id"]),
                    "X-Current-Search-Name": current["name"]
                }
            )

    # Generate on-the-fly
    latest_item = db.get_latest_item(current['id'])
    image_bytes = renderer.render_search_latest(current, latest_item, width, height)

    # Only cache default size
    if width == 128 and height == 160:
        renderer.save_render(current['id'], image_bytes)

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Current-Search-Id": str(current["id"]),
            "X-Current-Search-Name": current["name"],
            "X-Screen-Size": f"{width}x{height}"
        }
    )


class ScreenStatusResponse(BaseModel):
    current_search_id: Optional[int]
    current_search_name: Optional[str]
    current_index: int
    total_active_searches: int
    rotation_interval_seconds: int
    seconds_until_next_rotation: int
    active_search_ids: List[int]


@router.get("/screen/status", response_model=ScreenStatusResponse)
async def get_screen_status():
    """Get current screen rotation status."""
    from server.screen_rotator import get_rotator

    rotator = get_rotator()
    status = rotator.get_status()
    return ScreenStatusResponse(**status)


@router.post("/screen/next")
async def force_next_screen():
    """Force rotation to next search."""
    from server.screen_rotator import get_rotator

    rotator = get_rotator()
    rotator.force_rotation()
    status = rotator.get_status()
    return {"message": "Rotated to next search", "status": status}


@router.post("/screen/set/{search_id}")
async def set_current_screen(search_id: int):
    """Manually set which search to display."""
    from server.screen_rotator import get_rotator

    rotator = get_rotator()
    success = rotator.set_current_search(search_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Search {search_id} not found or not active"
        )

    status = rotator.get_status()
    return {"message": f"Set current search to {search_id}", "status": status}


# ==================== WATCHER CONTROL ENDPOINTS ====================

class WatcherStatusResponse(BaseModel):
    running: bool
    interval_seconds: int
    last_run: float
    seconds_since_last_run: Optional[int]


@router.get("/watcher/status", response_model=WatcherStatusResponse)
async def get_watcher_status():
    """Get watcher status."""
    from server.wallapop.watcher import get_watcher

    watcher = get_watcher()
    return WatcherStatusResponse(**watcher.get_status())


@router.post("/watcher/run")
async def run_watcher_once():
    """Trigger a manual search cycle for all active searches."""
    from server.wallapop.watcher import get_watcher

    watcher = get_watcher()
    results = watcher.run_once()
    return {
        "message": "Search cycle completed",
        "results": results
    }


@router.post("/searches/{search_id}/run")
async def run_single_search(search_id: int):
    """Trigger a manual search for a specific search."""
    from server.wallapop.watcher import get_watcher

    db = get_db()
    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    watcher = get_watcher()
    results = watcher.search_single(search_id)
    return {
        "message": f"Search '{search['name']}' completed",
        "results": results
    }


@router.delete("/searches/{search_id}/items")
async def delete_search_items(search_id: int):
    """Delete all items for a search (reset the search)."""
    from server.renderer import get_renderer

    db = get_db()
    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    # Delete all items for this search
    deleted_count = db.delete_items_for_search(search_id)

    # Clear last_item_id
    db.update_search(search_id, last_item_id=None)

    # Invalidate cached render
    renderer = get_renderer()
    cache_path = renderer.renders_dir / f"search_{search_id}.jpg"
    if cache_path.exists():
        import os
        os.remove(cache_path)

    return {
        "message": f"Deleted {deleted_count} items for search '{search['name']}'",
        "deleted_count": deleted_count
    }


@router.delete("/reset")
async def reset_database():
    """Delete ALL searches and items from the database."""
    from server.renderer import get_renderer
    import shutil

    db = get_db()
    result = db.delete_all_data()

    # Clear all cached renders
    renderer = get_renderer()
    if renderer.renders_dir.exists():
        for f in renderer.renders_dir.glob("*.jpg"):
            f.unlink()

    return {
        "message": f"Database reset complete",
        "searches_deleted": result["searches_deleted"],
        "items_deleted": result["items_deleted"]
    }


# ==================== CONFIGURATION ENDPOINTS ====================

class ConfigResponse(BaseModel):
    search_interval: int
    rotation_interval: int
    items_count: int
    time_filter: str


class ConfigUpdate(BaseModel):
    search_interval: Optional[int] = Field(None, ge=60, le=3600)
    rotation_interval: Optional[int] = Field(None, ge=5, le=300)
    items_count: Optional[int] = Field(None, ge=5, le=100)
    time_filter: Optional[str] = Field(None)


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    db = get_db()
    return ConfigResponse(
        search_interval=int(db.get_config("search_interval", "300")),
        rotation_interval=int(db.get_config("rotation_interval", "10")),
        items_count=int(db.get_config("items_count", "20")),
        time_filter=db.get_config("time_filter", "all")
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(config: ConfigUpdate):
    """Update configuration."""
    from server.wallapop.watcher import get_watcher
    from server.screen_rotator import get_rotator

    db = get_db()

    if config.search_interval is not None:
        db.set_config("search_interval", str(config.search_interval))
        watcher = get_watcher()
        watcher.interval = config.search_interval

    if config.rotation_interval is not None:
        db.set_config("rotation_interval", str(config.rotation_interval))
        rotator = get_rotator()
        rotator.rotation_interval = config.rotation_interval

    if config.items_count is not None:
        db.set_config("items_count", str(config.items_count))

    if config.time_filter is not None:
        # Validate time_filter
        if config.time_filter in ("today", "week", "all"):
            db.set_config("time_filter", config.time_filter)

    return ConfigResponse(
        search_interval=int(db.get_config("search_interval", "300")),
        rotation_interval=int(db.get_config("rotation_interval", "10")),
        items_count=int(db.get_config("items_count", "20")),
        time_filter=db.get_config("time_filter", "all")
    )
