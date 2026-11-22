import {
  api,
  getAgentVersions,
  type AgentSummary,
  type AgentVersion,
  type ListResponse,
} from "@/lib/api";

export const dynamic = "force-dynamic";

type AgentWithVersions = AgentSummary & { versions: AgentVersion[] };

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  candidate: "Candidate",
  active: "Active",
  retired: "Retired",
};

export default async function AgentsPage() {
  let agents: AgentWithVersions[] = [];
  let error = false;
  try {
    const res = await api<ListResponse<AgentSummary>>("/agents");
    const versionLists = await Promise.all(res.items.map((agent) => getAgentVersions(agent.id)));
    agents = res.items.map((agent, index) => ({
      ...agent,
      versions: versionLists[index].items,
    }));
  } catch {
    error = true;
  }

  return (
    <div>
      <h1>Agent Registry</h1>
      {error ? (
        <p className="error">Unable to load agents (is the API running?).</p>
      ) : (
        <div>
          {agents.map((agent) => {
            const active = agent.versions.find((v) => v.status === "active");
            return (
              <div className="card" key={agent.id}>
                <h2>
                  {agent.name} <span className="badge">{agent.role}</span>
                </h2>
                {active ? (
                  <p>
                    Active version{" "}
                    <span className="badge">
                      v{active.version} · {active.model_profile}
                    </span>
                  </p>
                ) : (
                  <p className="placeholder">No active version.</p>
                )}
                <ul className="list">
                  {agent.versions.map((version) => (
                    <li key={version.id}>
                      <span className="badge">
                        {STATUS_LABEL[version.status] ?? version.status}
                      </span>{" "}
                      v{version.version} · {version.model_profile}
                      <span className="placeholder">
                        {" "}
                        · {version.capabilities.join(", ") || "no capabilities"}
                      </span>
                    </li>
                  ))}
                  {agent.versions.length === 0 && <li className="placeholder">No versions yet.</li>}
                </ul>
              </div>
            );
          })}
          {agents.length === 0 && <p className="placeholder">No agents registered.</p>}
        </div>
      )}
    </div>
  );
}
