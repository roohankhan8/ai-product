# AI Operations Platform

An AI operations assistant for company knowledge and controlled business workflows. The long-term product combines a web app, API, document search with citations, authorized tools, and human approval for consequential actions.

The project is being implemented in stages. See [`IDEA.md`](IDEA.md) for the product and learning goals, [`PLAN.md`](PLAN.md) for implementation phases and acceptance criteria, and [`SETUP.md`](SETUP.md) for detailed setup instructions.

## Current status

- FastAPI API with `/health` and `/ready`, structured errors, request IDs, and development authentication
- PostgreSQL 16 and Redis 7 in Docker Compose
- Async SQLAlchemy persistence with tenant-scoped models and five Alembic migrations
- Password-protected development login and seeded admin support
- Document upload, local storage, durable Redis ingestion, retry handling, and baseline retrieval with citations
- Next.js workspace for sign-in, chat, conversations, document upload, and indexing status

The next milestone is verification and hardening of this document-to-cited-answer slice: CI checks, tenant/auth security cases, operational visibility, and production-ready session handling. Controlled agent tools come after that foundation.

## Quick start

Prerequisites: Python 3.12+, Node.js 20+ with npm, and Docker Desktop with Compose.

Start local infrastructure from the repository root:

```bash
docker compose up -d postgres redis
```

PostgreSQL is intentionally available on host port `5433` (`localhost:5433`); Redis is at `localhost:6379`.

In a second terminal, install and run the API:

```bash
cd apps/api
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in Windows PowerShell or `source .venv/bin/activate` on macOS/Linux. Then run:

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn main:app --reload --port 8000
```

In a third terminal, install and run the web app:

```bash
cd apps/web
npm ci
npm run dev
```

The API is at <http://localhost:8000>, its OpenAPI docs are at <http://localhost:8000/docs>, and the web app is at <http://localhost:3000>. The health endpoint is <http://localhost:8000/health>.

Stop the local containers from the repository root:

```bash
docker compose down
```

## Repository map

```text
apps/api/       FastAPI backend and migrations
apps/web/       Next.js frontend
docs/           Architecture notes, decisions, and operational docs
evals/          AI and retrieval evaluation datasets
infrastructure/ Deployment and infrastructure assets
packages/       Shared packages
scripts/        Developer utilities
```

## Development

Keep tenant authorization in application and data access code. Treat documents and model output as untrusted, and route every tool action through validation, authorization, and audit logging. Prefer deterministic provider fakes in tests so normal development does not require a live LLM key.

The repository CI currently runs API linting plus web lint and build checks. Tests are intentionally not part of the current local workflow until the project explicitly enables them.
