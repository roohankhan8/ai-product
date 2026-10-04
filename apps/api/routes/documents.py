import uuid
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal
from core.config import get_settings
from core.dependencies import get_current_principal
from core.errors import APIError
from database import get_db_session
from models import AuditEvent, Document, IngestionJob
from ingestion import create_or_reset_job, enqueue, remove_queued_job
from storage import path_for, remove_file, save_bytes

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    storage_key: str = Field(min_length=1, max_length=512)
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int = Field(ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class DocumentUpdate(BaseModel):
    original_filename: str | None = Field(default=None, min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_key: str
    original_filename: str
    content_type: str | None
    size_bytes: int
    sha256: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class IndexResponse(BaseModel):
    document_id: uuid.UUID
    chunk_count: int
    status: str


ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def _audit(
    principal: Principal,
    request: Request,
    action: str,
    document_id: uuid.UUID,
) -> AuditEvent:
    return AuditEvent(
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user_id,
        action=action,
        resource_type="document",
        resource_id=str(document_id),
        request_id=getattr(request.state, "request_id", None),
        details={},
    )


async def _get_document(
    document_id: uuid.UUID,
    principal: Principal,
    session: AsyncSession,
) -> Document:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == principal.tenant_id,
        )
    )
    if document is None:
        raise APIError(404, "document_not_found", "Document not found")
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = Document(
        tenant_id=principal.tenant_id,
        uploaded_by_user_id=principal.user_id,
        **payload.model_dump(),
    )
    session.add(document)
    await session.flush()
    session.add(_audit(principal, request, "document.created", document.id))
    await session.commit()
    await session.refresh(document)
    return document


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    content_type = file.content_type or ""
    expected_suffix = ALLOWED_TYPES.get(content_type)
    if expected_suffix is None:
        raise APIError(
            415,
            "unsupported_file_type",
            "Only PDF, text, and Markdown files are allowed",
        )

    original_filename = Path(file.filename or "upload").name
    if not original_filename or Path(original_filename).suffix.lower() != expected_suffix:
        raise APIError(415, "file_extension_mismatch", "File extension does not match its type")
    duplicate = await session.scalar(
        select(Document.id).where(
            Document.tenant_id == principal.tenant_id,
            func.lower(Document.original_filename) == original_filename.lower(),
        )
    )
    if duplicate is not None:
        raise APIError(
            409,
            "duplicate_filename",
            "A document with this filename already exists in the workspace",
        )

    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise APIError(413, "file_too_large", "Uploaded file exceeds the size limit")
    if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise APIError(415, "invalid_file_signature", "Uploaded PDF signature is invalid")
    if not content:
        raise APIError(422, "empty_file", "Uploaded file is empty")

    document_id = uuid.uuid4()
    storage_key = f"{principal.tenant_id}/{document_id}{expected_suffix}"
    digest = sha256(content).hexdigest()
    save_bytes(storage_key, content)
    document = Document(
        id=document_id,
        tenant_id=principal.tenant_id,
        uploaded_by_user_id=principal.user_id,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=digest,
        status="uploaded",
    )
    try:
        session.add(document)
        await session.flush()
        job = await create_or_reset_job(session, document)
        session.add(_audit(principal, request, "document.uploaded", document_id))
        await session.commit()
        await session.refresh(document)
        try:
            await enqueue(job.id)
        except Exception:
            # The durable job remains pending and can be re-enqueued by the retry endpoint.
            pass
    except Exception:
        await session.rollback()
        remove_file(storage_key)
        raise
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Document]:
    rows = await session.scalars(
        select(Document)
        .where(Document.tenant_id == principal.tenant_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    return await _get_document(document_id, principal, session)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    document = await _get_document(document_id, principal, session)
    path = path_for(document.storage_key)
    if not path.is_file():
        raise APIError(404, "file_not_found", "Document file is not available")
    return FileResponse(
        path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.original_filename,
    )


@router.post("/{document_id}/index", response_model=IndexResponse)
async def index_uploaded_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> IndexResponse:
    document = await _get_document(document_id, principal, session)
    job = await create_or_reset_job(session, document)
    await session.commit()
    try:
        await enqueue(job.id)
    except Exception:
        pass
    return IndexResponse(document_id=document.id, chunk_count=0, status=document.status)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = await _get_document(document_id, principal, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    session.add(_audit(principal, request, "document.updated", document.id))
    await session.commit()
    await session.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    document = await _get_document(document_id, principal, session)
    job = await session.scalar(select(IngestionJob).where(IngestionJob.document_id == document.id))
    session.add(_audit(principal, request, "document.deleted", document.id))
    await session.delete(document)
    await session.commit()
    if job is not None:
        try:
            await remove_queued_job(job.id)
        except Exception:
            pass
    remove_file(document.storage_key)
