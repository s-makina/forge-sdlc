# Phase 1 — Foundation and Infrastructure

**Goal:** A running, reproducible development environment plus the platform's control-plane skeleton (projects, repos, audit).

**Depends on:** nothing.\
**Precedes:** Phase 2 and Phase 3.\
**Reference:** SRS FR-1, FR-9, NFR-4, NFR-6.

---

## 1.1 Repository, tooling, and CI conventions

**What will be done**
- Establish the monorepo layout from the README §17 (`apps/`, `services/`, `packages/`, `infrastructure/`, …).
- Add root-level tooling: `package.json`/`pnpm-workspace.yaml` for JS/TS, `pyproject.toml`/`uv` or poetry for Python, `.editorconfig`, `.prettierrc`, ESLint config.
- Add `AGENTS.md` and `CODING_STANDARDS.md` at the root to steer agents and reviewers.
- Add a GitHub Actions CI pipeline: lint, typecheck, unit tests, and a build on push/PR.

**Acceptance criteria**
- A clean clone builds and passes lint/typecheck/unit tests with one command per language.
- CI runs the same checks in the repo.

## 1.2 Docker Compose development environment

**What will be done**
- Root `docker-compose.yml` (dev profile) wiring: dashboard, API, Postgres, Redis, Temporal (server + UI), a local model server (Ollama), and optional object storage.
- `.env.example` with all referenced variables (no secrets).
- A compose override for local development (hot reload) vs production.

**Acceptance criteria**
- `docker compose up` starts every core service; healthchecks pass.
- The dashboard and API are reachable through a reverse proxy at known local URLs.

## 1.3 PostgreSQL and Redis

**What will be done**
- Compose services for Postgres and Redis with persistence volumes and healthchecks.
- A schema-migration tool (Alembic) wired into the FastAPI app.
- Initial tables: `users`, `projects`, `repositories`, plus an audit event table (see 1.8).
- A Redis client wired for caching and transient coordination.

**Acceptance criteria**
- Migrations run on startup; the schema is applied to a fresh volume.
- Postgres and Redis respond to the app.

## 1.4 FastAPI application structure

**What will be done**
- Modular monolith layout: `apps/api/` with routers per domain (projects, agents, tasks, workflows, models, approvals).
- Settings management (pydantic-settings), dependency-injection container, and a DB session dependency.
- Health endpoint and structured JSON error handling.
- OpenAPI schema generated automatically.

**Acceptance criteria**
- The API boots, serves `/health`, and exposes OpenAPI at `/docs`.

## 1.5 Next.js dashboard shell

**What will be done**
- `apps/dashboard/` Next.js App Router app with the 12 main areas from README §18 as route shells.
- A layout with navigation, theme, and an API client that targets the FastAPI base URL.
- Stub pages returning placeholder content for non-MVP areas.

**Acceptance criteria**
- The dashboard loads and navigates across all route areas.

## 1.6 Authentication (single-user)

**What will be done**
- Single-operator sign-in (email/password or a configured shared token).
- Session handling (HTTP-only cookie) and a server-side auth dependency on the API.
- A `users` table and a bootstrap operator account.

**Acceptance criteria**
- Only authenticated requests reach protected API routes; the dashboard enforces login.

## 1.7 Project management

**What will be done**
- `projects` and `repositories` resources: create, list, update, deactivate.
- Repository records store URL, default branch, and adapter detection status.
- API routes + dashboard Project page.

**Acceptance criteria**
- A user creates a project enterprising its repo; it appears in the dashboard (FR-1, FR-9).

## 1.8 Audit logging foundation

**What will be done**
- An `audit_logs` table and a lightweight write-path used by protected mutations.
- Enrich logs with actor, action, entity, timestamp.
- Dashboard "activity" list on the Overview page.

**Acceptance criteria**
- Creating a project writes an audit record visible in the dashboard (NFR-6).

---

## Exit criteria (Phase 1)
A developer can start the whole environment with one command and create/manage projects through the API and dashboard, with audit events recorded.