import { api, type AuditLog, type ListResponse, type Project } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  let projects: Project[] = [];
  let auditLogs: AuditLog[] = [];
  let projectsError = false;
  let auditError = false;

  try {
    const res = await api<ListResponse<Project>>("/projects");
    projects = res.items;
  } catch {
    projectsError = true;
  }

  try {
    const res = await api<ListResponse<AuditLog>>("/audit");
    auditLogs = res.items;
  } catch {
    auditError = true;
  }

  return (
    <div>
      <h1>Overview</h1>

      <div className="card">
        <h2>Projects</h2>
        {projectsError ? (
          <p className="error">Unable to load projects (is the API running?).</p>
        ) : (
          <ul className="list">
            {projects.map((p) => (
              <li key={p.id}>{p.name}</li>
            ))}
            {projects.length === 0 && <li className="placeholder">No projects yet.</li>}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Recent Activity</h2>
        {auditError ? (
          <p className="error">Unable to load audit log.</p>
        ) : (
          <ul className="list">
            {auditLogs.map((entry) => (
              <li key={entry.id}>
                <span className="badge">{entry.action}</span>{" "}
                {new Date(entry.created_at).toLocaleString()}
              </li>
            ))}
            {auditLogs.length === 0 && <li className="placeholder">No activity yet.</li>}
          </ul>
        )}
      </div>
    </div>
  );
}
