"""Health check router — GET /health"""

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/health", summary="Health check")
async def health():
    """Returns service status. Used by load balancers and uptime monitors."""
    return {"status": "UP"}
