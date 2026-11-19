# Phase 4 — Workflow Orchestration

**Goal:** A durable workflow can coordinate multiple dependent tasks across agents, with retries, timeouts, cancellation, recovery, and monitoring.

**Depends on:** Phase 2 and Phase 3.\
**Precedes:** Phase 5.\
**Reference:** SRS FR-6, NFR-2, NFR-6; README §10, §11.

---

## 4.1 Temporal integration

**What will be done**
- Stand up Temporal server + UI (already in Phase 1 compose) and a Python Temporal client/worker.
- Wire the orchestrator service to submit and manage workflows.
- Map durable workflow state to Temporal; agent conversations are not the record of progress.

**Acceptance criteria**
- A workflow is submitted and its durable state is visible in the Temporal UI.

## 4.2 Workflow templates

**What will be done**
- A template system for reusable workflow sequences (README §10.2).
- MVP templates: **feature-development** (primary), plus **bug-fix** and **refactoring** stubs.
- Each template defines stage transitions exceptionally, with dependencies.

**Acceptance criteria**
- A workflow instance is created from a template with typed inputs.

## 4.3 Task creation and dependencies

**What will be done**
- A `tasks` first-class record: title, description, type, priority, acceptance criteria, dependencies, assigned role, repo + target branch, skills, model profile, execution limits, status (README §11).
- CRUD + status lifecycle: `draft, ready, assigned, in_progress, blocked, review, failed, completed, cancelled`.
- Task dependency wiring (`task_dependencies`).

**Acceptance criteria**
- A plan creates tasks with dependencies; status transitions are enforced and recorded.

## 4.4 Assignment and scheduling

**What will be done**
- Assign tasks to agent roles based on the plan and agent registry.
- Schedule ready tasks respecting dependencies.

**Acceptance criteria**
- A ready task with no unmet dependencies is scheduled to the correct agent role.

## 4.5 Parallel execution rules

**What will be done**
- Enforce the README §11.1 rules: parallel work only when interfaces, ownership, and dependencies are clear.
- MVP allows up to **2 concurrent developers** on separate branches (agreed scope).
- Use separate branches/worktrees; avoid multiple agents editing the same tree without coordination.

**Acceptance criteria**
- Two independent tasks run concurrently on separate branches without file collisions.

## 4.6 Retry, timeout, cancellation, recovery

**What will be done**
- Bounded retries per activity with backoff.
- Per-activity and per-workflow timeouts.
- Cancellation propagation into running executions.
- Idempotent activities where possible; recovery after worker/infra failure.

**Acceptance criteria**
- A failed activity retries within bounds; a timed-out task cancels its workspace; a crashed worker resumes without loss.

## 4.7 Workflow monitoring

**What will be done**
- Dashboard view of workflow instances, stage status, retries, and failure details.
- Execution history surfaced alongside tasks and executions.

**Acceptance criteria**
- A workflow's full progress and history are visible in the dashboard (FR-9, NFR-6).

---

## Exit criteria (Phase 4)
A durable workflow coordinates multiple dependent tasks across agents, supports two concurrent developers, and recovers after failure — with full monitoring.