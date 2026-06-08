"""
Authentication router.

POST /api/auth/register  — create account, returns JWT
POST /api/auth/login     — verify credentials, returns JWT
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.trace import get_trace_id
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.utils.errors import AppError
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ───────────────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    status_code=201,
    summary="Register a new user",
    description="Creates a user account and returns a JWT token.",
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("New user registered: %s", user.email, extra={"traceId": get_trace_id()})

    return success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "access_token": create_access_token(user.id),
            "token_type": "bearer",
        },
        trace_id=get_trace_id(),
        status_code=201,
    )


@router.post(
    "/login",
    summary="Login",
    description="Validates credentials and returns a JWT token.",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time comparison prevents timing attacks
    if user is None or not verify_password(body.password, user.hashed_password):
        raise AppError("INVALID_CREDENTIALS", "Incorrect email or password.", 401)

    logger.info("User logged in: %s", user.email, extra={"traceId": get_trace_id()})

    return success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "access_token": create_access_token(user.id),
            "token_type": "bearer",
        },
        trace_id=get_trace_id(),
    )
