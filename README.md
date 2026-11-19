# ForgeSDLC --- Autonomous SDLC Platform

## Architecture and Planning Blueprint

**Document status:** Initial architecture proposal\
**Version:** 0.1\
**Date:** 19 November 2026\
**Purpose:** Establish a shared foundation for further requirements
analysis, architecture decisions, estimation, and implementation
planning.

------------------------------------------------------------------------

## 1. Executive Summary

ForgeSDLC is a proposed reusable, multi-project autonomous software
development platform. It is intended to operate like an AI-powered
software engineering organisation: a user submits a software project or
development task, and a coordinated team of specialised agents analyses,
plans, implements, tests, reviews, and prepares the work for release.

The platform should support different projects, programming languages,
frameworks, repositories, and deployment environments. It must not be
hardcoded around one technology stack.

The selected operating decisions are:

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Execution                           Docker-based isolated workspaces

  Models                              Hybrid: local models and external
                                      OpenAI-compatible endpoints

  Autonomy                            Agents work autonomously, with
                                      human approval at defined gates and
                                      before production deployment

  Product scope                       Reusable platform for multiple
                                      projects, technologies, and
                                      programming languages

  Initial architecture                Modular monolith for the control
                                      plane, with independently
                                      deployable workers and execution
                                      services
  -----------------------------------------------------------------------

The platform should be designed for incremental delivery. The first
release must prove that a small team of agents can take a real
development task from requirements through implementation, testing,
review, and a staging-ready deliverable.

## 2. Product Vision and Goals

### 2.1 Vision

Build a reusable autonomous SDLC platform that allows a product owner to
delegate software development work to specialised AI agents while
retaining visibility, control, and approval authority.

### 2.2 Primary goals

1.  Manage multiple independent software projects.
2.  Register and configure specialised AI agents.
3.  Connect local and external AI models through a unified interface.
4.  Execute coding tasks in isolated Docker workspaces.
5.  Coordinate long-running SDLC workflows reliably.
6.  Support multiple languages, frameworks, databases, and tooling
    ecosystems.
7.  Integrate with Git repositories and branch-based development.
8.  Run automated tests, quality checks, and independent code reviews.
9.  Require human approval at configurable milestones and before
    production deployment.
10. Measure agent performance and improve agent configurations through
    controlled evaluation.

### 2.3 Non-goals for the first release

The first release should not attempt to:

-   Automatically rewrite and deploy its own platform code.
-   Guarantee fully autonomous delivery of every possible software
    project.
-   Support every programming language and framework immediately.
-   Give agents unrestricted access to the host, production systems, or
    credentials.
-   Replace human product ownership, architecture accountability, or
    release responsibility.
-   Introduce a large microservices architecture before there is a
    demonstrated need.

## 3. Operating Principles

The following principles should guide design and implementation.

### 3.1 Separation of responsibilities

Keep these concerns separate:

-   **Control plane:** projects, users, permissions, agent registry,
    tasks, approvals, and workflow state.
-   **Workflow orchestration:** durable SDLC workflows, retries,
    timeouts, dependencies, and approval waits.
-   **Agent intelligence:** role instructions, skills, model selection,
    context preparation, and decision-making.
-   **Coding runtime:** repository interaction, file editing, terminal
    commands, and test execution.
-   **Execution plane:** Docker workspaces and isolated build/test
    environments.
-   **Model gateway:** provider configuration, routing, fallback, and
    usage tracking.

### 3.2 Technology neutrality

The orchestrator must not contain framework-specific assumptions.
Technology-specific behaviour belongs in versioned adapters and project
profiles.

### 3.3 Human control

Agents may perform approved development activities autonomously.
Destructive operations, sensitive infrastructure changes, and production
releases require explicit authorisation.

### 3.4 Traceability

Every workflow, task assignment, agent run, tool invocation, code
change, test result, approval, and release should be traceable.

### 3.5 Evaluation before improvement

Agent prompts, skills, tools, and model assignments must be versioned
and evaluated against benchmarks before promotion.

## 4. High-Level Architecture

### 4.1 Logical architecture

``` mermaid
flowchart TD
    U[Platform Owner / Product Owner] --> UI[Next.js Management Dashboard]
    UI --> API[FastAPI Platform API]
    API --> DB[(PostgreSQL)]
    API --> WF[Temporal Workflow Engine]

    WF --> ORCH[Agent Orchestration Layer]
    ORCH --> REG[Agent Registry and Skill Loader]
    ORCH --> CTX[Project Context and Knowledge]
    ORCH --> EXEC[Execution Manager]

    ORCH --> GW[LiteLLM Model Gateway]
    GW --> LOCAL[Local Models / Ollama]
    GW --> EXT[External OpenAI-Compatible Providers]

    EXEC --> OH[OpenHands Coding Runtime]
    OH --> DOCKER[Isolated Docker Workspaces]
    DOCKER --> GIT[Git Repositories]
    DOCKER --> TESTS[Builds and Test Tools]

    API --> REDIS[(Redis)]
    WF --> EVENTS[Workflow and Execution Events]
    EVENTS --> OBS[OpenTelemetry / Monitoring]
```

