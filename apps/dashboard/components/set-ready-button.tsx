"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { transitionTaskStatus } from "@/lib/api";

export function SetReadyButton({ taskId }: { taskId: number }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [setting, setSetting] = useState(false);

  async function onSetReady() {
    setSetting(true);
    setError(null);
    try {
      await transitionTaskStatus(taskId, "ready");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark task ready");
    } finally {
      setSetting(false);
    }
  }

  return (
    <>
      <button onClick={onSetReady} disabled={setting}>
        {setting ? "Setting..." : "Set ready"}
      </button>
      {error && <div className="muted">{error}</div>}
    </>
  );
}