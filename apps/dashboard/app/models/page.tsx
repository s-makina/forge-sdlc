import {
  api,
  type ListResponse,
  type ModelInfo,
  type ModelProfile,
  type ModelProvider,
  type ProviderHealth,
  type SkillInfo,
  type ToolInfo,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  let providers: ModelProvider[] = [];
  let models: ModelInfo[] = [];
  let profiles: ModelProfile[] = [];
  let health: ProviderHealth[] = [];
  let tools: ToolInfo[] = [];
  let skills: SkillInfo[] = [];
  let error = false;

  const get = async <T,>(fn: Promise<T>) => {
    try {
      return await fn;
    } catch {
      return undefined;
    }
  };

  const [p, m, pf, h, t, sk] = await Promise.all([
    get(api<ListResponse<ModelProvider>>("/models/providers").then((r) => r.items)),
    get(api<ListResponse<ModelInfo>>("/models/items").then((r) => r.items)),
    get(api<ListResponse<ModelProfile>>("/models/profiles").then((r) => r.items)),
    get(api<ListResponse<ProviderHealth>>("/models/health").then((r) => r.items)),
    get(api<ListResponse<ToolInfo>>("/registries/tools").then((r) => r.items)),
    get(api<ListResponse<SkillInfo>>("/registries/skills").then((r) => r.items)),
  ]);

  if (p === undefined && m === undefined && pf === undefined) error = true;
  providers = p ?? [];
  models = m ?? [];
  profiles = pf ?? [];
  health = h ?? [];
  tools = t ?? [];
  skills = sk ?? [];

  const modelsByProvider = (providerId: number) =>
    models.filter((m) => m.provider_id === providerId);
  const profileFor = (profile: ModelProfile) =>
    models.find((m) => m.id === profile.primary_model_id) ?? null;

  return (
    <div>
      <h1>Models</h1>
      {error && <p className="error">Unable to load model configuration.</p>}

      <div className="card">
        <h2>Providers &amp; Health</h2>
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Type</th>
              <th>Base URL</th>
              <th>Credential</th>
              <th>Status</th>
              <th>Models</th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => {
              const healthRow = health.find((hd) => hd.provider_id === provider.id);
              return (
                <tr key={provider.id}>
                  <td>{provider.name}</td>
                  <td>{provider.provider_type}</td>
                  <td className="muted">{provider.base_url}</td>
                  <td className="muted">{provider.credential_ref ?? "none"}</td>
                  <td>
                    <span className={"badge " + (healthRow?.status === "ok" ? "ok" : "muted")}>
                      {healthRow?.status ?? "unchecked"}
                    </span>
                  </td>
                  <td>{modelsByProvider(provider.id).length}</td>
                </tr>
              );
            })}
            {providers.length === 0 && (
              <tr>
                <td colSpan={6} className="placeholder">
                  No providers configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Models</h2>
        <ul className="list">
          {models.map((model) => (
            <li key={model.id}>
              <strong>{model.name}</strong>{" "}
              <span className="muted">
                · {model.provider_name} · {model.capabilities.join(", ")}
              </span>
            </li>
          ))}
          {models.length === 0 && <li className="placeholder">No models registered yet.</li>}
        </ul>
      </div>

      <div className="card">
        <h2>Model Profiles</h2>
        <ul className="list">
          {profiles.map((profile) => {
            const target = profileFor(profile);
            return (
              <li key={profile.id}>
                <span className="badge">{profile.name}</span> {profile.description}
                <span className="muted">
                  {" "}
                  → {target ? target.name : "no model assigned"} · requires{" "}
                  {profile.required_capabilities.join(", ") || "chat"}
                </span>
              </li>
            );
          })}
          {profiles.length === 0 && <li className="placeholder">No profiles configured.</li>}
        </ul>
      </div>

      <div className="card">
        <h2>Tool &amp; Skill Registries</h2>
        <div className="two-col">
          <div>
            <h3>Tools</h3>
            <ul className="list">
              {tools.map((tool) => (
                <li key={tool.id}>{tool.name}</li>
              ))}
              {tools.length === 0 && <li className="placeholder">None.</li>}
            </ul>
          </div>
          <div>
            <h3>Skills</h3>
            <ul className="list">
              {skills.map((skill) => (
                <li key={skill.id}>{skill.name}</li>
              ))}
              {skills.length === 0 && <li className="placeholder">None.</li>}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