### 4.2 Control plane and execution plane

**Control plane responsibilities** - User authentication and
authorisation. - Project and repository management. - Agent and model
configuration. - Workflow creation and monitoring. - Task assignment and
dependencies. - Approval management. - Audit records and reporting.

**Execution plane responsibilities** - Provision isolated workspaces. -
Clone or update repositories. - Checkout task branches. - Run coding
agents and tools. - Execute builds, tests, and scanners. - Collect
patches, commits, logs, and artefacts. - Clean up or archive workspaces.

The execution plane should be isolated from the public application
network. The Docker management interface must not be exposed publicly.

## 5. Proposed Technology Stack

  -----------------------------------------------------------------------
  Layer                   Proposed technology     Notes
  ----------------------- ----------------------- -----------------------
  Web dashboard           Next.js + TypeScript    Project, agent, task,
                                                  approval, and
                                                  monitoring UI

  Platform API            Python + FastAPI        Modular control-plane
                                                  API

  Durable workflows       Temporal                Long-running workflows,
                                                  retries, timers,
                                                  approval signals

  Coding runtime          OpenHands Software      Repository-oriented
                          Agent SDK               software engineering
                                                  execution

  Agent framework         Custom platform agent   Owns roles, skills,
                          layer                   permissions, context,
                                                  and model profiles

  Model gateway           LiteLLM                 Unified access to local
                                                  and external model
                                                  providers

  Primary database        PostgreSQL              Transactional platform
                                                  data

  Cache / transient       Redis                   Cache and short-lived
  coordination                                    coordination where
                                                  needed

  Execution               Docker                  Isolated task
                                                  workspaces

  Source control          GitHub and GitLab       Repository and
                          adapters                pull/merge request
                                                  integration

  Monitoring              Prometheus + Grafana    Infrastructure and
                                                  application metrics

  Tracing                 OpenTelemetry           Workflow and tool-call
                                                  traces

  Object storage          S3-compatible storage   Logs, reports, test
                                                  artefacts, and larger
                                                  files

  Semantic retrieval      pgvector (optional)     Add when retrieval
                                                  needs justify it
  -----------------------------------------------------------------------

### 5.1 Architectural qualification

Do not introduce two competing workflow engines. Temporal should own
durable business workflow state. The platform agent layer should manage
agent roles and task-level execution. OpenHands should provide the
coding runtime. LiteLLM should provide model routing.

The OpenAI Agents SDK may be evaluated for selected non-coding agents if
its handoff and tool abstractions provide a clear benefit. It should not
be added as a mandatory second orchestration system without a specific
requirement.

Compatibility with OpenAI-style APIs must be tested per provider and per
capability. An endpoint may support basic chat completions but not every
tool-calling, structured-output, streaming, or multimodal feature.

## 6. Core Platform Modules

  -----------------------------------------------------------------------
  Module                              Responsibilities
  ----------------------------------- -----------------------------------
  Project Management                  Projects, objectives, repositories,
                                      environments, technology profiles

  Agent Registry                      Agent definitions, versions, roles,
                                      skills, permissions, model profiles

  Model Management                    Providers, endpoints, credentials,
                                      models, routing, limits, usage

  Workflow Engine                     Workflow templates, instances,
                                      transitions, retries, recovery

  Task Management                     Tasks, dependencies, assignments,
                                      priorities, acceptance criteria

  Execution Manager                   Docker workspace provisioning,
                                      lifecycle, resource limits, cleanup

  Knowledge Management                Project documents, architecture
                                      decisions, conventions, lessons

  Git Integration                     Clone, branch, commit, push,
                                      pull/merge requests, status

  Quality Management                  Build, test, lint, static analysis,
                                      security checks, review gates

  Approval Management                 Human approval requests, decisions,
                                      comments, audit trail

  Evaluation Engine                   Benchmarks, agent metrics,
                                      regression evaluation, promotion

  Observability                       Logs, traces, metrics, cost,
                                      execution history, alerts

  Notification Service                Dashboard notifications and
                                      optional email integrations
  -----------------------------------------------------------------------

Start with a modular monolith for the platform API. Separate the
workflow workers, model gateway, and execution services where
operational isolation is useful. Do not create a separate microservice
for every module prematurely.

## 7. Multi-Project and Technology Support

### 7.1 Project technology profiles

Every project should declare or discover its technology profile.

Example:

