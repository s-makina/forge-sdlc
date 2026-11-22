"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  createModel,
  type CapabilityInfo,
  type ModelProvider,
} from "@/lib/api";

export function CreateModelForm({
  providers,
  capabilities,
}: {
  providers: ModelProvider[];
  capabilities: CapabilityInfo[];
}) {
  const router = useRouter();
  const [providerId, setProviderId] = useState(
    providers.length > 0 ? String(providers[0].id) : "",
  );
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [contextWindow, setContextWindow] = useState("");
  const [selected, setSelected] = useState<string[]>(["chat"]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // The provider list can arrive after mount (e.g. after adding the first one).
  const selectedProvider =
    providerId || (providers.length > 0 ? String(providers[0].id) : "");

  function toggle(value: string) {
    setSelected((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProvider) {
      setError("Add a provider first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createModel(Number(selectedProvider), {
        name,
        display_name: displayName || undefined,
        capabilities: selected,
        context_window: contextWindow ? Number(contextWindow) : undefined,
      });
      setName("");
      setDisplayName("");
      setContextWindow("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add model");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h2>Add Model</h2>
      <div>
        <label>
          Provider
          <select
            value={selectedProvider}
            onChange={(e) => setProviderId(e.target.value)}
            disabled={providers.length === 0}
          >
            {providers.length === 0 && <option value="">No providers yet</option>}
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div>
        <label>
          Model ID
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="meta/llama-3.3-70b-instruct"
          />
        </label>
      </div>
      <p className="muted">
        Use the exact model ID from the provider. For NVIDIA NIM, list them with{" "}
        <code>GET https://integrate.api.nvidia.com/v1/models</code>.
      </p>
      <div>
        <label>
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Reviewer (optional)"
          />
        </label>
      </div>
      <div>
        <label>
          Context window
          <input
            type="number"
            min={1}
            value={contextWindow}
            onChange={(e) => setContextWindow(e.target.value)}
            placeholder="131072 (optional)"
          />
        </label>
      </div>
      <fieldset>
        <legend>Capabilities</legend>
        {capabilities.map((capability) => (
          <label key={capability.value} title={capability.description}>
            <input
              type="checkbox"
              checked={selected.includes(capability.value)}
              onChange={() => toggle(capability.value)}
            />{" "}
            {capability.value}
          </label>
        ))}
      </fieldset>
      <p className="muted">
        Only declare what the model really supports. Profiles route on exact capability matches.
      </p>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting || providers.length === 0}>
        {submitting ? "Adding..." : "Add Model"}
      </button>
    </form>
  );
}
