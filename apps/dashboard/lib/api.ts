function resolveApiBaseUrl(): string {
  // Inlined at build time for the browser bundle.
  const publicUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

  // In the browser, call the API through the same origin (the nginx reverse
  // proxy serves /api/). Same-origin requests never trigger CORS and carry the
  // session cookie naturally.
  if (typeof window !== "undefined") {
    return publicUrl;
  }

  // On the server (SSR / React Server Components), fetch runs inside the
  // dashboard container where a relative URL cannot be resolved. Prefer an
  // explicit internal URL that reaches the API over the Docker network.
  if (process.env.API_INTERNAL_BASE_URL) {
    return process.env.API_INTERNAL_BASE_URL;
  }
  if (/^https?:\/\//i.test(publicUrl)) {
    return publicUrl;
  }
  return "http://api:8000/api/v1";
}

const API_BASE_URL = resolveApiBaseUrl();

interface RequestOptions {
  method?: string;
  body?: unknown;
  credentials?: RequestCredentials;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: options.credentials ?? "include",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  default_branch: string;
  is_active: boolean;
  created_at: string;
  repositories: Repository[];
}

export interface Repository {
  id: number;
  project_id: number;
  url: string;
  default_branch: string;
  adapter_status: string;
  adapter_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  actor_id: number | null;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: string | null;
  created_at: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface OperatorStatus {
  email: string | null;
  is_authenticated: boolean;
}

export const getProjects = (includeInactive = false) =>
  api<ListResponse<Project>>(`/projects${includeInactive ? "?include_inactive=true" : ""}`);
export const createProject = (data: {
  name: string;
  description?: string;
  repositories?: { url: string; default_branch?: string }[];
}) => api<Project>("/projects", { method: "POST", body: data });
export const getAuditLogs = () => api<ListResponse<AuditLog>>("/audit");
export const getHealth = () => api<{ status: string }>("/health");
export const getOperatorStatus = () => api<OperatorStatus>("/auth/me");
export const login = (data: { email: string; password: string }) =>
  api<{ email: string; display_name: string | null; is_operator: boolean }>("/auth/login", {
    method: "POST",
    body: data,
  });
export const logout = () => api<null>("/auth/logout", { method: "POST" });

export interface AgentVersion {
  id: number;
  agent_id: number;
  version: string;
  status: "draft" | "candidate" | "active" | "retired";
  instructions: string;
  capabilities: string[];
  model_profile: string;
  quality_gates: string[];
  skills: { skill_name: string; position: number }[];
  tool_permissions: { tool_name: string; permissions: Record<string, boolean>; position: number }[];
  definition_hash: string | null;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: number;
  slug: string;
  name: string;
  role: string;
  description: string | null;
  is_active: boolean;
  versions: AgentVersion[];
  created_at: string;
  updated_at: string;
}

export interface ModelProvider {
  id: number;
  name: string;
  provider_type: string;
  base_url: string;
  credential_ref: string | null;
  timeout_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelInfo {
  id: number;
  provider_id: number;
  provider_name: string | null;
  name: string;
  display_name: string | null;
  capabilities: string[];
  context_window: number | null;
  input_cost_per_million: number | null;
  output_cost_per_million: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelProfile {
  id: number;
  name: string;
  description: string | null;
  primary_model_id: number | null;
  fallback_model_ids: number[];
  required_capabilities: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderHealth {
  provider_id: number;
  provider_name: string;
  provider_type: string;
  base_url: string;
  status: string;
  connectivity: { ok: boolean; latency_ms: number | null; detail: string | null };
  capabilities: Record<
    string,
    { capability: string; supported: boolean | null; detail: string | null }
  >;
  model_count: number;
}

export interface ToolInfo {
  id: number;
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  required_permissions: string[];
  is_active: boolean;
}

export interface SkillInfo {
  id: number;
  name: string;
  description: string;
  instructions: string | null;
  files: string[];
  is_active: boolean;
}

export const getAgents = (includeInactive = false) =>
  api<ListResponse<Agent>>(`/agents${includeInactive ? "?include_inactive=true" : ""}`);
export const getAgent = (id: number) => api<Agent>(`/agents/${id}`);
export const createAgent = (data: unknown) => api<Agent>("/agents", { method: "POST", body: data });
export const getAgentVersions = (id: number) =>
  api<ListResponse<AgentVersion>>(`/agents/${id}/versions`);
export const createAgentVersion = (id: number, data: unknown) =>
  api<AgentVersion>(`/agents/${id}/versions`, { method: "POST", body: data });
export const agentVersionAction = (versionId: number, action: string) =>
  api<AgentVersion>(`/agents/versions/${versionId}/action`, { method: "POST", body: { action } });

export const getModelProviders = (includeInactive = false) =>
  api<ListResponse<ModelProvider>>(
    `/models/providers${includeInactive ? "?include_inactive=true" : ""}`
  );
export const createModelProvider = (data: unknown) =>
  api<ModelProvider>("/models/providers", { method: "POST", body: data });
export const getModels = () => api<ListResponse<ModelInfo>>("/models/items");
export const getProviderModels = (providerId: number) =>
  api<ListResponse<ModelInfo>>(`/models/providers/${providerId}/models`);
export const createModel = (providerId: number, data: unknown) =>
  api<ModelInfo>(`/models/providers/${providerId}/models`, { method: "POST", body: data });
export const getModelProfiles = () => api<ListResponse<ModelProfile>>("/models/profiles");
export const createModelProfile = (data: unknown) =>
  api<ModelProfile>("/models/profiles", { method: "POST", body: data });
export const getProviderHealth = () => api<ListResponse<ProviderHealth>>("/models/health");
export const checkProvider = (providerId: number) =>
  api<ProviderHealth>(`/models/providers/${providerId}/check`, { method: "POST" });

export const getTools = () => api<ListResponse<ToolInfo>>("/registries/tools");
export const getSkills = () => api<ListResponse<SkillInfo>>("/registries/skills");

// --- Workflows (Phase 4.2/4.7) ---------------------------------------------

export interface WorkflowStage {
  id: number;
  workflow_id: number;
  position: number;
  name: string;
  agent_role: string;
  status: string;
  retries: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface Workflow {
  id: number;
  project_id: number;
  template_id: number;
  name: string;
  status: string;
  inputs: Record<string, unknown>;
  error_message: string | null;
  stages: WorkflowStage[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplateStage {
  id: number;
  position: number;
  name: string;
  agent_role: string;
  depends_on: string[];
}

export interface WorkflowTemplate {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  category: string;
  input_schema: Record<string, unknown>;
  is_active: boolean;
  stages: WorkflowTemplateStage[];
  created_at: string;
  updated_at: string;
}

export const getWorkflows = (projectId?: number) =>
  api<ListResponse<Workflow>>(`/workflows${projectId ? `?project_id=${projectId}` : ""}`);
export const getWorkflow = (id: number) => api<Workflow>(`/workflows/${id}`);
export const createWorkflow = (data: {
  project_id: number;
  template_id: number;
  name: string;
  inputs?: Record<string, unknown>;
}) => api<Workflow>("/workflows", { method: "POST", body: data });
export const scheduleWorkflow = (id: number) =>
  api<Workflow>(`/workflows/${id}/schedule`, { method: "POST" });
export const advanceWorkflow = (id: number) =>
  api<Workflow>(`/workflows/${id}/advance`, { method: "POST" });
export const cancelWorkflow = (id: number) =>
  api<Workflow>(`/workflows/${id}/cancel`, { method: "POST" });
export const recoverWorkflow = (id: number) =>
  api<Workflow>(`/workflows/${id}/recover`, { method: "POST" });
export const getWorkflowTemplates = (includeInactive = false) =>
  api<ListResponse<WorkflowTemplate>>(
    `/workflows/templates${includeInactive ? "?include_inactive=true" : ""}`
  );

// --- Tasks (Phase 4.3/4.7) -------------------------------------------------

export interface Task {
  id: number;
  project_id: number;
  workflow_id: number | null;
  title: string;
  description: string | null;
  task_type: string;
  priority: string;
  status: string;
  acceptance_criteria: string | null;
  repository_url: string | null;
  target_branch: string;
  assigned_role: string | null;
  assigned_agent_id: number | null;
  skills: string[];
  model_profile: string | null;
  relevant_files: string[];
  cpu_limit: number | null;
  memory_limit: string | null;
  disk_limit: string | null;
  timeout_seconds: number | null;
  network_policy: string | null;
  result_summary: string | null;
  artefact_refs: string[];
  dependencies: number[];
  depends_on: number[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export const getTasks = (projectId?: number, statusFilter?: string) => {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", String(projectId));
  if (statusFilter) params.set("status_filter", statusFilter);
  const qs = params.toString();
  return api<ListResponse<Task>>(`/tasks${qs ? `?${qs}` : ""}`);
};
export const getTask = (id: number) => api<Task>(`/tasks/${id}`);
export const createTask = (data: Record<string, unknown>) =>
  api<Task>("/tasks", { method: "POST", body: data });
export const updateTask = (id: number, data: Record<string, unknown>) =>
  api<Task>(`/tasks/${id}`, { method: "PATCH", body: data });
export const transitionTaskStatus = (id: number, status: string, note?: string) =>
  api<Task>(`/tasks/${id}/status`, { method: "POST", body: { status, ...(note ? { note } : {}) } });
export const setTaskDependencies = (id: number, dependsOn: number[]) =>
  api<Task>(`/tasks/${id}/dependencies`, { method: "POST", body: { depends_on: dependsOn } });