``` yaml
project:
  name: Appointment SaaS
  repository: https://git.example.com/team/appointments
  default_branch: main

technology:
  backend:
    language: java
    framework: spring-boot
    version: "21"
    build_tool: maven
  frontend:
    language: typescript
    framework: nextjs
    package_manager: pnpm
  database:
    engine: postgresql
  testing:
    backend: junit
    frontend: playwright
  execution:
    container_profile: java-node-postgres
```

This is illustrative. The actual profile schema should be formally
defined and validated.

### 7.2 Technology adapter system

Create a registry of versioned technology adapters. An adapter should
provide deterministic tooling information, not AI-generated guesses.

An adapter should define:

-   Language and framework identification rules.
-   Supported versions.
-   Build commands.
-   Test commands.
-   Lint and formatting commands.
-   Dependency installation commands.
-   Static analysis and security tools.
-   Docker image or execution profile.
-   Required environment variables (names only; secrets supplied
    separately).
-   Project structure conventions.
-   Recommended skills.
-   Known limitations and compatibility requirements.

Initial adapters to consider:

-   Java / Spring Boot.
-   PHP / Laravel.
-   JavaScript / TypeScript / Next.js.
-   Python.
-   Go.
-   Flutter.

Add further adapters based on actual project demand.

Example interface:

``` python
class TechnologyAdapter:
    def detect(self, repository): ...
    def get_build_command(self): ...
    def get_test_command(self): ...
    def get_lint_command(self): ...
    def get_docker_image(self): ...
    def get_quality_checks(self): ...
    def get_recommended_skills(self): ...
```

The interface above is conceptual. The implementation should use typed
contracts, validation, adapter versioning, and explicit execution
policies.

### 7.3 Repository discovery

On project onboarding, the platform should:

1.  Inspect repository metadata and permitted files.
2.  Detect languages, frameworks, build tools, and test tools.
3.  Identify monorepo or multi-service structure.
4.  Identify existing conventions and documentation.
5.  Propose a technology profile.
6.  Ask for human confirmation when detection is ambiguous.
7.  Save the confirmed profile and adapter versions.

## 8. Agent Architecture

Use three broad categories of agents.

### 8.1 Management agents

  -----------------------------------------------------------------------
  Agent                               Responsibility
  ----------------------------------- -----------------------------------
  Chief Orchestrator                  Coordinates workflows and delegates
                                      work

  Project Manager                     Creates plans, tasks, dependencies,
                                      and milestones

  Business Analyst                    Requirements, user stories,
                                      acceptance criteria

  Software Architect                  Architecture, data design, API
                                      contracts, technical decisions
  -----------------------------------------------------------------------

### 8.2 Engineering agents

  -----------------------------------------------------------------------
  Agent                               Responsibility
  ----------------------------------- -----------------------------------
  UI/UX Designer                      User flows, interface
                                      specifications, HTML mockups where
                                      requested

  Backend Developer                   APIs, domain logic, persistence,
                                      integrations

  Frontend Developer                  Web UI and frontend integration

  Mobile Developer                    Mobile application development

  Database Engineer                   Schema, indexing, migrations, data
                                      integrity

  Integration Engineer                External services and API
                                      integrations

  QA Engineer                         Test strategy, automated tests,
                                      regression testing

  Security Engineer                   Threat analysis, security checks,
                                      vulnerability assessment

  Code Reviewer                       Independent review of changes

  DevOps Engineer                     Containers, CI/CD, staging and
                                      deployment preparation

  Technical Writer                    API, operational, and user
                                      documentation
  -----------------------------------------------------------------------

### 8.3 Specialist agents

Specialists should be loaded dynamically using a general role plus
technology-specific skills. Examples include Spring Boot Specialist,
Laravel Specialist, PostgreSQL Specialist, React Specialist, Flutter
Specialist, Go Specialist, and Kubernetes Specialist.

Do not require a permanently running agent for every technology.
Specialist configurations can be instantiated when the task requires
them.

### 8.4 Agent definition

Agent definitions should be versioned and validated.

``` yaml
agent:
  id: backend-developer
  name: Backend Developer
  version: 1.0.0
  role: software_engineer

  capabilities:
    - code_analysis
    - implementation
    - debugging
    - unit_testing
    - refactoring

  model_profile: coding-strong

  tools:
    - repository_read
    - repository_write
    - terminal
    - test_runner
    - git

  permissions:
    read_repository: true
    write_repository: true
    create_branch: true
    merge_branch: false
    production_access: false

  skills:
    - clean-code
    - software-testing
    - secure-coding
    - project-technology-profile

  quality_gates:
    - tests_must_pass
    - lint_must_pass
    - no_unresolved_critical_security_findings
```

Use logical model profile names rather than hardcoding vendor model
identifiers in agent definitions.

### 8.5 Agent identity and lifecycle

Each agent should have:

