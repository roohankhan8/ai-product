"""Application-controlled, read-only tools for the manual agent loop."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal
from core.errors import APIError
from models import Document
from rag import RetrievedChunk, retrieve

MAX_TOOL_CALLS = 3
TOOL_TIMEOUT_SECONDS = 5.0


class ListDocumentsArgs(BaseModel):
    suffix: str | None = Field(default=None, pattern=r"^\.(pdf|md|txt)$")


class SearchKnowledgeArgs(BaseModel):
    query: str = Field(min_length=1, max_length=12000)
    top_k: int = Field(default=5, ge=1, le=10)


class TaskCreateArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class ToolProposal(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


def parse_tool_proposal(content: str) -> ToolProposal | None:
    """Parse only the deliberately small JSON envelope accepted from a model."""
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(candidate)
        if not isinstance(data, dict) or data.get("type") != "tool_call":
            return None
        return ToolProposal.model_validate(data.get("tool", {}))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ToolContext:
    session: AsyncSession
    principal: Principal


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], Awaitable[Any]]
    required_roles: frozenset[str]
    read_only: bool = True


async def list_documents(context: ToolContext, args: ListDocumentsArgs) -> list[dict[str, str]]:
    query = select(Document).where(Document.tenant_id == context.principal.tenant_id)
    if args.suffix:
        query = query.where(Document.original_filename.ilike(f"%{args.suffix}"))
    documents = await context.session.scalars(query.order_by(Document.created_at.asc()))
    return [{"id": str(item.id), "filename": item.original_filename} for item in documents]


async def search_knowledge(context: ToolContext, args: SearchKnowledgeArgs) -> list[RetrievedChunk]:
    return await retrieve(context.session, context.principal.tenant_id, args.query, args.top_k)


class ToolRegistry:
    def __init__(self, specs: tuple[ToolSpec, ...]) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"name": spec.name, "description": spec.description, "read_only": spec.read_only}
            for spec in self._specs.values()
        ]

    async def execute(self, name: str, arguments: dict[str, Any], context: ToolContext) -> Any:
        spec = self._specs.get(name)
        if spec is None:
            raise APIError(400, "unknown_tool", "The requested tool is not available")
        if context.principal.role not in spec.required_roles:
            raise APIError(403, "tool_forbidden", "You are not allowed to use this tool")
        try:
            parsed = spec.args_model.model_validate(arguments)
        except Exception as exc:
            raise APIError(400, "invalid_tool_arguments", "Tool arguments are invalid") from exc
        try:
            return await asyncio.wait_for(spec.handler(context, parsed), TOOL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            raise APIError(504, "tool_timeout", "The tool took too long to respond") from exc


READ_ONLY_ROLES = frozenset({"owner", "admin", "member"})
tool_registry = ToolRegistry((
    ToolSpec(
        name="list_documents",
        description="List documents available in the authenticated tenant.",
        args_model=ListDocumentsArgs,
        handler=list_documents,
        required_roles=READ_ONLY_ROLES,
    ),
    ToolSpec(
        name="search_knowledge",
        description="Search indexed documents available in the authenticated tenant.",
        args_model=SearchKnowledgeArgs,
        handler=search_knowledge,
        required_roles=READ_ONLY_ROLES,
    ),
))
