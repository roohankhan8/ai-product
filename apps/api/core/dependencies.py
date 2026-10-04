from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal, decode_token
from core.errors import APIError
from database import get_db_session
from models import User

bearer = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(401, "authentication_required", "Authentication is required")
    token_principal = decode_token(credentials.credentials)
    user = await session.scalar(select(User).where(
        User.id == token_principal.user_id,
        User.tenant_id == token_principal.tenant_id,
        User.is_active.is_(True),
    ))
    if user is None:
        raise APIError(401, "authentication_required", "Authentication is required")
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
    )
