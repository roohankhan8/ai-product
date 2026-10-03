# Implementation Plan

This plan turns the product and learning roadmap in [`IDEA.md`](IDEA.md) into an implementation sequence for this repository. Each stage should leave the project runnable and should be completed with tests, documentation, and a short record of the design decisions that matter.

## Product outcome

Build a single-company AI Operations Assistant first. Authenticated employees can upload internal documents, ask questions that are answered with citations, and use explicitly authorized tools to perform limited business actions. The system must preserve tenant boundaries, require human approval for consequential actions, and record enough evidence to investigate failures and security incidents.

The architecture should grow from a modular FastAPI application and Next.js UI. Add workers, agent frameworks, MCP, cloud deployment, and multimodal features only after the preceding capability has a clear use case and a working baseline.

## Current repository baseline

- `apps/api/main.py` exposes FastAPI `/health` and `/ready` endpoints; `core/` and `routes/` separate shared runtime concerns and HTTP routes.
- `apps/api/pyproject.toml` defines the API dependencies, including async SQLAlchemy, Alembic, asyncpg, and psycopg for migrations.
- `apps/api/models.py`, `database.py`, and `alembic/versions/` define the initial relational schema, async session setup, and reversible migration.
- `docker-compose.yml` starts PostgreSQL 16 and Redis 7. PostgreSQL is exposed on host port `5433`.
- `apps/web/` contains a Next.js starter application and npm lockfile.
- `IDEA.md` describes the target system, learning sequence, and technology areas.

The Postgres host mapping to port `5433` is intentional and should be preserved. Keep setup examples and environment defaults aligned with the Compose credentials and database name; keep local secrets out of version control.

## Delivery rules

1. Work in the phase order below unless a dependency clearly requires a change.
2. At each phase, keep a usable end-to-end slice; avoid introducing infrastructure for a later phase early.
3. Define tests alongside behavior. Use deterministic fakes for LLMs, tools, and external services.
4. Treat tenant identity and authorization as application/data-layer invariants. Never rely on prompts for access control.
5. Make external side effects explicit, validated, auditable, and approval-gated where appropriate.
6. Update `SETUP.md` and relevant docs in the same change that makes a command or workflow available.
7. Keep decisions in `docs/decisions/` when they constrain future work, especially database, vector search, auth, provider, and deployment choices.

## Phases and acceptance criteria

### 0. Make the starter reliable

**Scope:** Bring the existing API, web app, database, and Redis starters into agreement.

- Preserve the intentional Postgres host port `5433`; align credentials, commands, and environment variable names across setup docs and Compose.
- Add an API environment template and ensure local secrets are ignored by Git.
- Make the API installable from `apps/api` and ensure the documented Uvicorn command works.
- Add basic API tests for `/health` and `/ready`.
- Confirm the Next.js app installs from its lockfile and runs locally.
- Add a concise root README or keep `SETUP.md` as the single authoritative local setup guide.

**Done when:** A new contributor can follow the setup guide, start Postgres/Redis, run both apps, and verify the health endpoint without guessing configuration.

### 1. Python foundation and application boundaries

**Scope:** Establish a clear, testable Python structure before adding product behavior.

- Keep `apps/api/` flat for the current small service (`main.py`, `core/`, `routes/`, and focused persistence modules); add domain, services, or repositories when behavior needs those boundaries.
- Define typed settings and structured logging; validate required settings at startup.
- Add error handling, request IDs, and a consistent API response/error convention.
- Keep domain logic independent of FastAPI and persistence.
- Configure Ruff and pytest conventions; add focused unit tests.

**Done when:** Domain/service tests run without a database or network, and the app has a documented local run and check workflow.

### 2. Relational persistence and migrations

**Scope:** Add PostgreSQL persistence for the first product entities.

- Use SQLAlchemy 2.x async sessions with asyncpg for API requests; use psycopg synchronously for Alembic commands so migrations remain a normal one-shot CLI process.
- Configure database sessions and lifecycle handling.
- Design initial entities: tenant, user, document metadata, conversation, message, task, and audit event. Add only entities needed by the first vertical slice.
- Implement Alembic metadata wiring, an initial migration, and migration checks in CI.
- Add constraints, indexes, timestamps, and transaction boundaries.
- Add repository tests against a disposable PostgreSQL instance or isolated test database.

**Done when:** A clean database can be created with migrations, repositories persist and retrieve records, and test data is isolated from local development data.

### 3. Identity, authentication, and tenant isolation

**Scope:** Establish who is making each request and which tenant owns the data.

- Define tenant and user identity, membership, and role rules.
- Implement a narrow authentication flow suitable for local development, then select a production identity approach.
- Resolve the authenticated principal in FastAPI dependencies.
- Scope every tenant-owned repository operation by the principal's tenant; avoid unscoped query helpers.
- Add authorization checks for reads and writes, plus audit events for security-sensitive operations.
- Test cross-tenant access denial for each endpoint and repository boundary.

