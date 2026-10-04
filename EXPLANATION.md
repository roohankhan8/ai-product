# Codebase explanation

This document explains the current implementation of the AI Operations Platform: what each source file owns, how requests move through the system, and where the current boundaries are. It describes the code as it exists today, not the complete future product described in `IDEA.md` and `PLAN.md`.

## Product shape

The repository contains two applications and a small set of operational utilities:

```text
Browser (Next.js)
        │ HTTP + bearer token
        ▼
FastAPI API ─────── PostgreSQL
    │                   │
    ├── local storage   └── documents, chunks, jobs, users, tenants
    ├── Redis queue
    └── LLM provider
            ▲
            │
     ingestion worker
```

The current user journey is:

1. A user signs in through the development login endpoint.
2. The web app stores the signed bearer token in browser local storage.
3. The user uploads a UTF-8 text or Markdown file.
4. The API stores the file and creates a durable ingestion job.
5. Redis wakes the ingestion worker, which parses, chunks, embeds, and indexes it.
6. Chat retrieves chunks belonging to the user’s tenant and sends them to the configured chat provider.
7. The response includes citation metadata for the retrieved chunks.

PDF files are currently accepted for storage and download, but parsing/OCR is intentionally deferred. The baseline embedding and retrieval implementation is local and deterministic; it is a learning-oriented baseline, not yet a production-scale vector index.

## Current status and what is next

The repository is past the initial scaffold. The current vertical slice includes FastAPI health/readiness and error handling, PostgreSQL models and migrations, development password login, tenant-scoped document access, local storage, Redis-backed ingestion with retries, deterministic baseline retrieval, cited chat, conversation history, unanswered-question tracking, and a Next.js workspace.

The next work should be:

1. Verify the existing slice end to end from a clean local setup: migrations, API, worker, web build, upload/index, and cited chat.
2. Add automated verification and a minimal CI gate around authentication, tenant isolation, upload/index failure paths, health/readiness, and retrieval.
3. Harden the trust boundaries before adding agents: production identity/session handling, upload and prompt-injection threat cases, rate limits, authorization checks, and sensitive-data redaction.
4. Add operational visibility for queue health, model latency/usage, retrieval results, and provider or worker failures.
5. Then implement read-only typed tools and a bounded manual agent loop; side-effecting tools should wait for persisted human approval.

This order keeps the document-to-cited-answer flow reliable and makes future agent, approval, and MCP features reuse the same application authorization and audit boundaries.

## Root documentation and configuration

### `AGENTS.md`

Repository operating instructions for the coding agent. It defines the product direction, layering rules, security expectations, setup-documentation requirements, and the important constraint that tests must not be written or run unless explicitly requested. It also says not to read or commit secret files such as `.env`.

### `IDEA.md`

Product rationale and the long-term learning roadmap. It explains why the platform exists, the intended multi-tenant architecture, the progression from basic persistence to RAG, agents, approvals, MCP, workers, evaluation, observability, security, and deployment. It is directional rather than an executable specification.

### `PLAN.md`

The staged implementation plan. Each numbered phase has scope, implementation principles, and a “Done when” acceptance statement. The code currently covers the early API/database phases, baseline RAG, evaluation, the initial UI, and durable ingestion.

### `SETUP.md`

The operational setup guide. It documents prerequisites, ports, environment variables, migrations, API/web commands, baseline RAG evaluation, the ingestion worker, and the root `scripts/dev.ps1` launcher. PostgreSQL’s host port is intentionally `5433`.

### `README.md`

Short repository orientation and quick-start instructions. It points readers to `IDEA.md`, `PLAN.md`, and `SETUP.md`, describes the current stack, and shows the manual startup flow. The one-command Windows launcher is documented in `SETUP.md`.

### `docker-compose.yml`

Defines local infrastructure only:

- `postgres`: PostgreSQL 16, exposed as `localhost:5433`, with a persistent volume.
- `redis`: Redis 7 with append-only persistence, exposed as `localhost:6379`.

The API, worker, and web app are not containerized yet. This is why the root developer launcher starts them as local processes.

## Backend package: `apps/api`

### `apps/api/__init__.py`

Marks the API directory as a Python package. It contains no application behavior.

### `apps/api/pyproject.toml`

Defines the backend package and its dependencies. Important runtime dependencies are FastAPI, SQLAlchemy async support, asyncpg, Alembic, Pydantic settings, HTTPX, multipart upload support, and Redis. The `dev` extra provides pytest and Ruff for environments where those checks are explicitly requested.

