import { api, type ListResponse, type Workflow, type WorkflowTemplate } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export const dynamic = "force-dynamic";

export default async function WorkflowsPage() {
  let workflows: Workflow[] = [];
  let templates: WorkflowTemplate[] = [];
  let error = false;
  try {
    const res = await api<ListResponse<Workflow>>("/workflows");
    workflows = res.items;
    const tpl = await api<ListResponse<WorkflowTemplate>>("/workflows/templates");
    templates = tpl.items;
  } catch {
    error = true;
  }

  return (
    <div>
      <h1>Workflows</h1>
      <p className="muted">
        Durable workflow instances, stage status, retries, and failure details (Phase 4).
      </p>

      {error ? (
        <div className="card">
          <p className="error">Unable to load workflows (is the API running?).</p>
        </div>
      ) : (
        <>
          <div className="card">
            <h2>Available Templates</h2>
            <ul className="list">
              {templates.map((t) => (
                <li key={t.id}>
                  <strong>{t.name}</strong> <span className="badge">{t.slug}</span>
                  {t.description && <span className="muted"> — {t.description}</span>}
                </li>
              ))}
              {templates.length === 0 && <li className="placeholder">No templates yet.</li>}
            </ul>
          </div>

          <div className="card">
            <h2>Workflow Instances</h2>
            {workflows.length === 0 ? (
              <p className="placeholder">No workflow instances yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Workflow</th>
                    <th>Status</th>
                    <th>Stages</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <strong>{w.name}</strong>
                        <span className="muted"> (#{w.id})</span>
                        {w.error_message && <div className="error">Error: {w.error_message}</div>}
                      </td>
                      <td>
                        <StatusBadge status={w.status} />
                      </td>
                      <td>
                        <StageList stages={w.stages} />
                      </td>
                      <td className="muted">
                        {w.started_at ? new Date(w.started_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StageList({ stages }: { stages: Workflow["stages"] }) {
  return (
    <ol className="stage-list">
      {stages.map((s) => (
        <li key={s.id}>
          <StatusBadge status={s.status} />
          <span> {s.name}</span>
          {s.retries > 0 && <span className="muted"> (retries: {s.retries})</span>}
          {s.error_message && <div className="error">{s.error_message}</div>}
        </li>
      ))}
    </ol>
  );
}