**Done when:** Automated tests prove a user cannot list, read, modify, or infer another tenant's records.

### 4. First operational API slice

**Scope:** Implement the basic user and document metadata workflows without AI processing.

- Add versioned API routers and Pydantic request/response schemas.
- Implement tenant-scoped document metadata list/detail/delete behavior and conversation/task primitives as justified by the UI.
- Define pagination, validation, not-found behavior, and stable error responses.
- Generate and inspect the OpenAPI contract.
- Add API tests for happy paths, invalid input, authentication, and authorization.

**Done when:** The API supports a complete authenticated CRUD path for the first selected resource, with tenant tests and documented API behavior.

### 5. File upload and document lifecycle

**Scope:** Accept documents safely and track processing state.

- Set allowed file types, size limits, and upload quotas.
- Store file bytes outside the relational database through a storage interface; use local storage in development and select a production object store later.
- Persist metadata, tenant ownership, checksum, and lifecycle state.
- Validate file signatures where practical; never trust client-provided filenames or MIME types.
- Add upload, status, download/access, and deletion flows with tenant authorization.
- Record upload and lifecycle events.

**Done when:** An authorized user can upload a permitted file, see its state, and cannot access another tenant's file; invalid and oversized uploads are rejected safely.

### 6. LLM provider boundary and basic chat

**Scope:** Deliver a simple, observable model call before adding retrieval or agents.

- Define a small provider interface for chat generation and structured errors.
- Implement one selected hosted provider and a deterministic mock provider.
- Keep keys in environment/secret storage and redact them from logs.
- Add timeout, bounded retry, and rate/cost accounting behavior.
- Persist conversations and messages; expose a basic chat endpoint.
- Add tests for provider success, timeout, malformed output, and provider failure using fakes.

**Done when:** A user can send a message and receive a model response; tests run without a real API key, and usage/failure details are traceable.

### 7. Document parsing and baseline RAG

**Scope:** Turn uploaded text documents into searchable evidence and cited answers.

- Implement a parser interface and support a small initial set of text-based formats; defer OCR and complex formats.
- Normalize text, preserve source metadata, and chunk deterministically.
- Select an embedding provider and vector storage approach after a documented comparison of pgvector and a separate vector service.
- Store chunk ownership and metadata so tenant filters are mandatory during retrieval.
- Implement top-k vector retrieval, context construction, citation references, and a retrieval-backed answer endpoint.
- Add a small versioned evaluation set with expected sources and baseline retrieval/answer checks.

**Done when:** Answers cite the chunks that support them, retrieval is tenant-filtered at the data boundary, and tests include empty, malformed, and cross-tenant cases.

### 8. RAG quality and evaluation

**Scope:** Improve retrieval through measured iterations.

- Add metadata filters and access-control filters before expanding retrieval complexity.
- Measure hit rate/recall and ranking quality on the evaluation set.
- Add hybrid retrieval and reranking only if the baseline evaluation identifies a real gap.
- Measure citation correctness, groundedness, latency, token use, and cost.
- Keep evaluation datasets and results versioned; run a small regression suite in CI.

**Done when:** A repeatable evaluation command compares a change with the baseline and can detect material retrieval or citation regressions.

### 9. Controlled tools and manual agent loop

**Scope:** Let the model propose tool calls while application code retains control.

- Define a typed tool registry with schemas, descriptions, and permission requirements.
- Start with read-only tools over existing application data, such as knowledge search or customer lookup using seeded/sample data.
- Validate model arguments and authorize every call against the user and tenant before execution.
- Bound tool count, execution time, and loop iterations; record inputs/results with sensitive data redacted.
- Keep orchestration manual and explicit before adopting an agent framework.
- Test invalid parameters, repeated calls, denied access, and malicious tool requests.

**Done when:** Tool calls cannot bypass application authorization and every call is bounded and auditable.

### 10. Human approval for consequential actions

**Scope:** Add approval as a persisted workflow state before enabling write tools.

- Classify tools as read-only or side-effecting and define approval policy per action.
- Persist proposed action, validated arguments, requester, tenant, expiration, and status.
- Implement approve/reject and execute transitions with transaction and idempotency protection.
- Re-authorize at approval and execution time; do not trust stale permissions.
- Audit every transition and make retries safe against duplicate effects.

**Done when:** A side-effecting action cannot execute without a valid approval, and duplicate requests do not duplicate the effect.

### 11. Redis, workers, and durable ingestion

**Scope:** Move slow document processing out of web requests.

- Use Redis/Celery only when ingestion latency or retry needs justify background work.
- Define job states, idempotency keys, retry/backoff policy, and terminal failure handling.
- Create an ingestion job after upload; worker parses, chunks, embeds, indexes, and updates document status.
- Add concurrency limits and safe cleanup/reprocessing behavior.
- Test worker retries, duplicate delivery, poison inputs, and recovery after process restart.

