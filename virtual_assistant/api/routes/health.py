"""
Health check route for the Virtual Assistant API.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return API health status and version."""
    return {"status": "ok", "version": "0.1.0"}