-   Stable identifier.
-   Display name and role.
-   Versioned instructions.
-   Skills and tool permissions.
-   Model profile.
-   Configuration schema.
-   Status and availability.
-   Created and updated timestamps.
-   Evaluation history.
-   Promotion and rollback history.

An agent configuration change should create a new version rather than
silently overwriting the active version.

## 9. Model Management and Routing

### 9.1 Provider requirements

Support:

-   Ollama and other local inference servers.
-   External OpenAI-compatible endpoints.
-   Multiple API providers.
-   Provider-specific base URLs.
-   Credential references.
-   Model capability declarations.
-   Timeouts and rate limits.
-   Fallback routes.
-   Usage and cost tracking where provider data is available.

### 9.2 Logical model profiles

  Profile               Intended workload
  --------------------- ----------------------------------------------
  `general-fast`        Classification and simple tasks
  `reasoning-strong`    Requirements, planning, and architecture
  `coding-strong`       Complex implementation and debugging
  `coding-fast`         Routine implementation
  `review-specialist`   Independent code review
  `documentation`       Technical documentation
  `vision`              Screenshot and visual analysis, if supported

The model router should select a concrete model based on profile,
availability, capability, policy, budget, and measured task performance.

### 9.3 Model selection and fallback

A fallback must not silently downgrade a task to a model that cannot
support the required capability. For example, a task requiring tool
calls or structured output must only be routed to models and providers
that pass the relevant compatibility checks.

Track:

-   Provider availability.
-   Latency.
-   Error rate.
-   Task success by task category.
-   Input and output tokens.
-   Cost where applicable.
-   Context window.
-   Tool-calling and structured-output support.

## 10. SDLC Workflow

The platform should provide reusable workflow templates rather than one
hardcoded sequence.

### 10.1 Full feature-development workflow

``` mermaid
flowchart TD
    A[User submits project or feature] --> B[Requirements analysis]
    B --> C[Business Analyst]
    C --> D[Software Architect]
    D --> E[Plan and task breakdown]
    E --> F{Plan approval}
    F -->|Changes requested| C
    F -->|Approved| G[Create branches and workspaces]
    G --> H[Parallel development]
    H --> I[Integration]
    I --> J[Automated testing]
    J --> K{Tests pass?}
    K -->|No| L[Create defect tasks]
    L --> H
    K -->|Yes| M[Independent code review]
    M --> N{Review passed?}
    N -->|No| L
    N -->|Yes| O[Security and quality checks]
    O --> P{Quality gates pass?}
    P -->|No| L
    P -->|Yes| Q[Deploy to staging]
    Q --> R[Human acceptance review]
    R --> S{Release approved?}
    S -->|No| L
    S -->|Yes| T[Production release]
    T --> U[Monitor and document]
    U --> V[Evaluate agent performance]
```

### 10.2 Additional workflow templates

Plan for:

-   New project discovery and setup.
-   Feature development.
-   Bug fixing.
-   Refactoring.
-   Dependency updates.
-   Security remediation.
-   Performance investigation.
-   Test coverage improvement.
-   Documentation generation.
-   Maintenance and upgrade work.

### 10.3 Workflow requirements

Each workflow should support:

-   Durable state.
-   Explicit state transitions.
-   Task dependencies.
-   Parallel and sequential activities.
-   Retries with bounded policies.
-   Timeouts and cancellation.
-   Human approval signals.
-   Escalation on repeated failure.
-   Idempotent activities where possible.
-   Recovery after worker or infrastructure failure.
-   Complete execution history.

Temporal should own durable workflow state. Agent conversations should
not be the only record of workflow progress.

## 11. Task Management and Parallel Development

Tasks should be first-class platform records.

Each task should contain:

-   Project and workflow.
-   Title and description.
-   Task type and priority.
-   Acceptance criteria.
-   Dependencies.
-   Assigned agent or agent role.
-   Repository and target branch.
-   Relevant files or modules, if known.
-   Required skills and model profile.
-   Execution limits.
-   Status.
-   Results and artefact references.

Suggested task statuses:

`draft`, `ready`, `assigned`, `in_progress`, `blocked`, `review`,
`failed`, `completed`, `cancelled`.

### 11.1 Parallel execution rules

Agents may work in parallel only when interfaces, ownership, and
dependencies are clear.

Before parallel implementation, the architect should define:

-   API contracts.
-   Database ownership and migration coordination.
-   Module boundaries.
-   Shared file ownership.
-   Integration expectations.
-   Test responsibilities.

Use separate Git branches or worktrees for independent tasks. Avoid
multiple agents editing the same working tree or files simultaneously
without an explicit coordination mechanism.

Integration should combine changes through reviewed pull/merge requests
and run cross-module tests.

## 12. Docker Execution and Security

### 12.1 Execution lifecycle