The package configuration exposes top-level modules such as `main`, `models`, and `database`, and discovers the `core` and `routes` packages. The API is designed to run from `apps/api`, which is also how imports such as `from models import Document` resolve.

### `apps/api/main.py`

The FastAPI composition root.

Responsibilities:

- Loads settings and configures JSON logging.
- Creates the `FastAPI` application and lifespan handler.
- Disposes the database engine during shutdown.
- Registers exception handlers.
- Adds CORS middleware for the local Next.js origins (`localhost:3000` and `127.0.0.1:3000`). This handles browser `OPTIONS` preflight requests.
- Includes the health, auth, chat, document, and tenant routers.
- Adds request middleware that creates or accepts a safe `X-Request-ID`, stores it in request state/context, measures duration, and logs the completed request.

The middleware is deliberately near the application boundary so every route gets the same request correlation behavior.

### `apps/api/database.py`

Creates the async SQLAlchemy engine and session factory from `DATABASE_URL`. `get_db_session()` yields an `AsyncSession`; service/route code owns commits and rollbacks. `dispose_database()` is used by the FastAPI lifespan shutdown.

This is the persistence connection seam. Routes depend on a session rather than constructing database connections themselves.

### `apps/api/models.py`

Defines the SQLAlchemy domain schema and shared metadata naming convention.

#### `Base` and `TimestampMixin`

`Base` supplies SQLAlchemy declarative metadata and predictable names for primary keys, foreign keys, indexes, unique constraints, and checks. `TimestampMixin` adds timezone-aware `created_at` and `updated_at` columns.

#### `Tenant`

Represents a company/workspace. `slug` is unique. Tenant IDs are the central ownership key used throughout application queries.

#### `User`

Belongs to a tenant and has an email, display name, role, and active flag. Email uniqueness is scoped to the tenant. Roles are constrained to `owner`, `admin`, or `member`.

#### `Document`

Stores uploaded-document metadata: tenant owner, uploader, storage key, original filename, content type, byte size, checksum, and processing status. Status is constrained to `uploaded`, `processing`, `ready`, or `failed`.

The database stores metadata; the actual bytes live under the configured local storage directory.

#### `DocumentChunk`

Stores the searchable representation of a document chunk. Each row carries both `tenant_id` and `document_id`, content, source metadata, chunk position, and a JSON embedding. A unique `(document_id, chunk_index)` constraint makes re-indexing deterministic and prevents duplicate positions.

#### `IngestionJob`

Tracks durable background work for one document. Its unique document constraint makes the job idempotency key the document itself. Status can be `pending`, `running`, `retry`, `completed`, or `failed`; attempts and an error message make failures inspectable. `available_at` supports future backoff scheduling.

#### `Conversation`, `Message`, `Task`, and `AuditEvent`

These are the foundations for later chat history, controlled actions, and auditability. Conversations and tasks are tenant-owned. Messages belong to conversations. Audit events retain tenant, actor, action, resource, request ID, and structured details.

### `apps/api/core/config.py`

Defines typed settings with Pydantic Settings. Values can come from environment variables or `.env` when running locally.

Important settings include database and Redis URLs, auth secret, storage directory, upload limit, LLM provider/model/key/base URL, and timeout. The development defaults intentionally support local work, but production should supply managed secrets and a real provider configuration.

### `apps/api/core/auth.py`

Implements the current development bearer-token format without adding an identity-provider dependency.

- `Principal` is the authenticated identity passed into routes. It contains user ID, tenant ID, role, and email.
- `issue_token()` serializes those claims, base64url-encodes them, and signs the encoded payload with HMAC-SHA256.
- `decode_token()` verifies the signature and converts the claims back into a `Principal`.
- `generate_secret()` creates a suitable random secret for local configuration.

This is a compact development mechanism, not a production OIDC/session implementation. Token claims are signed, but route-level authorization still needs to query application data where necessary.

### `apps/api/core/dependencies.py`

Defines the FastAPI authentication dependency. It reads an HTTP bearer credential, rejects missing or non-bearer credentials, and delegates validation to `decode_token()`.

Routes use `Depends(get_current_principal)` to make authentication explicit and consistent.

### `apps/api/core/errors.py`

Defines `APIError`, the safe application exception carrying an HTTP status, machine-readable code, and client-safe message. Business/application code can raise this without knowing how JSON responses are formatted.

