"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { applyGatewayConfig } from "@/lib/api";

export function ApplyGatewayConfigButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await applyGatewayConfig();
      if (result.reloaded) {
        setMessage(
          `Wrote ${result.model_count} model(s) to the LiteLLM config and reloaded the proxy.`,
        );
      } else {
        setMessage(
          `Wrote ${result.model_count} model(s) to the LiteLLM config. Restart LiteLLM to load them.`,
        );
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to write gateway config");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="gateway-config-action">
      <button type="button" onClick={onClick} disabled={busy}>
        {busy ? "Writing config..." : "Write LiteLLM config"}
      </button>
      {message && <p className="muted" role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
