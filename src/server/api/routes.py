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


class SearchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    keywords: Optional[str] = Field(None, min_length=1, max_length=200)
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)
    category_ids: Optional[str] = None
    distance: Optional[int] = Field(None, ge=0, le=500)
    active: Optional[bool] = None


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
    uptime = int(time.time() - _start_time)
    db = get_db()
    db_status = "connected" if db else "disconnected"

    return HealthResponse(
        status="ok",
        version="3.0.0",
        uptime_seconds=uptime,
        database=db_status,
        watcher="stopped"  # Will be "running" when watcher is implemented
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
        active=search.active
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
            first_seen=item["first_seen"],
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
        first_seen=item["first_seen"],
        wallapop_url=item.get("wallapop_url")
    )


@router.get("/searches/{search_id}/screen.jpg")
async def get_screen_image(search_id: int):
    """Get the rendered 128x160 JPG image for ESP32."""
    db = get_db()

    search = db.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail=f"Search with id {search_id} not found")

    # Check if rendered image exists
    data_dir = os.getenv("WALLBOT_DATA_DIR", "./data")
    render_path = os.path.join(data_dir, "renders", f"{search_id}.jpg")

    if os.path.exists(render_path):
        return FileResponse(
            render_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache"}
        )

    # Return placeholder image (will be implemented in FASE 4)
    # For now, return 404
    raise HTTPException(
        status_code=404,
        detail="Image not yet rendered. Run watcher to generate images."
    )


# ==================== ESP32 SCREEN ENDPOINTS ====================

@router.get("/screen.jpg")
async def get_esp32_screen():
    """Get the current screen image for ESP32.

    This is the main endpoint for ESP32 polling.
    The server automatically rotates between active searches.
    """
    from server.screen_rotator import get_rotator

    rotator = get_rotator()
    current = rotator.get_current_search()

    if not current:
        # No active searches - return placeholder
        raise HTTPException(
            status_code=404,
            detail="No active searches configured"
        )

    # Check if rendered image exists
    data_dir = os.getenv("WALLBOT_DATA_DIR", "./data")
    render_path = os.path.join(data_dir, "renders", f"{current['id']}.jpg")

    if os.path.exists(render_path):
        return FileResponse(
            render_path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Current-Search-Id": str(current["id"]),
                "X-Current-Search-Name": current["name"]
            }
        )

    # No image yet
    raise HTTPException(
        status_code=404,
        detail=f"Image for search '{current['name']}' not yet rendered"
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
