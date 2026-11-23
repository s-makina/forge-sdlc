import { api, type ListResponse, type Project, type Task } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { CreateTaskForm } from "@/components/create-task-form";
import { LaunchTaskButton } from "@/components/launch-task-button";
import type { AgentSummary, ModelProfile } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  let tasks: Task[] = [];
  let projects: { project: Project; repositories: Project["repositories"] }[] = [];
  let roles: string[] = [];
  let modelProfiles: ModelProfile[] = [];
  let error = false;
  try {
    const res = await api<ListResponse<Task>>("/tasks");
    tasks = res.items;
    const proj = await api<ListResponse<Project>>("/projects");
    projects = proj.items.map((p) => ({ project: p, repositories: p.repositories }));
    const agents = await api<ListResponse<AgentSummary>>("/agents");
    roles = Array.from(new Set(agents.items.map((a) => a.role).filter(Boolean)));
    const profiles = await api<ListResponse<ModelProfile>>("/models/profiles");
    modelProfiles = profiles.items.filter((p) => p.is_active);
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
      ) : (
        <>
          <CreateTaskForm projects={projects} roles={roles} modelProfiles={modelProfiles} />

          {tasks.length === 0 ? (
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
                    <th>Execution</th>
                    <th></th>
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
                        {t.last_execution_id ? (
                          <span className="muted">
                            {t.last_execution_id}
                            <StatusBadge status={t.last_execution_status ?? "created"} />
                          </span>
                        ) : (
                          <span className="placeholder">not launched</span>
                        )}
                      </td>
                      <td>
                        <LaunchTaskButton taskId={t.id} disabled={t.status !== "ready"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}