``` mermaid
flowchart TD
    A[Orchestrator assigns task] --> B[Execution Manager]
    B --> C[Create isolated workspace]
    C --> D[Clone or prepare repository]
    D --> E[Checkout task branch]
    E --> F[Load project context and skills]
    F --> G[Start coding runtime]
    G --> H[Edit files and run tools]
    H --> I[Run build and tests]
    I --> J{Successful?}
    J -->|No| K[Capture errors and apply bounded retry]
    K --> G
    J -->|Yes| L[Commit or prepare patch]
    L --> M[Publish execution report]
    M --> N[Archive required artefacts and clean workspace]
```

### 12.2 Workspace requirements

Each execution workspace should have:

-   Unique execution identifier.
-   Project and task association.
-   Dedicated repository checkout.
-   Dedicated branch or worktree.
-   Approved container image.
-   CPU, memory, disk, and time limits.
-   Network policy.
-   Scoped credentials.
-   Execution event capture.
-   Cleanup policy.

### 12.3 Security requirements

-   Run containers as non-root where possible.
-   Never mount the host Docker socket into agent containers.
-   Do not expose the Docker management API publicly.
-   Apply CPU, memory, disk, and process limits.
-   Enforce execution timeouts.
-   Restrict network access by policy.
-   Use short-lived, scoped credentials.
-   Keep secrets out of prompts, logs, and source control.
-   Use read-only mounts where possible.
-   Separate production credentials from development execution.
-   Audit every privileged operation.
-   Scan images and dependencies.
-   Clean up temporary workspaces and credentials.
-   Consider stronger isolation or dedicated execution hosts for
    high-risk tasks.

The platform must treat repository contents, issue descriptions,
documents, and tool output as untrusted data. Instructions found in
those sources must not override platform policies or agent permissions.

## 13. Human Approval and Autonomy

The selected operating model is autonomous execution with human approval
at defined gates.

Suggested approval points:

  Gate                 Approval purpose
  -------------------- -------------------------------------------------
  Requirements         Confirm scope and acceptance criteria
  Architecture         Approve significant technical decisions
  Milestone            Accept major deliverables or integration points
  Production release   Authorise production deployment

Approval rules should be configurable per project and workflow.

A minor bug fix may not need a separate architecture approval. A
database redesign or major infrastructure change may require one.

Every approval record should include:

-   Requesting workflow and project.
-   Approval type.
-   Relevant artefacts and evidence.
-   Requested decision.
-   Approver identity.
-   Decision and comments.
-   Timestamp.
-   Configuration/version context.

Production deployment, destructive database operations, and other
high-impact actions must be protected by explicit authorisation and
auditable controls.

## 14. Knowledge and Context Management

Use separate knowledge scopes.

  -----------------------------------------------------------------------
  Scope                               Examples
  ----------------------------------- -----------------------------------
  Global                              Platform policies, general coding
                                      standards, security requirements

  Agent                               Role instructions, skills, tool
                                      guidance, evaluated lessons

  Project                             Architecture, requirements,
                                      conventions, decisions

  Task                                Current task context, relevant
                                      files, errors, prior attempts
  -----------------------------------------------------------------------

### 14.1 Project knowledge example

``` text
PROJECT: Appointment SaaS

Architecture:
- Spring Boot modular monolith
- Next.js frontend
- PostgreSQL database

Development rules:
- Controllers must not contain business logic.
- Business logic belongs in dedicated services.
- Use DTOs for API requests and responses.
- Use Flyway for database migrations.
- Enforce tenant boundaries in data access.
- Test important business operations.

Known risks:
- Appointment overlap validation.
- Provider assignment concurrency.
- Payment fallback behaviour.
```

### 14.2 Retrieval requirements

The context service should retrieve only relevant knowledge for each
task. Avoid sending the entire project history to every model call.

Initial storage approach:

-   PostgreSQL for structured project and agent knowledge.
-   Git for version-controlled technical documentation.
-   PostgreSQL full-text search for initial retrieval.
-   pgvector for semantic retrieval when useful.
-   S3-compatible storage for large artefacts and reports.

Knowledge must have source, scope, version, and provenance.
Agent-generated claims should not automatically become trusted project
facts.

## 15. Continuous Agent Evaluation and Improvement

The improvement system should be a core module.

### 15.1 Metrics

**Engineering** - Task completion rate. - First-attempt test pass
rate. - Defects introduced. - Review rejection rate. - Rework
frequency. - Regression defects.

**Operational** - Task duration. - Model calls and token usage. - Cost
where available. - Container execution time. - Retry frequency. -
Failure and timeout rate.

**Quality** - Acceptance criteria satisfied. - Test coverage and test
quality. - Maintainability findings. - Security findings. -
Documentation completeness.

Metrics must be interpreted by task type and complexity. A raw success
percentage alone is not sufficient to compare agents fairly.

### 15.2 Improvement lifecycle

