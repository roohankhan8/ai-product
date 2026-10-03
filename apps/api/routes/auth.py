import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal, issue_token
from core.dependencies import get_current_principal
from core.errors import APIError
from database import get_db_session
from models import AuditEvent, User

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PrincipalResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    request_context: Request,
    request: DevLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == request.email.lower()))
    if user is None or not user.is_active:
        raise APIError(401, "invalid_credentials", "Invalid credentials")
    session.add(
        AuditEvent(
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            request_id=getattr(request_context.state, "request_id", None),
            details={"method": "dev-login"},
        )
    )
    await session.commit()
    principal = Principal(user.id, user.tenant_id, user.role, user.email)
    return TokenResponse(access_token=issue_token(principal))


@router.get("/me", response_model=PrincipalResponse)
async def me(principal: Principal = Depends(get_current_principal)) -> PrincipalResponse:
    return PrincipalResponse(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        email=principal.email,
        role=principal.role,
    )
