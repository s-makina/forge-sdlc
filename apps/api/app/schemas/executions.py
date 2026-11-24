"""Execution schemas (Phase 4.4/4.6).

Describes an execution's two observable statuses:

* pipeline status — owned by the execution-manager (created → ready → running →
  succeeded/failed/cancelled), surfaced by ``GET /executions/{id}/status``;
* durable status — owned by the Temporal orchestrator (running/completed/failed/
  cancelled), surfaced by ``GET /executions/{id}/run-status``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExecutionSummary(BaseModel):
    """A lightweight execution record derived from its owning task."""

    execution_id: str = Field(min_length=1, max_length=64)
    task_id: int = Field(gt=0)
    task_title: str
    status: str = Field(
        description="Last known pipeline status recorded on the task (snapshot)."
    )


class ExecutionStatus(BaseModel):
    """Live execution-manager pipeline status for a single execution."""

    execution_id: str = Field(min_length=1, max_length=64)
    status: str


class ExecutionRunStatus(BaseModel):
    """Live durable Temporal workflow status for a single execution."""

    execution_id: str = Field(min_length=1, max_length=64)
    durable_status: str
