import { api, type ListResponse, type Task } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  let tasks: Task[] = [];
  let error = false;
  try {
    const res = await api<ListResponse<Task>>("/tasks");
    tasks = res.items;
  } catch {
    error = true;
  }

  return (
    <div>
      <h1>Tasks</h1>
      <p className="muted">
        Task backlog, dependencies, assignments, status, and execution results (Phase 4).
      </p>

      {error ? (
        <div className="card">
          <p className="error">Unable to load tasks (is the API running?).</p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="card">
          <p className="placeholder">No tasks yet.</p>
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assigned</th>
                <th>Dependencies</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td>
                    <strong>{t.title}</strong>
                    <span className="muted"> (#{t.id})</span>
                    {t.target_branch && <span className="muted"> — {t.target_branch}</span>}
                    {t.result_summary && <div className="muted">{t.result_summary}</div>}
                  </td>
                  <td>
                    <span className="badge">{t.task_type}</span>
                  </td>
                  <td>
                    <span className="badge">{t.priority}</span>
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>{t.assigned_role ?? <span className="placeholder">unassigned</span>}</td>
                  <td>
                    {t.dependencies.length > 0 ? (
                      t.dependencies.map((d) => (
                        <span key={d} className="badge">
                          #{d}
                        </span>
                      ))
                    ) : (
                      <span className="placeholder">none</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