1.  Collect execution outcomes and evidence.
2.  Identify repeated failure patterns.
3.  Propose changes to prompts, skills, tools, workflows, or model
    profiles.
4.  Create a new candidate agent version.
5.  Run a fixed benchmark and regression suite.
6.  Compare candidate and current versions.
7.  Require owner approval for promotion.
8.  Monitor the promoted version.
9.  Roll back if performance regresses.

The system must not silently rewrite active production agent
instructions or deploy platform code changes.

### 15.3 Benchmark suite

Create representative historical tasks with expected acceptance
criteria. Use them to test whether an agent change improves outcomes
without damaging existing capabilities.

## 16. Suggested Database Domain Model

The following is a conceptual starting point, not a final migration
specification.

``` mermaid
erDiagram
    USERS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ REPOSITORIES : contains
    PROJECTS ||--o{ PROJECT_TECHNOLOGIES : uses
    PROJECTS ||--o{ WORKFLOWS : runs
    PROJECTS ||--o{ TASKS : contains
    AGENTS ||--o{ AGENT_VERSIONS : has
    AGENT_VERSIONS }o--|| MODEL_PROFILES : uses
    WORKFLOWS ||--o{ TASKS : coordinates
    TASKS ||--o{ EXECUTIONS : generates
    TASKS ||--o{ TASK_DEPENDENCIES : depends_on
    TASKS ||--o{ TASK_ASSIGNMENTS : assigned
    AGENTS ||--o{ TASK_ASSIGNMENTS : receives
    EXECUTIONS ||--o{ EXECUTION_EVENTS : records
    PROJECTS ||--o{ APPROVALS : requires
    PROJECTS ||--o{ KNOWLEDGE_DOCUMENTS : maintains
    AGENT_VERSIONS ||--o{ EVALUATIONS : evaluated
    EXECUTIONS ||--o{ EVALUATIONS : produces
    PROJECTS ||--o{ RELEASES : produces
```

### 16.1 Initial table candidates

-   `users`
-   `projects`
-   `repositories`
-   `project_technologies`
-   `agents`
-   `agent_versions`
-   `agent_skills`
-   `model_providers`
-   `models`
-   `model_profiles`
-   `workflow_templates`
-   `workflows`
-   `tasks`
-   `task_dependencies`
-   `task_assignments`
-   `executions`
-   `execution_events`
-   `approvals`
-   `knowledge_documents`
-   `evaluations`
-   `releases`
-   `audit_logs`

The final schema should define tenant/project ownership, foreign keys,
indexes, retention, soft deletion where appropriate, and audit
requirements. Do not assume every entity needs a separate table until
detailed requirements are complete.

## 17. Proposed Repository Structure

``` text
forgesdlc/
├── apps/
│   ├── dashboard/                 # Next.js
│   └── api/                       # FastAPI
│
├── services/
│   ├── orchestrator/              # Temporal workflows and workers
│   ├── agent-runtime/             # Agent execution and context
│   ├── execution-manager/         # Docker workspace lifecycle
│   ├── model-gateway/             # LiteLLM configuration
│   ├── knowledge-service/         # Context retrieval
│   ├── evaluation-engine/         # Benchmarks and evaluation
│   └── notification-service/
│
├── packages/
│   ├── agent-core/
│   ├── agent-registry/
│   ├── technology-adapters/
│   ├── tool-registry/
│   ├── workflow-contracts/
│   ├── shared-models/
│   └── security/
│
├── agents/
│   ├── management/
│   ├── engineering/
│   └── specialist/
│
├── skills/
│   ├── general/
│   ├── backend/
│   ├── frontend/
│   ├── database/
│   ├── devops/
│   └── security/
│
├── technology-adapters/
│   ├── java-spring/
│   ├── php-laravel/
│   ├── javascript-nextjs/
│   ├── python/
│   ├── golang/
│   └── flutter/
│
├── workflows/
│   ├── full-sdlc/
│   ├── bug-fix/
│   ├── feature-development/
│   ├── refactoring/
│   └── maintenance/
│
├── infrastructure/
│   ├── docker/
│   ├── temporal/
│   ├── litellm/
│   ├── postgres/
│   ├── redis/
│   └── monitoring/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── agent-evaluations/
│
├── docs/
└── docker-compose.yml
```

The exact deployment boundaries and package ownership should be
finalised during detailed design.

## 18. Dashboard Requirements

The dashboard should provide these main areas:

1.  **Overview:** active projects, workflow status, blocked tasks,
    approvals, usage, and recent activity.
2.  **Projects:** project setup, repository configuration, technology
    profiles, objectives, and environments.
3.  **Agents:** agent registry, roles, versions, skills, tools, model
    profiles, and performance.
4.  **Models:** providers, endpoints, models, credentials references,
    routing policies, limits, and health.
5.  **Workflows:** templates, running instances, stage status, retries,
    and failure details.