### `apps/api/core/request_context.py`

Holds the current request ID in a `ContextVar`. Logging can retrieve the ID even in code that does not have direct access to the FastAPI `Request` object.

### `apps/api/core/logging.py`

Configures structured JSON logging. `JsonFormatter` emits timestamps, level, logger name, message, request ID, HTTP fields, and exception details when present. This gives operators a consistent shape for correlating API requests.

### `apps/api/core/llm.py`

Defines the chat-provider abstraction and provider implementations.

- `ChatMessage` is the internal role/content message value.
- `ChatProvider` is the minimal async completion interface.
- `MockChatProvider` returns a deterministic response from the latest user message and requires no credentials.
- `OpenAICompatibleProvider` sends a standard chat-completions payload through HTTPX.
- `GeminiProvider` translates messages into Gemini `contents` and calls `generateContent`.
- `get_chat_provider()` selects the configured provider. In development, Gemini with an absent or literal `replace-me` key falls back to the mock provider so local chat does not make an invalid external request.

Provider errors are converted to safe `APIError` responses rather than leaking HTTP/provider details.

### `apps/api/exception_handlers.py`

Maps expected API errors, HTTP errors, validation errors, and unexpected exceptions to one JSON error shape. Every response includes the request ID where available. Unexpected errors are logged with trace information while the client receives a generic `internal_error` message.

### `apps/api/storage.py`

Owns local file storage. `path_for()` resolves a storage key beneath the configured root and rejects path traversal. `save_bytes()` creates parent directories and writes bytes; `remove_file()` deletes an existing stored file.

The path check is an important trust boundary because filenames and storage keys originate from upload/application input.

### `apps/api/rag.py`

Contains the baseline parsing, chunking, embedding, indexing, and retrieval implementation.

- `parse_text()` accepts `.txt` and `.md`, decodes UTF-8 with BOM support, normalizes Unicode, normalizes line endings, trims trailing whitespace, and rejects unsupported or malformed text.
- `chunk_text()` makes deterministic character-based chunks with a line-boundary preference and overlap. Empty text produces no chunks.
- `embed()` creates a fixed 256-dimensional normalized word vector. A stable `blake2b` digest maps each word to a bucket, avoiding Python’s process-randomized `hash()`.
- `index_document()` reads stored bytes, parses and chunks them, deletes prior chunks, inserts the new chunks, and marks the document ready. The caller controls the transaction.
- `retrieve()` always filters by `tenant_id` at the SQL query boundary, computes cosine-like dot products in Python, drops zero-score results, and returns top-k chunks.

This implementation is intentionally simple. JSON embeddings and application-side scoring are suitable for a small learning baseline; pgvector or a dedicated vector service should be evaluated before scaling.

### `apps/api/ingestion.py`

Owns the durable ingestion job lifecycle.

- `redis_client()` creates a Redis client from settings.
- `enqueue()` pushes a job ID onto the `document-ingestion` queue.
- `create_or_reset_job()` creates the unique job for a document or resets an existing job for reprocessing, and marks the document `processing`.
- `process_job()` claims a job, increments attempts, calls the RAG indexer, and commits either completion or failure state. Exceptions are recorded, retried with exponential backoff up to `MAX_ATTEMPTS`, and finally mark both job and document failed.

The job is idempotent because indexing deletes and replaces all chunks for the document and the database allows only one job row per document.

### `apps/api/worker.py`

The standalone Redis worker process. It blocks on `document-ingestion`, parses job payloads, opens an async database session, and delegates processing to `process_job()`. Start it from `apps/api` with `python -m worker`.

The current worker is intentionally one-process/one-loop. Concurrency limits and a richer scheduler can be added once throughput requires them.

## API routes

### `apps/api/routes/auth.py`

Provides the development authentication flow:

- `POST /auth/dev-login` accepts an email and password and returns a bearer token for an existing active user.
- `POST /auth/logout` records a logout audit event.
- `apps/api/scripts/seed_admin.py` creates or updates the local admin user using a scrypt password hash.
- `GET /auth/me` returns the current principal.

This remains development authentication; production still needs a secure session or identity-provider integration.

Login writes an audit event. User lookup and tenant creation happen through the database session.

### `apps/api/routes/health.py`

Provides:

- `GET /health`: process liveness.
- `GET /ready`: executes `SELECT 1` and returns 503 if PostgreSQL is unavailable.

The distinction allows orchestration to know whether the process is alive versus ready for database-backed traffic.

