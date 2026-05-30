"""Authentication routes: register, login, guest, current user."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import Token, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(subject=user.id, is_guest=False)
    _set_auth_cookie(response, token)
    return Token(access_token=token, is_guest=False)


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled.")
    token = create_access_token(subject=user.id, is_guest=False)
    _set_auth_cookie(response, token)
    return Token(access_token=token, is_guest=False)


@router.post("/guest", response_model=Token)
async def continue_as_guest(response: Response):
    """Issue a guest token (no DB row). Lets users try the app instantly."""
    guest_id = f"guest_{uuid.uuid4().hex[:16]}"
    token = create_access_token(subject=guest_id, is_guest=True)
    _set_auth_cookie(response, token)
    return Token(access_token=token, is_guest=True)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
