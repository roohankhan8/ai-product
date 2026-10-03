# AI Operations Platform — Setup Guide

This repository is the starting point for a multi-tenant AI operations platform. The planned system combines a Next.js web app, a FastAPI backend, PostgreSQL, Redis/Celery workers, retrieval-augmented generation, agent tools, and an MCP server.

The project is intended to be built progressively. Start with the API and database, then add LLM features, RAG, agents, workers, the frontend, and production infrastructure.

## Prerequisites

Install the following tools:

- Git
- Python 3.12 or newer
- Node.js 20 or newer and npm
- Docker Desktop with Docker Compose
- PostgreSQL 16 or newer (Docker is recommended for local development)
- Redis 7 or newer (Docker is recommended)

You will also eventually need an API key for an LLM provider that supports chat completions and embeddings.

Verify the core tools:

```bash
python --version
node --version
npm --version
docker --version
docker compose version
```

## Planned repository layout

The target structure is a monorepo:

```text
apps/
├── api/          # FastAPI application
├── web/          # Next.js frontend
├── worker/       # Celery/background jobs
└── mcp-server/   # MCP tools and resources
packages/         # Shared types and prompts
infrastructure/   # Docker, Compose, AWS, and Azure assets
evals/            # RAG and agent evaluation datasets
docs/             # Architecture, security, decisions, and runbooks
scripts/          # Developer utilities
```

The current repository contains the project plan in [`IDEA.md`](IDEA.md); application code can be added as each phase is implemented.

## Local services

When the Docker Compose configuration is added, local development should use:

| Service | Purpose | Default address |
|---|---|---|
| PostgreSQL | Relational application data | `localhost:5433` |
| Redis | Cache, queue, and rate limits | `localhost:6379` |
| API | FastAPI backend | `http://localhost:8000` |
| Web | Next.js frontend | `http://localhost:3000` |

Start the infrastructure with:

```bash
docker compose up -d postgres redis
```

Stop it with:

```bash
docker compose down
```

## Backend setup

Create and activate a virtual environment:

```bash
cd apps/api
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the backend dependencies:

```bash
pip install -e ".[dev]"
alembic upgrade head
```

Run the API locally:

```bash
uvicorn main:app --reload --port 8000
```

Useful endpoints should include:

- `GET /health` — process health
- `GET /ready` — dependency readiness
- `GET /docs` — OpenAPI documentation

## Frontend setup

Once the Next.js app exists:

```bash
cd apps/web
npm install
npm run dev
```

The frontend should use an environment variable for the backend URL, for example:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Environment variables

Create `apps/api/.env` from `apps/api/.env.example` if you need local overrides. The API reads `.env` from its working directory; keep it out of Git.

Suggested initial variables:

```env
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://devuser:devpassword@localhost:5433/devdb
REDIS_URL=redis://localhost:6379/0

LLM_API_KEY=replace-me
LLM_MODEL=replace-with-a-chat-model
EMBEDDING_MODEL=replace-with-an-embedding-model

