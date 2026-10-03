import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal
from core.config import get_settings
from core.dependencies import get_current_principal
from core.errors import APIError
from core.llm import ChatMessage, get_chat_provider
from database import get_db_session
from models import AuditEvent, Conversation, Message

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    created_at: datetime


async def _get_conversation(
    conversation_id: uuid.UUID,
    principal: Principal,
    session: AsyncSession,
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == principal.tenant_id,
        )
    )
    if conversation is None:
        raise APIError(404, "conversation_not_found", "Conversation not found")
    return conversation


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def chat(
    payload: ChatRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    if payload.conversation_id is None:
        conversation = Conversation(
            tenant_id=principal.tenant_id,
            owner_user_id=principal.user_id,
            title=payload.message[:200],
        )
        session.add(conversation)
        await session.flush()
    else:
        conversation = await _get_conversation(payload.conversation_id, principal, session)

    history = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = [ChatMessage(item.role, item.content) for item in history]
    messages.append(ChatMessage("user", payload.message))
    assistant_content = await get_chat_provider().complete(messages)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
    )
    session.add_all([user_message, assistant_message])
    session.add(
        AuditEvent(
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            action="chat.completed",
            resource_type="conversation",
            resource_id=str(conversation.id),
            request_id=getattr(request.state, "request_id", None),
            details={"provider": get_settings().llm_provider},
        )
    )
    await session.commit()
    await session.refresh(assistant_message)
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        content=assistant_message.content,
        created_at=assistant_message.created_at,
    )
