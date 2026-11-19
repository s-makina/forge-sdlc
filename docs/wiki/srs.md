# ForgeSDLC — MVP System Requirements Specification

**Document status:** Draft for review\
**Version:** 0.2\
**Date:** 19 November 2026\
**Scope:** MVP = end-to-end proof of a feature from requirements through a completed pull request.

---

## 1. Introduction

### 1.1 Purpose

This SRS defines the functional and non-functional requirements for the ForgeSDLC MVP. It is the reference for the MVP phase plan in `docs/wiki/mvp-phase-plan.md`.

### 1.2 Scope

The MVP proves that a coordinated set of AI agents can take a real software development task from requirements analysis through implementation, testing, independent review, and a completed pull request, inside isolated Docker workspaces.

### 1.3 Definitions / acronyms

| Term | Meaning |
|------|---------|
| Control plane | Platform API, project/agent/task state, approvals |
| Execution plane | Isolated Docker workspaces where agents run |
| Agent | A role configured with instructions, skills, tools, model profile |
| Model profile | Logical name for a model assignment (e.g. `coding-strong`) |
| Adapter | Versioned technology-specific tooling knowledge |
| SDLC | Software development lifecycle |

### 1.4 References

- Architecture blueprint: `README.md`.
- Phase plan: `docs/wiki/mvp-phase-plan.md`.

---

## 2. Functional Requirements

### FR-1 — Project management
- **FR-1.1** Create and list independent projects.
- **FR-1.2** Each project records a name, description, default branch, and optional repository URL.
- **FR-1.3** Update and deactivate projects.

### FR-2 — Technology adapters
- **FR-2.1** Detect a repository's language/framework and propose a technology profile.
- **FR-2.2** Provide build, test, lint, and dependency-install commands via versioned adapters.
- **FR-2.3** Ship adapters for **Spring Boot**, **Laravel**, and **Next.js**.
- **FR-2.4** Allow human confirmation when detection is ambiguous.

### FR-3 — Model gateway
- **FR-3.1** Connect an **Ollama** local endpoint and an external **OpenAI-compatible** endpoint.
- **FR-3.2** Define logical model profiles and route requests to a concrete model.
- **FR-3.3** Declare provider capabilities (tool-calling, structured output) and refuse routing to incapable providers.
- **FR-3.4** Record usage (tokens, cost where available).

### FR-4 — Agent registry
- **FR-4.1** Define and version agent roles.
- **FR-4.2** MVP ships at least these roles: **Business Analyst, Project Manager, Software Architect, Developer, QA Engineer, Code Reviewer**.
- **FR-4.3** Each agent declares capabilities, tools, permissions, skills, and a model profile.

### FR-5 — Docker execution
- **FR-5.1** Provision an isolated workspace per task with a dedicated repository checkout and branch.
- **FR-5.2** Enforce CPU, memory, disk, and time limits.
- **FR-5.3** Capture execution events, logs, and artefacts.
- **FR-5.4** Clean up or archive workspaces after execution.
- **FR-5.5** Run agents as non-root; never mount the host Docker socket.

### FR-6 — Workflow orchestration
- **FR-6.1** Run a feature-development workflow from requirement to completed PR.
- **FR-6.2** Support durable state, retries, timeouts, cancellation, and recovery.
- **FR-6.3** Model tasks with dependencies, assignment, and status.
- **FR-6.4** Support at least two concurrent developers on separate branches.

### FR-7 — Testing and review
- **FR-7.1** Run project-specific automated tests and capture results.
- **FR-7.2** Produce an independent code-review findings report.

### FR-8 — Approvals
- **FR-8.1** Require **plan approval** after architecture, before implementation begins.
- **FR-8.2** Record approver, decision, comments, and timestamp.

### FR-9 — Dashboard
- **FR-9.1** View projects, agents, tasks, workflow status, and execution history.
- **FR-9.2** Distinguish actual execution data from illustrative metrics.

---

## 3. Non-Functional Requirements

### NFR-1 — Security
- **NFR-1.1** Secrets never appear in prompts, logs, or source control.
- **NFR-1.2** Credentials are short-lived and scoped to the execution.
- **NFR-1.3** Docker management API is not exposed publicly.
- **NFR-1.4** Repository contents and tool output are treated as untrusted data; they cannot override platform policies.

### NFR-2 — Reliability
- **NFR-2.1** Workflow state is durable and survives worker or infrastructure failure.
- **NFR-2.2** Activities are idempotent where possible.

### NFR-3 — Performance
- **NFR-3.1** Workspace provisioning completes within a bounded time for a small repository.
- **NFR-3.2** The MVP supports a small number of concurrent executions on one Docker host.

### NFR-4 — Operability
- **NFR-4.1** Whole environment starts via Docker Compose.
- **NFR-4.2** Logs and metrics are available for workflows and tool calls.

### NFR-5 — Maintainability
- **NFR-5.1** The API is a modular monolith; services split only when justified.
- **NFR-5.2** Agent, adapter, and workflow definitions are versioned.

### NFR-6 — Traceability
- **NFR-6.1** Every task assignment, agent run, tool call, test result, and approval is traceable.

---

## 4. Acceptance Scenario (end-to-end demo)

1. Create a project.
2. Connect a GitHub repository (Next.js demo app).
3. Submit a feature requirement.
4. Business Analyst generates requirements and acceptance criteria.
5. Software Architect produces a plan and implementation tasks.
6. Obtain plan approval.
7. Two developers implement tasks in parallel Docker workspaces on separate branches.
8. Integrate changes through a reviewed pull request.
9. Run automated tests.
10. Independent Code Reviewer reports findings.
11. Deliver a completed pull request and execution evidence.

**Pass criteria:** The feature reaches a completed pull request with passing tests and a review report, all within isolated workspaces and with a recorded approval at the plan gate.

---

*End of SRS.*