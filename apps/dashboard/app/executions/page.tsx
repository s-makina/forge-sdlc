"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getExecutions,
  getExecutionArtefacts,
  getExecutionLogs,
  getExecutionRunStatus,
  getExecutionStatus,
  type ExecutionArtefactsRead,
  type ExecutionLogsRead,
  type ExecutionSummary,
} from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

const POLL_INTERVAL_MS = 5000;

interface LiveStatus {
  status: string;
  durable_status: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function shortTime(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const executionsRef = useRef<ExecutionSummary[]>([]);
  const [live, setLive] = useState<Record<string, LiveStatus>>({});
  const [open, setOpen] = useState<Set<string>>(new Set());
  const openRef = useRef<Set<string>>(new Set());
  const [logs, setLogs] = useState<Record<string, ExecutionLogsRead>>({});
  const [artefacts, setArtefacts] = useState<Record<string, ExecutionArtefactsRead>>(
    {}
  );
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
      // Re-fetch details for currently open executions.
      await Promise.all(
        items
          .filter((e) => open.has(e.execution_id))
          .map((e) => fetchDetails(e.execution_id))
      );
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load executions");
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

  async function fetchDetails(execution_id: string) {
    try {
      const [logRes, artRes] = await Promise.all([
        getExecutionLogs(execution_id),
        getExecutionArtefacts(execution_id),
      ]);
      setLogs((prev) => ({ ...prev, [execution_id]: logRes }));
      setArtefacts((prev) => ({ ...prev, [execution_id]: artRes }));
    } catch {
      // details degrade gracefully; leave previous/empty
    }
  }

  async function onRefresh() {
    setLoading(true);
    await loadList();
  }

  function toggleOpen(execution_id: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(execution_id)) next.delete(execution_id);
      else next.add(execution_id);
      openRef.current = next;
      if (next.has(execution_id)) {
        void fetchDetails(execution_id);
      }
      return next;
    });
  }

  useEffect(() => {
    loadList();
    const timer = setInterval(() => {
      refreshStatuses(executionsRef.current);
      // Keep details of open executions live.
      Promise.all(
        executionsRef.current
          .filter((e) => openRef.current.has(e.execution_id))
          .map((e) => fetchDetails(e.execution_id))
      );
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
        every {POLL_INTERVAL_MS / 1000}s. Open a row to view its activity log
        and artefacts.
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
          <p className="placeholder">
            No executions yet. Launch a task from Tasks to create one.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Execution</th>
                <th>Task</th>
                <th>Pipeline status</th>
                <th>Durable status</th>
              </tr>
            </thead>
            <tbody>
              {executions.map((execution) => {
                const current =
                  live[execution.execution_id] ?? {
                    status: execution.status,
                    durable_status: "",
                  };
                const isOpen = open.has(execution.execution_id);

                const detailRow = (
                  <tr>
                    <td colSpan={5}>
                      <div className="card" style={{ margin: "0.5rem 0", padding: "0.75rem 1rem" }}>
                        <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                          <div style={{ minWidth: "260px" }}>
                            <h3
                              style={{
                                margin: "0 0 0.5rem 0",
                                fontSize: "0.95rem",
                              }}
                            >
                              Activity log
                            </h3>
                            {logs[execution.execution_id]?.entries.length ? (
                              <table
                                style={{ width: "100%", fontSize: "0.85rem" }}
                              >
                                <thead>
                                  <tr>
                                    <th style={{ textAlign: "left" }}>#</th>
                                    <th style={{ textAlign: "left" }}>Time</th>
                                    <th style={{ textAlign: "left" }}>Level</th>
                                    <th style={{ textAlign: "left" }}>Kind</th>
                                    <th style={{ textAlign: "left" }}>
                                      Message
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {logs[execution.execution_id]!.entries.map(
                                    (entry) => (
                                      <tr
                                        key={entry.sequence}
                                        style={{ borderBottom: "1px solid #edf2f7" }}
                                      >
                                        <td>{entry.sequence}</td>
                                        <td>{shortTime(entry.timestamp)}</td>
                                        <td>{entry.level}</td>
                                        <td>
                                          <span className="mono">{entry.kind}</span>
                                        </td>
                                        <td>{entry.message}</td>
                                      </tr>
                                    )
                                  )}
                                </tbody>
                              </table>
                            ) : (
                              <p className="placeholder">
                                No activity log captured yet.
                              </p>
                            )}
                          </div>
                          <div style={{ minWidth: "260px" }}>
                            <h3
                              style={{
                                margin: "0 0 0.5rem 0",
                                fontSize: "0.95rem",
                              }}
                            >
                              Artefacts
                            </h3>
                            {artefacts[execution.execution_id]?.artefacts.length ? (
                              <table
                                style={{ width: "100%", fontSize: "0.85rem" }}
                              >
                                <thead>
                                  <tr>
                                    <th style={{ textAlign: "left" }}>Name</th>
                                    <th style={{ textAlign: "left" }}>Size</th>
                                    <th style={{ textAlign: "left" }}>Kind</th>
                                    <th style={{ textAlign: "left" }}>
                                      MIME type
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {artefacts[execution.execution_id]!.artefacts.map(
                                    (a) => (
                                      <tr
                                        key={a.name}
                                        style={{ borderBottom: "1px solid #edf2f7" }}
                                      >
                                        <td>
                                          <span className="mono">{a.name}</span>
                                        </td>
                                        <td>{formatBytes(a.size_bytes)}</td>
                                        <td>{a.kind ?? <span className="placeholder">—</span>}</td>
                                        <td>
                                          {a.mime_type ?? (
                                            <span className="placeholder">—</span>
                                          )}
                                        </td>
                                      </tr>
                                    )
                                  )}
                                </tbody>
                              </table>
                            ) : (
                              <p className="placeholder">
                                No artefacts captured yet.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                );

                return (
                  <>
                    <tr
                      key={execution.execution_id}
                      onClick={() => toggleOpen(execution.execution_id)}
                      style={{ cursor: "pointer" }}
                    >
                      <td>
                        <span className="badge">{isOpen ? "▾" : "▸"}</span>
                      </td>
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
                    </tr>
                    {isOpen && detailRow}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
