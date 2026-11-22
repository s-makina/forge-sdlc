import {
  api,
  type CapabilityInfo,
  type ListResponse,
  type ModelInfo,
  type ModelProfile,
  type ModelProvider,
  type ProviderHealth,
  type SkillInfo,
  type ToolInfo,
} from "@/lib/api";
import { ApplyGatewayConfigButton } from "@/components/apply-gateway-config-button";
import { AssignProfileForm } from "@/components/assign-profile-form";
import { CheckProviderButton } from "@/components/check-provider-button";
import { CreateModelForm } from "@/components/create-model-form";
import { CreateProviderForm } from "@/components/create-provider-form";
import { ModelsList } from "@/components/models-list";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  let providers: ModelProvider[] = [];
  let models: ModelInfo[] = [];
  let profiles: ModelProfile[] = [];
  let health: ProviderHealth[] = [];
  let tools: ToolInfo[] = [];
  let skills: SkillInfo[] = [];
  let capabilities: CapabilityInfo[] = [];
  let error = false;

  const get = async <T,>(fn: Promise<T>) => {
    try {
      return await fn;
    } catch {
      return undefined;
    }
  };

  const [p, m, pf, h, t, sk, c] = await Promise.all([
    get(api<ListResponse<ModelProvider>>("/models/providers").then((r) => r.items)),
    get(api<ListResponse<ModelInfo>>("/models/items").then((r) => r.items)),
    get(api<ListResponse<ModelProfile>>("/models/profiles").then((r) => r.items)),
    get(api<ListResponse<ProviderHealth>>("/models/health").then((r) => r.items)),
    get(api<ListResponse<ToolInfo>>("/registries/tools").then((r) => r.items)),
    get(api<ListResponse<SkillInfo>>("/registries/skills").then((r) => r.items)),
    get(api<{ items: CapabilityInfo[] }>("/models/capabilities").then((r) => r.items)),
  ]);

  if (p === undefined && m === undefined && pf === undefined) error = true;
  providers = p ?? [];
  models = m ?? [];
  profiles = pf ?? [];
  health = h ?? [];
  tools = t ?? [];
  skills = sk ?? [];
  capabilities = c ?? [];

  const modelsByProvider = (providerId: number) =>
    models.filter((m) => m.provider_id === providerId);

  return (
    <div>
      <h1>Models</h1>
      {error && <p className="error">Unable to load model configuration.</p>}

      <div className="two-col">
        <CreateProviderForm />
        <CreateModelForm providers={providers} capabilities={capabilities} />
      </div>

      <div className="card">
        <h2>LiteLLM Gateway</h2>
        <p className="muted">
          Write the current provider and model list to the mounted LiteLLM config. The LiteLLM
          container must then be restarted before the changed model list is active.
        </p>
        <ApplyGatewayConfigButton />
      </div>

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
              <th>Actions</th>
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
                  <td className="muted">
                    {provider.has_api_key ? "Configured" : provider.credential_ref ?? "none"}
                  </td>
                  <td>
                    <span className={"badge " + (healthRow?.status === "ok" ? "ok" : "muted")}>
                      {healthRow?.status ?? "unchecked"}
                    </span>
                  </td>
                  <td>{modelsByProvider(provider.id).length}</td>
                  <td>
                    <CheckProviderButton providerId={provider.id} />
                  </td>
                </tr>
              );
            })}
            {providers.length === 0 && (
              <tr>
                <td colSpan={7} className="placeholder">
                  No providers configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <ModelsList models={models} capabilities={capabilities} />

      <div className="card">
        <h2>Model Profiles (roles)</h2>
        <AssignProfileForm profiles={profiles} models={models} />
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