### `apps/api/routes/tenant.py`

Provides authenticated tenant-scoped read endpoints for users and document summaries. Every query filters on `principal.tenant_id`, demonstrating the application/data-layer ownership boundary.

### `apps/api/routes/documents.py`

Owns document metadata and upload operations.

- `POST /api/v1/documents`: creates metadata for an already-managed storage key.
- `POST /api/v1/documents/upload`: validates content type, extension, size, PDF signature when applicable, and non-empty content; writes bytes; creates document metadata; creates a processing job; and enqueues it after commit.
- `GET /api/v1/documents`: lists documents for the current tenant.
- `GET /api/v1/documents/{id}`: returns a tenant-owned document.
- `GET /api/v1/documents/{id}/download`: serves the stored file after tenant authorization and path validation.
- `POST /api/v1/documents/{id}/index`: resets or creates the document’s ingestion job and re-enqueues it. It returns promptly with processing status rather than doing indexing inside the request.
- `PATCH` and `DELETE` update/remove metadata and clean up the local file on deletion.

Upload cleanup removes the stored file if the database transaction fails. This prevents an orphaned file when persistence fails.

### `apps/api/routes/chat.py`

Provides conversation and chat endpoints: list/delete conversations, list messages, list unanswered questions, and `POST /api/v1/chat`.

The chat route creates or retrieves a tenant-owned conversation, loads message history, retrieves tenant-filtered chunks, constructs a system instruction containing untrusted source context, calls the selected chat provider, persists messages, writes audit events, records unanswered questions when retrieval is insufficient, and returns the answer plus citation metadata.

The source text is framed as data rather than instructions. The LLM is not granted direct database or tool access.

## Database migrations

### `apps/api/alembic.ini`

Alembic configuration pointing migration discovery at `apps/api/alembic`. The placeholder SQLAlchemy URL is overridden by `alembic/env.py` from typed application settings.

### `apps/api/alembic/env.py`

Loads application settings, converts async PostgreSQL URLs to the synchronous psycopg driver used by Alembic, exposes `Base.metadata` for migration context, and supports offline/online migration modes.

### `apps/api/alembic/script.py.mako`

Alembic’s generated migration template. New revisions use it as their starting structure.

### `apps/api/alembic/README`

Alembic’s generated directory note. It is scaffolding documentation rather than runtime code.

### `0001_initial_schema.py`

Creates the first relational schema: tenants, users, documents, conversations, messages, tasks, and audit events, including ownership foreign keys, indexes, uniqueness, and status/role checks.

### `0002_document_chunks.py`

Adds tenant-owned `document_chunks` with document position uniqueness, content, source metadata, and JSON embeddings.

### `0003_ingestion_jobs.py`

Adds durable ingestion job state, attempts, retry timing, errors, tenant/document foreign keys, the unique document idempotency constraint, and the status/availability index used by workers and operators.

### `0004_user_password.py`

Adds password hashes for the local authentication flow and backfills existing users with an unusable value.

### `0005_unique_document_filename.py`

Adds the current tenant-scoped uniqueness rule for document filenames.

## Evaluation and developer scripts

### `evals/rag-baseline-v1.json`

Versioned synthetic retrieval data. It contains three small source documents and four queries covering known relevant sources and an unknown question. The expected document IDs support hit-rate, recall, MRR, and citation-coverage measurements.

### `scripts/evaluate_rag.py`

A dependency-light evaluation command. It implements the same stable hashed-vector idea as the API baseline, ranks documents by dot-product similarity, and prints JSON metrics for a selected `k`. It deliberately runs without database/API access so retrieval changes can be compared quickly.

### `scripts/dev.ps1`

The Windows one-command local launcher. It starts PostgreSQL and Redis with Docker Compose, verifies `apps/api/.venv` exists, activates that virtual environment in API and worker PowerShell windows, and starts the Next.js development server in another window. `-Foreground` prints the commands instead of spawning them.

## Frontend: `apps/web`

### `apps/web/app/layout.tsx`

Root Next.js layout. It loads Geist font variables, global CSS, sets the document language, and defines the Northstar page metadata.

### `apps/web/app/page.tsx`

The current client-side product surface.

- `api()` centralizes API URL construction and bearer-token headers, and maps 401/403 into an access-denied error.
- `Home` selects between sign-in and the authenticated workspace based on local storage.
- `SignIn` calls `/auth/dev-login`, handles loading/error state, and stores the returned token.
- `Workspace` provides chat/documents navigation, document loading, upload/indexing, sign-out, and shared error handling.
- `Chat` renders starter prompts, conversation messages, a composer, citations, loading state, and retry messaging.
- `Documents` renders upload controls, empty/loading/error states, document metadata, and processing/ready status badges.

