# Phase 5 — First Autonomous SDLC Team

**Goal:** A real feature progresses from requirements through implementation, tests, review, and a completed pull request, using the six-agent SDLC team.

**Depends on:** Phase 4 and the three technology adapters (Spring Boot, Laravel, Next.js).\
**Reference:** SRS §4 (acceptance scenario); README §10.1.

---

## 5.1 Agent roles: the six-team SDLC

**What will be done**
- Define and seed versioned definitions for: **Business Analyst, Project Manager, Software Architect, Developer, QA Engineer, Code Reviewer** (README §8).
- Each role gets instructions, skills, tool permissions, and a model profile.
- The Developer role is instantiated for concurrent tasks; Code Reviewer is independent of developers.

**Acceptance criteria**
- All six roles are registered, versioned, and assignable.

## 5.2 Feature-development workflow wiring

**What will be done**
- Wire the Phase 4 feature-development template end-to-end (README §10.1 mermaid):
  requirements → architecture → plan → approval → branches/workspaces → parallel dev → integration → testing → review → PR.
- Connect tasks, agent assignments, executions, and approval records through the workflow.

**Acceptance criteria**
- Submitting a feature drives the full workflow automatically to a PR.

## 5.3 Requirements → architecture → plan pipeline

**What will be done**
- Business Analyst produces requirements + acceptance criteria from the feature request.
- Project Manager decomposes scope into milestones/tasks and dependencies.
- Software Architect produces architecture, API contracts, module boundaries, and DB ownership.
- The plan is persisted as task records.

**Acceptance criteria**
- A feature request yields requirements, a plan, and tasks with dependencies.

## 5.4 Plan approval gate

**What will be done**
- Insert a **plan approval** gate after architecture, before implementation (FR-8).
- The approval request presents the plan and evidence; the operator approves or requests changes.
- Record approver, decision, comments, timestamp.

**Acceptance criteria**
- Development does not start until plan approval is recorded; rejection returns to planning.

## 5.5 Parallel development and integration

**What will be done**
- Run up to **2 developers** in parallel on separate branches/workspaces per agreed ownership.
- Integrate via a reviewed pull request; run cross-module tests.

**Acceptance criteria**
- Two independent tasks are implemented in parallel and integrated cleanly through a PR.

## 5.6 Automated testing

**What will be done**
- Run the demo project's test suite (via its technology adapter) in the workspace.
- Capture and gate on test results before review proceeds (FR-7.1).

**Acceptance criteria**
- A failing test blocks progress; a passing suite is recorded as evidence.

## 5.7 Independent code review

**What will be done**
- A Code Reviewer independent of the developers assesses the change.
- Produce a findings report; unresolved findings route back to defect tasks.

**Acceptance criteria**
- The reviewer produces an attributable findings report (FR-7.2).

## 5.8 Pull request delivery

**What will be done**
- Push the integrated branch and open a GitHub pull request.
- Attach test results, review report, and execution evidence to the workflow record.

**Acceptance criteria**
- The feature reaches a completed pull request with passing tests, a review report, and execution evidence.

---

## Exit criteria (Phase 5) — MVP demonstration passes

The full SRS §4 scenario passes end-to-end against a **Next.js** demo project: requirements → plan → approval → parallel dev → tests → review → completed PR, all inside isolated, policy-enforced workspaces.