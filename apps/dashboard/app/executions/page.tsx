"use client";

import { useEffect, useRef, useState } from "react";

import {
  getExecutions,
  getExecutionRunStatus,
  getExecutionStatus,
  type ExecutionSummary,
} from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

const POLL_INTERVAL_MS = 5000;

interface LiveStatus {
  status: string;
  durable_status: string;
}

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const executionsRef = useRef<ExecutionSummary[]>([]);
  const [live, setLive] = useState<Record<string, LiveStatus>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  async function loadList() {
    try {
      setError(null);
      const response = await getExecutions();
      const items = response.items ?? [];
      setExecutions(items);
      executionsRef.current = items;
      await refreshStatuses(items);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load executions"
      );
    } finally {
      setLoading(false);
    }
  }

  async function refreshStatuses(items: ExecutionSummary[]) {
    const updates: Record<string, LiveStatus> = {};
    await Promise.all(
      items.map(async (execution) => {
        try {
          const [pipeline, durable] = await Promise.all([
            getExecutionStatus(execution.execution_id),
            getExecutionRunStatus(execution.execution_id),
          ]);
          updates[execution.execution_id] = {
            status: pipeline.status,
            durable_status: durable.durable_status,
          };
        } catch {
          updates[execution.execution_id] = {
            status: "unknown",
            durable_status: "unknown",
          };
        }
      })
    );
    setLive((previous) => ({ ...previous, ...updates }));
  }

  async function onRefresh() {
    setLoading(true);
    await loadList();
  }

  useEffect(() => {
    loadList();
    const timer = setInterval(() => {
      refreshStatuses(executionsRef.current);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div>
        <h1>Executions</h1>
        <p className="muted">Loading executions…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1>Executions</h1>
        <div className="card">
          <p className="error">{error}</p>
          <button type="button" onClick={onRefresh}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1>Executions</h1>
      <p className="muted">
        Durable execution runs driven by the orchestrator through the coding
        pipeline (provision → prepare → start-session → run). Statuses poll
        every {POLL_INTERVAL_MS / 1000}s.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
          <button type="button" onClick={onRefresh}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          {lastUpdated && (
            <span className="muted">Last updated {lastUpdated}</span>
          )}
        </div>

        {executions.length === 0 ? (
          <p className="placeholder">No executions yet. Launch a task from Tasks to create one.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Execution</th>
                <th>Task</th>
                <th>Pipeline status</th>
                <th>Durable status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {executions.map((execution) => {
                const current = live[execution.execution_id] ?? {
                  status: execution.status,
                  durable_status: "",
                };
                return (
                  <tr key={execution.execution_id}>
                    <td>
                      <span className="mono">{execution.execution_id}</span>
                    </td>
                    <td>
                      <strong>#{execution.task_id}</strong>{" "}
                      {execution.task_title}
                    </td>
                    <td>
                      <StatusBadge status={current.status} />
                    </td>
                    <td>
                      <StatusBadge status={current.durable_status ?? ""} />
                    </td>
                    <td></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
