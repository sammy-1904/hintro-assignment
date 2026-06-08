from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.meetings import router as meetings_router
from app.routers.action_items import router as action_items_router
from app.routers.evaluation import router as evaluation_router

__all__ = [
    "auth_router",
    "health_router",
    "meetings_router",
    "action_items_router",
    "evaluation_router",
]
