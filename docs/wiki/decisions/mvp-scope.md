# MVP Scope Decisions

Date: 2026-11-19. These were confirmed with the product owner to shape the MVP phase plan.

## Boundary
- **MVP = README Milestones 1–5.** End-to-end: a feature progresses from requirements through implementation, tests, review, and a completed pull request.
- **Out of MVP:** staging deployment, production release, quality-gate framework, knowledge/context service, evaluation engine, RBAC.

## Deliverables
- An SRS (functional + non-functional requirements).
- Individual phase docs under `docs/plan/phase-XX-*.md`.
- A planning wiki under `docs/wiki/`.

## Technology adapters (MVP)
- Build three adapters: **Spring Boot (Java)**, **Laravel (PHP)**, **Next.js (TypeScript)**.
- The MVP demonstration project uses **Next.js** (aligns with the platform's own stack).

## Human approval gates (MVP)
- **Plan approval** only (after architecture, before development begins). Milestone and production gates are deferred.

## Parallel development (MVP)
- Up to **2 concurrent developers** on separate branches, to prove the parallel-execution rules.

## Git hosting (MVP)
- **GitHub** first (supports PRs, which the demo needs).

## Local model server (MVP)
- **Ollama** (OpenAI-compatible endpoint).

## External model provider (MVP)
- **Provider-agnostic** OpenAI-compatible endpoint; the user supplies a key.

## Users (MVP)
- **Single-user** platform operator. No RBAC.

## Supersedes
- Earlier ambiguous scope in README Sections 20 and 21.