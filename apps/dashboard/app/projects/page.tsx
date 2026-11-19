import { api, type ListResponse, type Project } from "@/lib/api";
import { CreateProjectForm } from "@/components/create-project-form";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  let projects: Project[] = [];
  let error = false;
  try {
    const res = await api<ListResponse<Project>>("/projects");
    projects = res.items;
  } catch {
    error = true;
  }

  return (
    <div>
      <h1>Projects</h1>
      <CreateProjectForm />

      <div className="card">
        <h2>All Projects</h2>
        {error ? (
          <p className="error">Unable to load projects (is the API running?).</p>
        ) : (
          <ul className="list">
            {projects.map((p) => (
              <li key={p.id}>
                <strong>{p.name}</strong>
                {p.repositories.length > 0 && (
                  <span className="placeholder"> - {p.repositories[0].url}</span>
                )}
              </li>
            ))}
            {projects.length === 0 && <li className="placeholder">No projects yet.</li>}
          </ul>
        )}
      </div>
    </div>
  );
}
