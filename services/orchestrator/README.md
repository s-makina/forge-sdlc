# ForgeSDLC Orchestrator

Durable workflow orchestrator worker (Phase 4.1). Submits workflow instances to
Temporal, requests cancellation, and reports back durable status, mirroring the
control-plane workflow lifecycle (`apps/api`).

## Layout

- `app/temporal/client.py` — injectable Temporal client (SDK + in-memory fake).
- `app/temporal/worker.py` — durable workflow registration scaffold.
- `app/services/orchestrator.py` — submission/cancel/status orchestration logic.
- `app/core/container.py` — DI container.
- `app/routers/` — health and workflow endpoints.

## Run

```sh
pip install -e ".[temporal]"
uvicorn app.main:app --port 8002
```

## Test (no live Temporal needed)

```sh
pip install -e ".[dev]"
pytest
```