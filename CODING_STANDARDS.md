# CODING_STANDARDS.md — ForgeSDLC Coding Standards

These standards apply to all code in this repository. They exist to make the codebase correct, consistent, and navigable for both humans and AI agents.

## General

- Prefer clarity over cleverness. Write code that reads plainly.
- Keep changes minimal and focused. Do not reformat unrelated code.
- Favor small, single-responsibility modules and functions.
- Name things for what they are: variables, functions, modules, and routes.
- Do not add comments that restate what the code already says. Add comments only for non-obvious decisions and rationale.

## Python (apps/api, services/)

- Follow PEP 8.
- Use type hints on all public functions and methods.
- Use `pydantic` models for API schemas and settings; validate input at the boundary.
- Use SQLAlchemy 2.0 style (`Mapped`, `mapped_column`) for ORM models.
- Run `ruff` for linting and formatting; run `mypy` for type checking.
- Organize FastAPI apps by domain: one router module per domain, a package for shared deps.
- Never log secrets, tokens, or passwords. Redact credentials.
- Use `pytest` for tests; name tests with a `test_` prefix.

## TypeScript / React (apps/dashboard)

- Use TypeScript with strict mode; avoid `any` unless a clear reason exists.
- Prefer functional React components with hooks. No class components unless necessary.
- Use Next.js App Router conventions (route groups, layouts, server components by default).
- Use the shared API client for all backend calls; never hardcode fetch URLs inline.
- Run ESLint and Prettier before finishing.

## Infrastructure

- Validate the environment with `docker compose config` before applying changes.
- Never mount the Docker socket into agent containers.
- Never expose the Docker management API publicly.
- Keep secrets out of compose files and source control; use `.env` / secret references.

## Tests

- Cover the code you touch. Prefer unit tests for logic and integration tests for boundaries.
- Do not add dependencies purely to satisfy coverage thresholds.
- Every protected mutation should have an accompanying test when feasible.

## Git

- Write clear, imperative commit messages.
- Do not commit secrets, `.env`, or generated build output.