**Done when:** Upload returns promptly, job progress is visible, retries do not create duplicate chunks, and failures are inspectable and recoverable.

### 12. Next.js product UI

**Scope:** Build the smallest usable UI over stable API contracts.

- Add sign-in/session handling consistent with the chosen auth model.
- Build document upload/list/status, cited chat, and approval/task views.
- Handle loading, empty, error, retry, and access-denied states.
- Add streaming only after the non-streaming contract is stable and evaluated.
- Keep server secrets server-side; expose only intentionally public configuration to the browser.
- Add component and end-to-end tests for critical flows and authorization-visible behavior.

**Done when:** A user can complete the core document-to-cited-answer flow and approve/reject a pending action through the UI.

### 13. Security hardening

**Scope:** Test the trust boundaries identified by `IDEA.md` against concrete abuse cases.

- Threat-model uploads, retrieval, model prompts, tool execution, tenant boundaries, and secrets.
- Test direct and indirect prompt injection; treat retrieved content as untrusted data.
- Test cross-tenant access, unauthorized tools, excessive permissions, SQL injection, SSRF, malicious files, and rate limits.
- Enforce least privilege, input validation, output handling, secure headers, and secret redaction.
- Add dependency and static security checks to CI where practical.
- Document incident-relevant audit fields and a response procedure.

**Done when:** Security regression tests cover the known attack cases and all tool side effects pass through application authorization and audit controls.

### 14. Observability and operational readiness

**Scope:** Make request and AI behavior diagnosable without leaking sensitive content.

- Propagate request/trace IDs across API, database, model, tool, and worker operations.
- Emit structured logs and metrics for latency, failures, queue age, tokens, and estimated cost.
- Add tracing with an OpenTelemetry-compatible setup and select an AI tracing/evaluation tool only when needed.
- Define readiness checks for actual required dependencies; keep liveness separate from readiness.
- Add retention and redaction rules for prompts, documents, and tool results.
- Write runbooks for migration, backup/restore, stuck jobs, provider outage, and key rotation.

**Done when:** An operator can trace a request end to end, identify dependency failures, and inspect usage/cost without exposing secrets or unrestricted document content.

### 15. MCP interoperability

**Scope:** Expose a small, safe subset of application capabilities to compatible AI clients.

- Implement an MCP server over existing application service/tool boundaries; do not duplicate business logic.
- Expose only explicitly authorized tools and document their input/output contracts.
- Carry user/tenant identity securely and apply the same authorization and audit controls as REST.
- Test tool discovery, valid invocation, invalid arguments, permission denial, and error handling.
- Document when direct REST use is preferable to MCP.

**Done when:** An MCP client can discover and invoke a permitted capability without bypassing application policy.

### 16. Docker, CI/CD, and deployment

**Scope:** Reproduce development and production environments predictably.

- Add production Dockerfiles with pinned/runtime-controlled dependencies and non-root execution.
- Extend Compose to run API and worker with health checks, networks, and persistent local data.
- Add CI for formatting/lint, type checks, unit/integration tests, migrations, and web build.
- Build and scan versioned images; deploy first to a non-production environment.
- Define secret injection, database migration/rollback strategy, smoke tests, backups, and release procedure.
- Deploy the initial cloud version to one selected platform; add another cloud only for a concrete portability or learning goal.

**Done when:** A clean CI run builds the application, and a documented deployment can be health-checked and rolled back.

### 17. Advanced capabilities: framework comparison, multimodal, offline

**Scope:** Pursue the later learning goals from `IDEA.md` only after the core product works.

- Reimplement a bounded manual workflow with LangGraph and compare persistence, branching, retries, observability, and complexity.
- Add OCR, images, audio, or speech only for a defined document/user need, with separate quality and privacy checks.
- Evaluate a local/offline model path against hosted inference for quality, latency, cost, hardware, and data handling.
- Add advanced agent memory only with explicit ownership, retention, and user deletion behavior.

**Done when:** Each advanced capability has a measured reason to exist, an evaluation, security review, and a documented decision to retain or remove it.

## Cross-cutting completion gate

Before calling a phase complete:

- Its acceptance criteria pass on a clean checkout.
- Automated tests cover normal behavior and the most important failure/security paths.
- Setup instructions and API documentation match the implementation.
- Migrations and external side effects are recoverable or idempotent where applicable.
- Logs and metrics provide useful diagnosis without leaking credentials or unrestricted user data.
- The next phase has a concrete dependency on this work; speculative work stays deferred.

## Immediate next work

1. Keep Postgres on the intentional host port (`5433`) and align `SETUP.md` and environment defaults with the Compose credentials.
2. Confirm the API installs and starts from `apps/api`, and the web app installs from its lockfile.
3. Add tests for the existing health endpoints and wire a minimal CI check.
4. Implement typed configuration and establish the persistence choice before adding database models.

For the complete product rationale and learning goals, see [`IDEA.md`](IDEA.md). For local commands, see [`SETUP.md`](SETUP.md).
