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
