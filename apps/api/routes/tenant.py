import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal
from core.dependencies import get_current_principal
from database import get_db_session
from models import Document, User

router = APIRouter(prefix="/tenant", tags=["tenant"])


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    status: str


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    rows = await session.scalars(select(User).where(User.tenant_id == principal.tenant_id))
    return list(rows)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    rows = await session.scalars(
        select(Document).where(Document.tenant_id == principal.tenant_id)
    )
    return list(rows)
