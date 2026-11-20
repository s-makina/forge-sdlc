const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