The current client uses the API directly from the browser, so CORS is required. Tokens are stored in local storage for this development stage; a production implementation should use an appropriate secure session strategy.

### `apps/web/app/globals.css`

Defines the visual system and responsive layout: semantic color variables, typography, buttons, auth split screen, workspace sidebar, chat composer, citations, document list, status badges, loading spinner, mobile breakpoints, and reduced-motion behavior. It uses Tailwind’s import but currently expresses the product styling primarily through a compact custom CSS layer.

### `apps/web/app/favicon.ico`

Browser tab icon for the Next.js app.

### `apps/web/package.json`

Defines the frontend scripts (`dev`, `build`, `start`, `lint`) and dependencies: Next.js, React, TypeScript, Tailwind/PostCSS, ESLint, and the Next React compiler plugin.

### `apps/web/package-lock.json`

Locks the exact npm dependency graph so clean installs are reproducible.

### `apps/web/next.config.ts`

Next.js configuration. It currently enables the React compiler and leaves other options at defaults.

### `apps/web/postcss.config.mjs`

Configures the PostCSS/Tailwind integration used by the global stylesheet.

### `apps/web/tsconfig.json`

Strict TypeScript configuration with browser/modern JavaScript libraries, bundler module resolution, JSX support, incremental checking, and the `@/*` path alias.

### `apps/web/eslint.config.mjs`

Next.js/ESLint configuration for frontend linting.

### `apps/web/README.md`

Generated Next.js starter documentation. It is useful for generic framework commands, while repository-specific setup belongs in the root `SETUP.md`.

### `apps/web/AGENTS.md` and `apps/web/CLAUDE.md`

Frontend-local agent guidance. The important Next.js note is to consult the installed Next documentation for version-specific behavior before making framework changes.

### `apps/web/public/*.svg`

Starter static assets from the Next.js scaffold (`file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, and `window.svg`). The current Northstar page does not depend on them; they can be replaced or removed when the product branding/assets are finalized.

## Request flows in detail

### Development sign-in

```text
SignIn form
  → POST /auth/dev-login
  → user lookup / development provisioning
  → signed Principal token
  → localStorage
  → Authorization: Bearer ... on future requests
```

### Upload and ingestion

```text
Browser upload
  → upload validation
  → local storage write
  → Document row + IngestionJob row commit
  → Redis RPUSH(document job ID)
  → worker BLPOP
  → job running / attempt increment
  → parse → chunk → stable embedding → replace chunks
  → document ready, job completed
```

If parsing or indexing fails, the worker records the error and either enqueues a retry with backoff or marks the job/document failed after three attempts. A duplicate queue delivery is safe because completed jobs are ignored and indexing replaces the document’s chunks.

### Retrieval-backed chat

```text
Chat request
  → tenant-owned conversation
  → tenant-filtered DocumentChunk query
  → local query embedding + score
  → top-k context with source labels
  → chat provider
  → persisted messages + audit event
  → answer + citation metadata
```

The tenant predicate is applied before scoring. It is not a prompt-level instruction and therefore does not depend on model compliance.

## Current intentional limitations

- Development HMAC tokens are not a production identity system.
- Local storage is not object storage and has no retention/virus-scanning pipeline yet.
- PDF parsing and OCR are deferred.
- Embeddings are local hashed word vectors, not semantic provider embeddings.
- Vector search is application-side JSON scoring and will not scale like pgvector/ANN search.
- The worker is a simple single-process Redis consumer; production deployment needs process supervision, concurrency controls, metrics, and recovery runbooks.
- The frontend has a development sign-in and local-storage token model, not a production session/identity integration.
- Streaming chat, evaluation persistence, hybrid search, reranking, tools, approvals, production identity, observability, and MCP remain later phases.

## Useful commands

From the repository root on Windows PowerShell:

```powershell
.\scripts\dev.ps1
```

From `apps/api` after activating `.venv`:

```powershell
alembic upgrade head
python -m uvicorn main:app --reload --port 8000
python -m worker
```

From `apps/web`:

```powershell
npm ci
npm run dev
npm run build
npm run lint
```

From the repository root:

```powershell
python scripts\evaluate_rag.py
```
