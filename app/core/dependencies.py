"""Shared FastAPI dependencies for authentication."""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

# auto_error=False lets us support "optional auth" (guest-friendly) endpoints.
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentPrincipal:
    """Represents whoever is making the request: a user or a guest token."""

    def __init__(self, user_id: Optional[str], is_guest: bool, guest_token: Optional[str]):
        self.user_id = user_id
        self.is_guest = is_guest
        self.guest_token = guest_token

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None or self.guest_token is not None


def _read_token(request: Request, creds: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if creds and creds.credentials:
        return creds.credentials
    # Also accept token from cookie so the server-rendered UI works.
    return request.cookies.get("access_token")


async def get_current_principal(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentPrincipal:
    token = _read_token(request, creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    is_guest = bool(payload.get("is_guest"))
    request.state.user_id = None if is_guest else sub
    if is_guest:
        return CurrentPrincipal(user_id=None, is_guest=True, guest_token=sub)
    return CurrentPrincipal(user_id=sub, is_guest=False, guest_token=None)


async def get_optional_principal(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentPrincipal]:
    try:
        return await get_current_principal(request, creds)
    except HTTPException:
        return None


async def get_current_user(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> User:
    if principal.is_guest or not principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A registered account is required for this action.",
        )
    user = await db.scalar(select(User).where(User.id == principal.user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user
