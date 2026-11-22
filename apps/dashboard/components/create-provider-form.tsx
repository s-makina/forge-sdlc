"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createModelProvider } from "@/lib/api";

export function CreateProviderForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("openai-compatible");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState("120");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createModelProvider({
        name,
        provider_type: providerType,
        base_url: baseUrl,
        api_key: apiKey || null,
        timeout_seconds: Number(timeoutSeconds),
      });
      setName("");
      setBaseUrl("");
      setApiKey("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create provider");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h2>Add Provider</h2>
      <div>
        <label>
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="nvidia-nim"
          />
        </label>
      </div>
      <div>
        <label>
          Type
          <select value={providerType} onChange={(e) => setProviderType(e.target.value)}>
            <option value="openai-compatible">openai-compatible</option>
            <option value="ollama">ollama</option>
          </select>
        </label>
      </div>
      <div>
        <label>
          Base URL
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            required
            placeholder="https://integrate.api.nvidia.com/v1"
          />
        </label>
      </div>
      <div>
        <label>
          API key (optional)
          <input
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste provider API key"
          />
        </label>
      </div>
      <div>
        <label>
          Timeout (seconds)
          <input
            type="number"
            min={1}
            max={600}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(e.target.value)}
          />
        </label>
      </div>
      <p className="muted">
        API keys are encrypted before storage and are never shown again. Enter the raw key here;
        writing the LiteLLM config will place it in the local config file.
      </p>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Adding..." : "Add Provider"}
      </button>
    </form>
  );
}
