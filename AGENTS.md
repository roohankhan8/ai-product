# Repository instructions

## Project direction

- Use `IDEA.md` for product goals, `PLAN.md` for implementation order, and `SETUP.md` for local commands.
- Build the platform in small, runnable stages. Prefer the standard library and existing project dependencies before adding abstractions or packages.
- Keep API transport, application/domain behavior, persistence, and external integrations in separate modules when those responsibilities are introduced. Do not create empty placeholder layers.
- Keep tenant ownership and authorization enforced in application/data access code, never in prompts.
- Treat uploaded content, model output, and tool arguments as untrusted input.

## Working rules

- Do not write or run tests unless the user explicitly asks.
- Do not read, print, or commit local secret files such as `.env`; use `.env.example` for safe templates.
- Preserve user changes and avoid staging or reverting files unless asked.
- Keep setup documentation aligned with actual commands, environment variables, and service ports. PostgreSQL's host port `5433` is intentional.
- When adding dependencies, keep them limited to the current implementation and update the owning `pyproject.toml` or `package.json`.
