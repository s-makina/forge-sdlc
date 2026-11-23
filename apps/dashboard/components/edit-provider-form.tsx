"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { updateModelProvider, type ModelProvider } from "@/lib/api";

export function EditProviderForm({ provider, onClose }: { provider: ModelProvider; onClose: () => void }) {
  const router = useRouter();
  const [name, setName] = useState(provider.name);
  const [baseUrl, setBaseUrl] = useState(provider.base_url);
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(provider.timeout_seconds));
  const [isActive, setIsActive] = useState(provider.is_active);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await updateModelProvider(provider.id, {
        name,
        base_url: baseUrl,
        api_key: apiKey || null,
        clear_api_key: clearApiKey && !apiKey,
        timeout_seconds: Number(timeoutSeconds),
        is_active: isActive,
      });
      onClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update provider");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h2>Edit Provider</h2>
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
          API key {provider.has_api_key ? "(leave blank to keep current key)" : ""}
          <input
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              if (e.target.value) setClearApiKey(false);
            }}
            placeholder={provider.has_api_key ? "Paste a new API key to replace it" : "Paste provider API key"}
          />
        </label>
      </div>
      {provider.has_api_key && (
        <div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={clearApiKey}
              onChange={(e) => {
                setClearApiKey(e.target.checked);
                if (e.target.checked) setApiKey("");
              }}
            />
            Clear current API key
          </label>
        </div>
      )}
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
      <div>
        <label className="checkbox">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      </div>
      <p className="muted">
        API keys are encrypted before storage and are never shown again. Enter the raw key here;
        writing the LiteLLM config will place it in the local config file.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="row-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Save Changes"}
        </button>
        <button type="button" className="secondary" onClick={onClose} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  );
}