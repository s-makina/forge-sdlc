# Phase 5 — Scoping & Implementation Plan

Status: **proposed** (review before coding).
Owner: implement in thin, verifiable slices, mirroring how Phase 4 was delivered.

---

## 1. What already exists (foundations — do not rebuild)

Confirmed against the current tree:

- **Six agent roles are seeded and versioned** — `apps/api/app/seeds/agents/*.yaml`
  (business-analyst, project-manager, software-architect, developer, qa-engineer,
  code-reviewer). §5.1 is largely satisfied.
- **Three technology adapters exist** — `services/execution-manager/app/adapters/registry.py`
  defines `python`, `nextjs`, `spring-boot`, `laravel` with build/test/lint/install
  commands + detection. The Phase 5 prerequisite is in place.
- **Coding runtime + permission boundary** — `services/execution-manager/app/openhands/client.py`
  (start/edit/run/test/close) with `AgentPermissions`; merge & production access are
  always denied.
- **Phase 4 workflow surface** — `WorkflowTemplate`, `Workflow`, `WorkflowStageRun`,
  `Task`, `TaskDependency`, `TaskStatus`, scheduling (`assign_to_role`,
  `schedule_ready_tasks`, per-task `task/<id>` branches), and the durable
  Temporal orchestrator workflow.
- **`waiting_approval` status already modelled** — `WorkflowStatus.WAITING_APPROVAL`
  exists and is in the status schema.

## 2. The real gaps (the work)

| # | Where | What's missing |
|---|-------|----------------|
| G1 | `apps/api/app/routers/approvals.py` | **Plan-approval gate (5.4)**. Router is an empty placeholder. No create/list/decide endpoints, no approval record model, no approver/decision/comments/timestamp capture, no gate blocking development. |
| G2 | `apps/api` engine/scheduling/workflows wiring | **Requirements→arch→plan→approval pipeline (5.3/5.2)**. Nothing drives the stage sequence automatically or connects task/agent/execution/approval records through it. |
| G3 | `services/execution-manager` runtime/test | **Test gating (5.6)**. `run_tests` exists but nothing gates progress on pass/fail (FR-7.1). |
| G4 | `apps/api` review surfaces | **Independent code review findings (5.7)**. No attributable findings-report model/surface (FR-7.2). |
| G5 | `services/execution-manager` | **PR delivery (5.8)**. `push_branch`/`open_pr` are always `False` (`runtime.py`); there is no git push + GitHub PR implementation anywhere. |

## 3. Proposed increments (thin, verifiable slices)

Each increment is independently verifiable with the existing toolchain
(`pytest`/`ruff`/`mypy` for API + execution-manager, `pnpm lint/typecheck/test`
for dashboard). No live Docker/Temporal required.

- **I1 — Approval gate (G1):** approval record model + migration, approval
  service, `approvals` router (create/list/decide), and a gate that sets the
  workflow `WAITING_APPROVAL` and blocks the developer stages until a decision
  is recorded. Tests for the approve/reject/request-changes paths.
- **I2 — Plan pipeline wiring (G2):** connect the feature template's
  requirements/architecture/planning stages to create requirements +
  acceptance criteria, decompose into `Task` records with dependencies, and
  record the plan; tests for a feature request → plan + tasks with dependencies.
- **I3 — Test gating (G3):** gate task/execution progress on the adapter test
  result (pass ⇒ proceed; fail ⇒ block/back to defect). Tests for pass/fail gating.
- **I4 — Code review findings (G4):** attributable findings model + surface;
  unresolved findings route back to defect tasks. Tests for the report path.
- **I5 — PR delivery (G5):** git push + GitHub PR client (injectable, Memory fake
  for tests), permission check on `open_pr`, and attachment of test results /
  review report / execution evidence to the workflow record. Tests for push + PR
  open using the fake.

## 4. Ordering & dependencies

- I1 before I2 (approval gate is the pipeline hinge; the empty placeholder blocks
  the whole phase).
- I2 after I1 (pipeline feeds approved plans to the gate).
- I3, I4, I5 build on the workflow surface but are largely independent of each
  other once I1/I2 land.

## 5. Open questions for the operator

1. Should the demo/verification project for Phase 5 be the **Next.js** adapter
   (per exit criteria) — implying we seed a small Next.js demo workspace?
2. PR delivery (I5) needs a GitHub target. Use a throwaway/private repo token in
   config, or keep `open_pr` behind a Memory fake + config flag until a live
   credential is available (the rest of the phase still lands and is testable)?

---

## Exit criteria (unchanged from `phase-05-sdlc-team.md`)

The full SRS §4 scenario passes end-to-end against a **Next.js** demo project:
requirements → plan → approval → parallel dev → tests → review → completed PR,
all inside isolated, policy-enforced workspaces.