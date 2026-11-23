"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createTask, type Project, type Repository } from "@/lib/api";

const TASK_TYPES = [
  "feature",
  "bugfix",
  "refactoring",
  "dependency",
  "security",
  "performance",
  "testing",
  "documentation",
];

export function CreateTaskForm({
  projects,
}: {
  projects: { project: Project; repositories: Repository[] }[];
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | "">("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [taskType, setTaskType] = useState("feature");
  const [assignedRole, setAssignedRole] = useState("");
  const [modelProfile, setModelProfile] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selected = projects.find((p) => p.project.id === projectId);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (projectId === "") {
      setError("Choose a project before creating the task.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createTask({
        project_id: projectId,
        title,
        description: description || null,
        task_type: taskType,
        acceptance_criteria: acceptanceCriteria || null,
        repository_url: repositoryUrl || null,
        assigned_role: assignedRole || null,
        model_profile: modelProfile || null,
      });
      setTitle("");
      setDescription("");
      setAcceptanceCriteria("");
      setAssignedRole("");
      setModelProfile("");
      setRepositoryUrl("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h2>Create Task</h2>
      <div>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Fix auth bug" />
        </label>
      </div>
      <div>
        <label>
          Project
          <select
            value={projectId}
            onChange={(e) => {
              const val = e.target.value;
              setProjectId(val === "" ? "" : Number(val));
              setRepositoryUrl("");
            }}
            required
          >
            <option value="">Select a project</option>
            {projects.map(({ project }) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div>
        <label>
          Repository (registered to the project)
          <select value={repositoryUrl} onChange={(e) => setRepositoryUrl(e.target.value)}>
            <option value="">— none —</option>
            {selected?.repositories.map((r) => (
              <option key={r.id} value={r.url}>
                {r.url}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div>
        <label>
          Task type
          <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
            {TASK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div>
        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
          />
        </label>
      </div>
      <div>
        <label>
          Acceptance criteria
          <textarea
            value={acceptanceCriteria}
            onChange={(e) => setAcceptanceCriteria(e.target.value)}
            placeholder="Optional acceptance criteria"
          />
        </label>
      </div>
      <div>
        <label>
          Assigned role
          <input
            value={assignedRole}
            onChange={(e) => setAssignedRole(e.target.value)}
            placeholder="software_engineer"
          />
        </label>
      </div>
      <div>
        <label>
          Model profile
          <input value={modelProfile} onChange={(e) => setModelProfile(e.target.value)} placeholder="coding-strong" />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Creating..." : "Create Task"}
      </button>
    </form>
  );
}