import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal
from core.dependencies import get_current_principal
from core.errors import APIError
from database import get_db_session
from models import ApprovalRequest, AuditEvent, Task

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApprovalCreate(BaseModel):
    action: str = Field(pattern=r"^task.create$")
    arguments: dict[str, str]


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    action: str
    status: str
    arguments: dict[str, str]
    expires_at: datetime
    idempotency_key: str


async def _get_approval(approval_id: uuid.UUID, principal: Principal, session: AsyncSession) -> ApprovalRequest:
    item = await session.scalar(select(ApprovalRequest).where(
        ApprovalRequest.id == approval_id, ApprovalRequest.tenant_id == principal.tenant_id
    ))
    if item is None:
        raise APIError(404, "approval_not_found", "Approval request not found")
    return item


def _expire_if_needed(item: ApprovalRequest) -> None:
    if item.status in {"pending", "approved"} and item.expires_at <= datetime.now(timezone.utc):
        item.status = "expired"


@router.post("", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval(
    payload: ApprovalCreate,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequest:
    if not payload.arguments.get("title"):
        raise APIError(400, "invalid_action_arguments", "A task title is required")
    item = ApprovalRequest(
        tenant_id=principal.tenant_id, requested_by_user_id=principal.user_id,
        action=payload.action, arguments=payload.arguments,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        idempotency_key=str(uuid.uuid4()),
    )
    session.add(item)
    session.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id,
        action="approval.created", resource_type="approval", resource_id=str(item.id),
        request_id=getattr(request.state, "request_id", None), details={"action": payload.action},
    ))
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[ApprovalRequest]:
    rows = list(await session.scalars(
        select(ApprovalRequest)
        .where(ApprovalRequest.tenant_id == principal.tenant_id)
        .order_by(ApprovalRequest.created_at.desc())
    ))
    changed = False
    for item in rows:
        before = item.status
        _expire_if_needed(item)
        changed |= before != item.status
    if changed:
        await session.commit()
    return rows


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(
    approval_id: uuid.UUID, request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequest:
    item = await _get_approval(approval_id, principal, session)
    _expire_if_needed(item)
    if item.status != "pending":
        raise APIError(409, "approval_not_pending", "Approval request is no longer pending")
    item.status = "approved"
    item.decided_by_user_id = principal.user_id
    item.decided_at = datetime.now(timezone.utc)
    session.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id,
        action="approval.approved", resource_type="approval", resource_id=str(item.id),
        request_id=getattr(request.state, "request_id", None), details={},
    ))
    await session.commit()
    return item


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject(
    approval_id: uuid.UUID, request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequest:
    item = await _get_approval(approval_id, principal, session)
    _expire_if_needed(item)
    if item.status != "pending":
        raise APIError(409, "approval_not_pending", "Approval request is no longer pending")
    item.status = "rejected"
    item.decided_by_user_id = principal.user_id
    item.decided_at = datetime.now(timezone.utc)
    session.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id,
        action="approval.rejected", resource_type="approval", resource_id=str(item.id),
        request_id=getattr(request.state, "request_id", None), details={},
    ))
    await session.commit()
    return item


@router.post("/{approval_id}/execute", response_model=ApprovalResponse)
async def execute(
    approval_id: uuid.UUID, request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalRequest:
    item = await _get_approval(approval_id, principal, session)
    _expire_if_needed(item)
    if item.status != "approved":
        raise APIError(409, "approval_not_approved", "Approval request is not approved")
    if not principal.can_manage_members():
        raise APIError(403, "action_forbidden", "Only workspace administrators can execute this action")
    task = Task(
        tenant_id=principal.tenant_id, created_by_user_id=item.requested_by_user_id,
        title=item.arguments["title"], description=item.arguments.get("description"),
    )
    session.add(task)
    await session.flush()
    item.status = "executed"
    item.executed_at = datetime.now(timezone.utc)
    session.add(AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id,
        action="approval.executed", resource_type="approval", resource_id=str(item.id),
        request_id=getattr(request.state, "request_id", None), details={"task_id": str(task.id)},
    ))
    await session.commit()
    return item
