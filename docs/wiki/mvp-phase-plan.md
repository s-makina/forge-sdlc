# ForgeSDLC — MVP Phase Plan

**Scope:** README Milestones 1–5. End-to-end proof of a feature from requirements through a completed pull request.
**Reference:** SRS in `docs/wiki/srs.md`; scope decisions in `docs/wiki/decisions/mvp-scope.md`.

Each phase below is expanded into its own document under `docs/plan/`.

---

## Phase 1 — Foundation and Infrastructure

**Goal:** A running, reproducible development environment and the platform's control-plane skeleton.

**Sub-phases**
1.1 Repository, tooling, and CI conventions
1.2 Docker Compose development environment
1.3 PostgreSQL and Redis
1.4 FastAPI application structure
1.5 Next.js dashboard shell
1.6 Authentication (single-user)
1.7 Project management
1.8 Audit logging foundation

**Exit criteria:** A developer can start the whole environment with one command and create/manage projects through the API and dashboard.

---

## Phase 2 — Agent and Model Management

**Goal:** Administrators can define versioned agents and connect local + external models.

**Sub-phases**
2.1 Agent registry data model
2.2 Versioned agent definitions
2.3 Skills and tool registry
2.4 Model provider configuration
2.5 LiteLLM integration
2.6 Logical model profiles
2.7 Provider health and capability checks

**Exit criteria:** An admin can register an agent with a model profile and see provider health.

---

## Phase 3 — Docker Execution Engine

**Goal:** A coding agent can safely run a bounded task against a real repository in an isolated workspace.

**Sub-phases**
3.1 Execution manager service
3.2 Workspace provisioning and lifecycle
3.3 Repository cloning and branch management
3.4 OpenHands runtime integration
3.5 Terminal and test execution
3.6 Resource and network policies
3.7 Log and artefact collection
3.8 Cleanup and recovery

**Exit criteria:** A single coding agent completes a bounded task against a repository with captured logs and a commit/patch.

---

## Phase 4 — Workflow Orchestration

**Goal:** A durable workflow can coordinate multiple tasks and agents.

**Sub-phases**
4.1 Temporal integration
4.2 Workflow templates
4.3 Task creation and dependencies
4.4 Assignment and scheduling
4.5 Parallel execution rules
4.6 Retry, timeout, cancellation, recovery
4.7 Workflow monitoring

**Exit criteria:** A workflow coordinates multiple dependent tasks across agents, with recoverable durable state.

---

## Phase 5 — First Autonomous SDLC Team

**Goal:** A real feature progresses from requirements through implementation, tests, review, and a completed PR.

**Sub-phases**
5.1 Agent roles: Business Analyst, Project Manager, Software Architect, Developer, QA Engineer, Code Reviewer
5.2 Feature-development workflow wiring
5.3 Requirements → architecture → plan pipeline
5.4 Plan approval gate
5.5 Parallel development and integration
5.6 Automated testing
5.7 Independent code review
5.8 Pull request delivery

**Exit criteria:** The MVP demonstration scenario passes end-to-end against the Next.js demo project.

---

## Dependencies and sequencing

- Phase 1 must precede everything (control plane and env).
- Phase 2 requires Phase 1 (registry + providers live in the control plane).
- Phase 3 requires Phase 1 (execution needs projects/repos) and is largely independent of Phase 2.
- Phase 4 requires Phases 2 and 3 (it orchestrates agents running in workspaces).
- Phase 5 requires Phase 4 and the three technology adapters.

Parallelizable tracks: **Phase 2** (agent/model) and **Phase 3** (execution) can proceed in parallel after Phase 1.

---

## Success criteria

- The MVP acceptance scenario in `docs/wiki/srs.md` §4 passes.
- A feature reaches a completed pull request with passing tests, a review report, and a recorded plan approval, inside isolated workspaces.