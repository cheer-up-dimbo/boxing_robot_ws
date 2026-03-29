"""Preset CRUD endpoints for BoxBunny Dashboard.

Users can save, list, update, delete, and favorite training presets.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from boxbunny_dashboard.api.auth import get_current_user
from boxbunny_dashboard.db.manager import DatabaseManager

logger = logging.getLogger("boxbunny.dashboard.presets")
router = APIRouter()


# ---- Pydantic models ----

class PresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    preset_type: str = Field(..., max_length=32)
    config_json: str = Field(default="{}")
    description: str = Field(default="", max_length=512)
    tags: str = Field(default="")


class PresetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    config_json: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=512)
    tags: Optional[str] = None


class PresetResponse(BaseModel):
    id: int
    name: str
    description: str
    preset_type: str
    config_json: str
    is_favorite: bool
    tags: str
    use_count: int


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


# ---- Endpoints ----

@router.get("/", response_model=List[PresetResponse])
async def list_presets(
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> List[PresetResponse]:
    """List all presets for the authenticated user."""
    rows = db.get_presets(user["user_id"])
    return [
        PresetResponse(
            id=r["id"], name=r["name"], description=r.get("description", ""),
            preset_type=r["preset_type"], config_json=r["config_json"],
            is_favorite=bool(r.get("is_favorite", False)),
            tags=r.get("tags", ""), use_count=r.get("use_count", 0),
        )
        for r in rows
    ]


@router.post("/", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
async def create_preset(
    body: PresetCreate,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> PresetResponse:
    """Create a new preset."""
    preset_id = db.create_preset(
        user_id=user["user_id"],
        name=body.name,
        preset_type=body.preset_type,
        config_json=body.config_json,
        description=body.description,
        tags=body.tags,
    )
    logger.info("Preset created: id=%d user=%s", preset_id, user["username"])
    return PresetResponse(
        id=preset_id, name=body.name, description=body.description,
        preset_type=body.preset_type, config_json=body.config_json,
        is_favorite=False, tags=body.tags, use_count=0,
    )


@router.put("/{preset_id}", response_model=Dict[str, Any])
async def update_preset(
    preset_id: int,
    body: PresetUpdate,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> Dict[str, Any]:
    """Update an existing preset."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    success = db.update_preset(preset_id, **updates)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset not found or no valid fields",
        )
    return {"id": preset_id, "updated": True}


@router.delete("/{preset_id}", status_code=status.HTTP_200_OK)
async def delete_preset(
    preset_id: int,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> Dict[str, Any]:
    """Soft-delete (archive) a preset by marking it as archived."""
    success = db.update_preset(preset_id, tags="archived")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset not found",
        )
    logger.info("Preset archived: id=%d user=%s", preset_id, user["username"])
    return {"id": preset_id, "archived": True}


@router.post("/{preset_id}/favorite", response_model=Dict[str, Any])
async def toggle_favorite(
    preset_id: int,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> Dict[str, Any]:
    """Toggle the favorite status of a preset."""
    presets = db.get_presets(user["user_id"])
    current = next((p for p in presets if p["id"] == preset_id), None)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset not found",
        )
    new_value = not bool(current.get("is_favorite", False))
    db.update_preset(preset_id, is_favorite=int(new_value))
    return {"id": preset_id, "is_favorite": new_value}
