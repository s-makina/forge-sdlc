# execution-manager

The Docker execution engine worker for ForgeSDLC. Owns the isolated-workspace
lifecycle for coding-agent executions (Phase 3).

## Scope (subphase 3.1)

Implements the execution-manager service API surface and the execution
task-record model:

- `POST /api/v1/executions` — request an execution.
- `GET /api/v1/executions` — list executions (optional `project_id` filter).
- `GET /api/v1/executions/{id}` — fetch an execution.
- `GET /api/v1/executions/{id}/status` — poll status.
- `GET /api/v1/executions/{id}/logs` — fetch logs.
- `GET /api/v1/executions/{id}/artefacts` — fetch artefacts.
- `POST /api/v1/executions/{id}/cancel` — request cancellation.
- `POST /api/v1/executions/{id}/cleanup` — mark a terminal execution done.

Lifecycle states (README §12.1):

```
created -> ready -> running -> succeeded | failed -> cleaning -> done
```

Docker provisioning, repository cloning/branching, the OpenHands runtime,
policies, log/artefact collection, and cleanup/recovery are implemented in
later Phase 3 subphases.

## Develop

```sh
pip install -e .[dev]
ruff check .
mypy .
pytest
```