AUTH_SECRET=replace-with-a-long-random-development-secret
STORAGE_DIR=./storage
MAX_UPLOAD_BYTES=10485760
LLM_PROVIDER=gemini
LLM_API_KEY=replace-with-your-gemini-api-key
LLM_MODEL=gemini-2.0-flash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/models
LLM_TIMEOUT_SECONDS=30
```

## Local authentication

The initial local flow uses a signed bearer token. Seed a user in PostgreSQL, call
`POST /auth/dev-login` with `{ "email": "user@example.com" }`, then send the returned
token as `Authorization: Bearer <token>`. `GET /auth/me`, `GET /tenant/users`, and
`GET /tenant/documents` are authenticated and tenant-scoped. This development flow is
not a production identity provider; replace it with OIDC before production deployment.

Authenticated document metadata is available under `/api/v1/documents`. It supports
list, create, detail, update, and delete operations.

Upload a PDF, plain-text, or Markdown file with `POST /api/v1/documents/upload` using
the multipart field `file`. Files are stored locally under `STORAGE_DIR`, limited by
`MAX_UPLOAD_BYTES` (10 MiB by default), and can be downloaded through the authenticated
`GET /api/v1/documents/{id}/download` endpoint.

Basic chat is available at `POST /api/v1/chat` with `{ "message": "..." }`. Select
the provider with `LLM_PROVIDER=gemini`, `LLM_PROVIDER=mock`, or
`LLM_PROVIDER=openai_compatible`. Gemini uses `LLM_API_KEY`, `LLM_MODEL`, and
`LLM_BASE_URL`; the mock provider requires no API key.

For production, provide secrets through a managed secret store rather than committing `.env` files.

## Recommended implementation order

1. Build the Python domain, service, repository, and infrastructure layers.
2. Add FastAPI routes, validation, authentication, error handling, and tests.
3. Add PostgreSQL models, migrations, tenant isolation, and audit logs.
4. Add a provider abstraction with real and mock LLM implementations.
5. Add document parsing, chunking, embeddings, retrieval, and citations.
6. Add multi-tenancy and access-controlled retrieval.
7. Add manually orchestrated tools and human approval for sensitive actions.
8. Introduce LangGraph only after the manual agent workflow is understood.
9. Add the MCP server, Redis, Celery, and document-ingestion jobs.
10. Add evaluation, observability, security testing, the Next.js UI, Docker, CI/CD, and cloud deployment.

Do not allow the LLM to modify the database directly. Tool calls must pass through application authorization, parameter validation, confirmation rules, and audit logging.

## Baseline RAG

After uploading a UTF-8 `.txt` or `.md` document, call
`POST /api/v1/documents/{id}/index`. Chat retrieves top matching chunks from the
authenticated user's tenant and returns citation metadata with the answer. The
baseline uses deterministic local word vectors stored as JSON in PostgreSQL so it
needs no new service. pgvector is the preferred next step for database-native
indexed search; a hosted vector service is deferred because it adds operational
and tenant-boundary complexity. PDF upload remains supported for storage and
download, but PDF parsing/OCR is deferred.

## Development commands

Expected commands as the project is implemented:

```bash
# Run backend tests
pytest

# Run frontend checks
npm run lint
npm run build

# Run the full local stack
docker compose up --build
```

## Development principles

- Keep tenant isolation in the application and data layers, never in prompts.
- Keep the database as the source of truth.
- Provide mock LLM and external-service implementations for tests.
- Make background jobs retryable and idempotent.
- Record request IDs, tenant IDs, model usage, latency, costs, retrieval results, tool calls, and errors.
- Maintain evaluation datasets for retrieval, generation, and agent behavior.
- Test prompt injection, indirect injection, unauthorized tools, data leakage, malicious uploads, SSRF, and rate-limit abuse.

For the complete product roadmap and architecture rationale, see [`IDEA.md`](IDEA.md).

## First-time setup commands

The repository is currently a scaffold. Run these commands from the repository root after cloning:

```bash
python --version
node --version
npm --version
docker --version
docker compose version
```

Create the API's local environment file from the repository root when you need to override defaults:

```bash
cp apps/api/.env.example apps/api/.env      # macOS/Linux/Git Bash
Copy-Item apps/api/.env.example apps/api/.env  # Windows PowerShell
```

Never commit `.env` or real API keys.

## Development workflow

Use separate terminals once the corresponding project files exist:

```bash
# Terminal 1 - infrastructure
docker compose up -d postgres redis

# Terminal 2 - API
cd apps/api
python -m venv .venv
```

Activate the backend environment in Windows PowerShell with `.venv\Scripts\Activate.ps1`, or on macOS/Linux with `source .venv/bin/activate`, then run:

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn main:app --reload --port 8000
```

In a third terminal, start the web app:

```bash
cd apps/web
npm ci
npm run dev
```

Use `npm install` only when intentionally changing dependencies and regenerating `package-lock.json`. Put `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local`.

Check the API at `http://localhost:8000/health`, `http://localhost:8000/ready`, and `http://localhost:8000/docs`. Stop local services with `docker compose down`.

## Checkout information

The API, frontend starter, and local Compose services are present. To inspect local changes and tracked files:

```bash
git status
git ls-files
```

Use the setup and development commands above to install and run the current components.