6.  **Tasks:** backlog, dependencies, assignments, status, and execution
    results.
7.  **Executions:** container/workspace details, logs, commands, diffs,
    commits, and artefacts.
8.  **Approvals:** pending decisions, evidence, comments, and audit
    history.
9.  **Knowledge:** project documents, architecture decisions,
    conventions, and lessons.
10. **Evaluations:** benchmarks, comparisons, candidate versions, and
    promotion history.
11. **Reports:** delivery metrics, quality, agent performance, time, and
    model usage.
12. **Settings:** users, roles, integrations, security policies, and
    retention.

The dashboard must distinguish actual execution data from illustrative
or estimated metrics.

## 19. Deployment Architecture

Initial deployment can use Docker Compose and a reverse proxy, with the
ability to move execution workloads to separate hosts later.

Suggested services:

-   Reverse proxy.
-   Next.js dashboard.
-   FastAPI API.
-   Temporal server and workers.
-   Agent runtime workers.
-   Execution manager.
-   LiteLLM gateway.
-   PostgreSQL.
-   Redis.
-   Object storage.
-   Prometheus and Grafana.
-   OpenTelemetry collector.

Keep model inference separate from the control-plane workload,
especially when local models use GPUs.

The platform should support multiple execution hosts in a later phase.
The execution manager should abstract workspace provisioning so that the
workflow layer does not depend on one Docker host.

## 20. Implementation Roadmap

### Milestone 1 --- Foundation and infrastructure

-   Repository and development conventions.
-   Docker Compose development environment.
-   PostgreSQL and Redis.
-   FastAPI application structure.
-   Next.js dashboard shell.
-   Authentication and authorisation.
-   Project management.
-   Repository records and integration foundation.
-   Audit logging foundation.

**Exit criteria:** Users can securely create and manage multiple
projects and configure repositories.

### Milestone 2 --- Agent and model management

-   Agent registry.
-   Versioned agent definitions.
-   Skills and tool registry.
-   Model provider configuration.
-   LiteLLM integration.
-   Logical model profiles.
-   Provider health and capability checks.

**Exit criteria:** Administrators can configure agents with different
model profiles and permissions.

### Milestone 3 --- Docker execution engine

-   Execution manager.
-   Isolated workspace lifecycle.
-   OpenHands integration.
-   Repository cloning and branch management.
-   Terminal and test execution.
-   Resource and network policies.
-   Logs and artefact collection.
-   Cleanup and recovery.

**Exit criteria:** A coding agent can safely execute a bounded task
against a real repository.

### Milestone 4 --- Workflow orchestration

-   Temporal integration.
-   Workflow templates.
-   Task creation and dependencies.
-   Assignment and scheduling.
-   Parallel execution rules.
-   Retry, timeout, cancellation, and recovery.
-   Workflow monitoring.

**Exit criteria:** A workflow can coordinate multiple tasks and agents
reliably.

### Milestone 5 --- First autonomous SDLC team

Start with six roles:

1.  Business Analyst.
2.  Project Manager.
3.  Software Architect.
4.  Developer.
5.  QA Engineer.
6.  Code Reviewer.

**Exit criteria:** A real feature can progress from requirements through
implementation, tests, review, and a completed pull request.

### Milestone 6 --- Quality and approvals

-   Quality gate framework.
-   Automated testing adapters.
-   Static analysis and security scanning.
-   Review findings and remediation loops.
-   Staging deployment integration.
-   Human approval workflows.
-   Production release authorisation.

**Exit criteria:** A release candidate cannot proceed to production
without the required approvals and quality evidence.

### Milestone 7 --- Knowledge and improvement

-   Project knowledge management.
-   Context retrieval.
-   Agent metrics.
-   Benchmark tasks.
-   Candidate configuration versions.
-   Regression evaluation.
-   Owner-approved promotion and rollback.

**Exit criteria:** Agent changes can be evaluated against a repeatable
benchmark before promotion.

### Milestone 8 --- Scale and advanced autonomy

-   Additional specialist agents.
-   More technology adapters.
-   Multiple execution hosts.
-   Resource scheduling.
-   Cost controls.
-   Advanced analytics.
-   Additional workflow templates.

**Exit criteria:** The platform can operate multiple projects
concurrently with controlled resource allocation and reliable isolation.

## 21. MVP Scope and Acceptance Criteria

The MVP should prove end-to-end delivery, not just agent registration or
dashboard functionality.

  Capability     MVP acceptance criterion
  -------------- ---------------------------------------------------------
  Projects       Create and manage multiple independent projects
  Technologies   Initial support for Spring Boot, Laravel, and Next.js
  Models         Connect Ollama and external OpenAI-compatible endpoints
  Agents         Configure and version at least six agent roles
  Execution      Run coding tasks in isolated Docker workspaces
  Repositories   Clone repositories and manage task branches
  Workflow       Run a feature-development workflow
  Tasks          Create, assign, and track dependent tasks
  Testing        Execute project-specific tests and capture results
  Review         Produce independent code review findings
  Approvals      Require human approval before production
  Monitoring     View workflow progress, errors, and execution history

