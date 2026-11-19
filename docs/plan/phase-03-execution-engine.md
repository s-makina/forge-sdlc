# Phase 3 — Docker Execution Engine

**Goal:** A coding agent can safely run a bounded task against a real repository in an isolated Docker workspace, with captured logs and a resulting commit/patch.

**Depends on:** Phase 1.\
**Runs parallel to:** Phase 2.\
**Precedes:** Phase 4.\
**Reference:** SRS FR-5, NFR-1, NFR-3; README §12.

---

## 3.1 Execution manager service

**What will be done**
- An `execution-manager` service (FastAPI worker) owning the Docker workspace lifecycle.
- API surface: request execution, poll status, fetch logs/artefacts, cancel, cleanup.
- A task-record model linking executions to a task and project.

**Acceptance criteria**
- The orchestrator can request and observe an execution through a stable API.

## 3.2 Workspace provisioning and lifecycle

**What will be done**
- Provision an isolated container per execution with a unique execution id.
- Each workspace has dedicated repo checkout, branch/worktree, limits, network policy, scoped credentials, and cleanup policy (README §12.2).
- Lifecycle states: created → ready → running → succeeded | failed → cleaning → done.

**Acceptance criteria**
- A workspace is created, used, and cleaned up; lifecycle is observable.

## 3.3 Repository cloning and branch management

**What will be done**
- Clone or update the project repository into the workspace.
- Create/checkout a task branch (e.g. `task/<execution-id>`).
- Later, push branch + open PR (Phase 5).

**Acceptance criteria**
- A workspace starts with the correct repo state on the task branch.

## 3.4 OpenHands runtime integration

**What will be done**
- Wire the OpenHands Software Agent SDK as the coding runtime inside the workspace.
- Provide the coding agent with repository read/write, terminal, and test-runner tools.
- Enforce agent permissions (no merge, no production access) from the agent registry.

**Acceptance criteria**
- A coding agent can edit files and run commands inside the workspace through OpenHands.

## 3.5 Terminal and test execution

**What will be done**
- Execute build, test, and lint commands sourced from the project's technology adapter.
- Capture exit codes and output as structured results.

**Acceptance criteria**
- Running the adapter's test command yields captured, attributable results (FR-7.1).

## 3.6 Resource and network policies

**What will be done**
- Enforce CPU, memory, disk, and time limits per workspace (README §12.3).
- Restrict network access by policy (default: minimal; allowlist for package registries).
- Run as non-root; never mount the host Docker socket into agent containers.

**Acceptance criteria**
- A runaway container is capped and cannot reach the Docker management API.

## 3.7 Log and artefact collection

**What will be done**
- Capture execution events, tool calls, commands, diffs, commits, and logs.
- Store artefacts (test reports, patches) in S3-compatible object storage.

**Acceptance criteria**
- An execution's full history is retrievable and artefacts are preserved.

## 3.8 Cleanup and recovery

**What will be done**
- Clean up or archive workspaces and scoped credentials after execution.
- Recover workspaces/credentials after worker or infra failure.
- Bounded retry on transient failures; escalate on repeated failure.

**Acceptance criteria**
- After a crash, no orphaned workspaces or credentials remain; execution state recovers.

---

## Exit criteria (Phase 3)
A single coding agent completes a bounded task against a repository with captured logs and a resulting commit/patch, inside an isolated, policy-enforced workspace.