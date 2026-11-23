"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { launchTask } from "@/lib/api";

export function LaunchTaskButton({ taskId, disabled }: { taskId: number; disabled: boolean }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  async function onLaunch() {
    setLaunching(true);
    setError(null);
    try {
      const result = await launchTask(taskId);
      setError(`Launched as execution ${result.execution_id}.`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to launch task");
    } finally {
      setLaunching(false);
    }
  }

  return (
    <>
      <button onClick={onLaunch} disabled={disabled || launching}>
        {launching ? "Launching..." : "Launch"}
      </button>
      {error && <div className="muted">{error}</div>}
    </>
  );
}