### MVP demonstration scenario

1.  Create a project.
2.  Connect a Git repository.
3.  Submit a feature requirement.
4.  Generate requirements and acceptance criteria.
5.  Generate architecture and implementation tasks.
6.  Obtain plan approval.
7.  Execute development tasks in Docker workspaces.
8.  Integrate changes through Git.
9.  Run automated tests.
10. Perform independent code review.
11. Prepare a staging deployment.
12. Present evidence and request release approval.

## 22. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Agents modify overlapping files     Separate branches/worktrees,
                                      ownership rules, integration gates

  Model produces incorrect code       Tests, independent review, static
                                      analysis, bounded retries

  Provider lacks required API         Capability checks and
  features                            provider-specific compatibility
                                      tests

  Runaway execution or cost           Budgets, timeouts, token limits,
                                      task limits, cancellation

  Docker host compromise              Isolation, no Docker socket in
                                      agents, restricted networking,
                                      separate hosts

  Secrets leak into logs or prompts   Scoped credentials, secret
                                      redaction, short-lived tokens

  Workflow loses state                Durable Temporal workflows and
                                      idempotent activities

  Incorrect project context           Source provenance, project-scoped
                                      retrieval, human-confirmed
                                      decisions

  Agent improvement causes            Versioning, fixed benchmarks,
  regressions                         approval, rollback

  Unreliable autonomous completion    Explicit acceptance criteria and
                                      evidence-based quality gates

  Infrastructure becomes too complex  Modular monolith initially, split
                                      services only when justified
  -----------------------------------------------------------------------

## 23. Decisions Still Requiring Confirmation

This document is an architecture proposal, not a complete SRS. The
following decisions should be resolved before detailed implementation
planning.

### Product and users

-   Is the first version single-user or multi-user?
-   Is the platform intended only for internal use initially, or will it
    eventually be offered as a SaaS product?
-   Are project-level roles and permissions required in the MVP?

### Source control

-   Which integration should be implemented first: GitLab or GitHub?
-   Should the platform create pull/merge requests automatically?
-   Should users be able to connect local repositories?

### Execution infrastructure

-   What server resources are available (CPU, RAM, disk, GPU)?
-   Will all execution happen on one Docker host initially?
-   What network access should coding containers have by default?
-   What maximum concurrent executions should be supported?

### Models and cost

-   Which local model server will be used initially?
-   Which external providers must be supported first?
-   Should each project have its own model budget?
-   Should the platform enforce a maximum spend per task and workflow?

### Approvals and release

-   Which milestones require approval by default?
-   Is staging deployment in the first MVP?
-   Which deployment targets should eventually be supported?
-   Who is authorised to approve production releases?

### Technology support

-   Confirm the first three technology adapters.
-   Define how monorepos and multiple services within one repository
    should be handled.
-   Decide whether UI mockups must be generated as HTML files for
    applicable projects.

## 24. Recommended Immediate Next Steps

Before implementation:

1.  Review and approve the product scope.
2.  Resolve the open decisions in Section 23.
3.  Produce a formal SRS with functional and non-functional
    requirements.
4.  Produce detailed architecture and component specifications.
5.  Define the initial database schema and API contracts.
6.  Define agent, skill, tool, and technology-adapter contracts.
7.  Define Docker security and execution policies.
8.  Define Temporal workflow state machines.
9.  Break the MVP into epics, tasks, dependencies, and acceptance
    criteria.
10. Establish a test and evaluation strategy.

The first implementation should focus on the platform foundation and one
working end-to-end feature-development workflow. Additional agents and
autonomy should be introduced only after the core execution and recovery
mechanisms are reliable.

------------------------------------------------------------------------

## 25. Reference Documentation

These are starting points for technical validation. Confirm current
versions, API capabilities, and licensing before selecting dependencies.

-   OpenHands SDK: https://docs.openhands.dev/sdk
-   OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
-   LiteLLM: https://docs.litellm.ai/
-   Temporal: https://docs.temporal.io/
-   Docker Engine security: https://docs.docker.com/engine/security/
-   FastAPI: https://fastapi.tiangolo.com/
-   PostgreSQL: https://www.postgresql.org/docs/
-   OpenTelemetry: https://opentelemetry.io/docs/
-   Prometheus: https://prometheus.io/docs/
-   Grafana: https://grafana.com/docs/

------------------------------------------------------------------------

**End of document**

*This blueprint is intended to be refined into the authoritative SRS,
architecture specification, implementation backlog, and acceptance-test
plan before production development begins.*
