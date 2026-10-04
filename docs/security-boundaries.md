# Security boundaries

This document records the current security controls and the remaining production assumptions for the platform.

## Tenant isolation

- Authenticated principals are revalidated against the active database user on every request.
- Document, chunk, conversation, message, approval, and task access is scoped by `tenant_id` in application queries.
- Retrieval applies the tenant predicate before scoring.
- Tool handlers receive the authenticated principal and must perform their own tenant-scoped queries.
- Approval execution re-checks tenant ownership and administrator authorization.

## Untrusted content

- Uploaded bytes, filenames, model responses, tool arguments, and retrieved document text are untrusted.
- Storage paths are resolved beneath the configured storage root and reject traversal.
- Uploads enforce size, extension/content-type, non-empty content, and PDF signature checks.
- Retrieved text is placed in a clearly delimited source context and explicitly treated as data, not instructions.
- Tool arguments are schema-validated before execution and tool results are labeled as untrusted when returned to the model.

## Side effects

- Read-only tools are tenant-scoped, role-checked, time-limited, and capped per request.
- `task.create` proposals create a pending approval and never execute directly from model output.
- Approval requests expire, are single-use, carry an idempotency key, and are re-authorized at execution.
- Approval transitions and tool outcomes are audited without recording raw tool arguments.

## Abuse and browser controls

- Redis-backed rate limits cover login, chat, uploads, and approvals, with a bounded local fallback.
- API responses include content-type sniffing, framing, referrer, permissions, and production HSTS headers.
- Error responses use safe machine-readable messages and do not expose provider or exception details.

## Production requirements

- Replace development bearer-token/local-storage authentication with a managed identity/session design.
- Use managed secrets and rotate authentication/provider credentials.
- Keep Redis available as a shared rate-limit store; the local fallback is not a multi-instance security boundary.
- Add dependency scanning, security regression coverage, malware scanning, retention/redaction policy, and incident runbooks before production deployment.
