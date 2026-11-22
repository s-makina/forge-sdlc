"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { checkProvider } from "@/lib/api";

export function CheckProviderButton({ providerId }: { providerId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function onClick() {
    setBusy(true);
    setResult(null);
    try {
      const health = await checkProvider(providerId);
      const latency = health.connectivity.latency_ms;
      setResult(
        `${health.status}${latency != null ? ` · ${Math.round(latency)} ms` : ""}`,
      );
      router.refresh();
    } catch (err) {
      setResult(err instanceof Error ? err.message : "check failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span>
      <button type="button" onClick={onClick} disabled={busy}>
        {busy ? "Checking..." : "Check"}
      </button>
      {result && <span className="muted"> {result}</span>}
    </span>
  );
}
