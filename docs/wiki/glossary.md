# ForgeSDLC Glossary

| Term | Definition |
|------|------------|
| Control plane | API + data + workflow state; where platform concerns live |
| Execution plane | Isolated Docker workspaces where agents do the work |
| Agent | A versioned role with instructions, skills, tools, permissions, model profile |
| Agent version | An immutable configuration revision of an agent |
| Model profile | Logical name mapping to a concrete model (e.g. `coding-strong`) |
| Model gateway | Service that routes model requests across providers (LiteLLM) |
| Technology adapter | Versioned tech-specific tooling knowledge (build/test/lint commands, images) |
| Technology profile | A project's declared tech stack derived from an adapter |
| Workspace | An isolated Docker environment for one execution |
| Execution | One run of an agent/task in a workspace |
| Task | A first-class work item with dependencies, assignment, acceptance criteria |
| Workflow | A durable orchestration of tasks (Temporal) |
| Approval gate | A human decision point in a workflow |
| Reviewer | Independent agent that assesses a change's quality |
| Quality gate | Automated check a change must pass (tests, lint, static analysis) |

## Design-tree ancestry
- Key decisions and their rationale: `decisions/mvp-scope.md`.