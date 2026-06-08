"""
Auth dependency — injects the authenticated user into any protected route.

Usage:
    from app.dependencies import get_current_user

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        ...
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.errors import AppError

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError("UNAUTHORIZED", "Authentication required", 401)

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise AppError("INVALID_TOKEN", "Malformed token payload", 401)
    except JWTError:
        raise AppError("INVALID_TOKEN", "Could not validate token", 401)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError("UNAUTHORIZED", "User no longer exists", 401)

    return user
