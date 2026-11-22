"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createModelProvider } from "@/lib/api";

export function CreateProviderForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("openai-compatible");
  const [baseUrl, setBaseUrl] = useState("");
  const [credentialRef, setCredentialRef] = useState("");
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
        credential_ref: credentialRef || null,
        timeout_seconds: Number(timeoutSeconds),
      });
      setName("");
      setBaseUrl("");
      setCredentialRef("");
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
          Credential reference
          <input
            value={credentialRef}
            onChange={(e) => setCredentialRef(e.target.value)}
            placeholder="env:EXTERNAL_MODEL_API_KEY"
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
        Secrets are never stored here. Set the key in <code>.env</code> and reference it as
        <code> env:NAME</code>.
      </p>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Adding..." : "Add Provider"}
      </button>
    </form>
  );
}
