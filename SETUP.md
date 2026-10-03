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
| PostgreSQL | Relational application data | `localhost:5432` |
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

Install the backend dependencies once `pyproject.toml` exists:

```bash
pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn app.main:app --reload --port 8000
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

Create a local `.env` file from `.env.example` when that template is added. Keep secrets out of Git.

Suggested initial variables:

```env
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/ai_operations
REDIS_URL=redis://localhost:6379/0

LLM_API_KEY=replace-me
LLM_MODEL=replace-with-a-chat-model
EMBEDDING_MODEL=replace-with-an-embedding-model

JWT_SECRET=replace-with-a-long-random-development-secret
```

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
git clone <repository-url>
cd ai-product
python --version
node --version
npm --version
docker --version
docker compose version
```

When `.env.example` is added, create the local environment file. Use `cp .env.example .env` on macOS/Linux or Git Bash, and `Copy-Item .env.example .env` in Windows PowerShell. Never commit `.env` or real API keys.

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
uvicorn app.main:app --reload --port 8000
```

In a third terminal, start the web app:

```bash
cd apps/web
npm ci
npm run dev
```

Use `npm install` only when intentionally changing dependencies and regenerating `package-lock.json`. Put `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local`.

Check the API at `http://localhost:8000/health`, `http://localhost:8000/ready`, and `http://localhost:8000/docs`. Stop local services with `docker compose down`.

## Current scaffold check

Until the API, frontend, and Compose files are added, validate the checkout with:

```bash
git status
git ls-files
```

Do not expect `pytest`, `uvicorn`, `npm run dev`, or `docker compose up` to work until their corresponding project files have been added.
