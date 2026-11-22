"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteModel, testModel, type CapabilityInfo, type ModelInfo } from "@/lib/api";
import { EditModelForm } from "@/components/edit-model-form";

export function ModelsList({
  models,
  capabilities,
}: {
  models: ModelInfo[];
  capabilities: CapabilityInfo[];
}) {
  const router = useRouter();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteConfirming, setDeleteConfirming] = useState<number | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{
    modelId: number;
    ok: boolean;
    latency_ms: number;
    response_preview?: string;
    error?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete(modelId: number) {
    setError(null);
    try {
      await deleteModel(modelId);
      setDeletingId(null);
      setDeleteConfirming(null);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete model");
      setDeletingId(null);
      setDeleteConfirming(null);
    }
  }

  async function handleTest(modelId: number) {
    setError(null);
    setTestingId(modelId);
    setTestResult(null);
    try {
      const result = await testModel(modelId);
      setTestResult({ modelId, ...result });
    } catch (err) {
      setTestResult({
        modelId,
        ok: false,
        error: err instanceof Error ? err.message : "Test failed",
        latency_ms: 0,
      });
    } finally {
      setTestingId(null);
    }
  }

  if (models.length === 0) {
    return (
      <div className="card">
        <h2>Models</h2>
        <p className="placeholder">No models registered yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Models</h2>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Provider</th>
            <th>Capabilities</th>
            <th>Status</th>
            <th>Test</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => {
            const isEditing = editingId === model.id;
            const isDeleting = deletingId === model.id;
            const isConfirming = deleteConfirming === model.id;
            return (
              <tr key={model.id}>
                <td>
                  {isEditing ? (
                    <input
                      defaultValue={model.name}
                      readOnly
                      className="mono"
                    />
                  ) : (
                    <strong>{model.name}</strong>
                  )}
                  <br />
                  <span className="muted mono">{model.provider_name}</span>
                </td>
                <td className="muted">{model.capabilities.join(", ")}</td>
                <td>
                  <span
                    className={
                      "badge " +
                      (model.is_active ? "ok" : "muted")
                    }
                  >
                    {model.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  {model.id === testingId ? (
                    <button type="button" disabled>Testing...</button>
                  ) : testResult && testResult.modelId === model.id ? (
                    <>
                      <button
                        type="button"
                        onClick={() => handleTest(model.id)}
                        disabled={isEditing || isDeleting}
                      >
                        Test again
                      </button>{" "}
                      <div className="test-result">
                        {testResult.ok ? (
                          <span className="ok">
                            ✓ OK ({testResult.latency_ms}ms)
                          </span>
                        ) : (
                          <span className="bad">✗ {testResult.error}</span>
                        )}
                        {testResult.response_preview && (
                          <span className="muted mono">
                            &quot;{testResult.response_preview}&quot;
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleTest(model.id)}
                      disabled={isEditing || isDeleting}
                    >
                      Test
                    </button>
                  )}
                </td>
                <td>
                  {isEditing ? (
                    <EditModelForm
                      model={model}
                      capabilities={capabilities}
                      onSave={() => {
                        setEditingId(null);
                        router.refresh();
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => setEditingId(model.id)}
                        disabled={isDeleting}
                      >
                        Edit
                      </button>{" "}
                      {isConfirming ? (
                        <>
                          <button
                            type="button"
                            onClick={() => handleDelete(model.id)}
                            className="danger"
                          >
                            Delete
                          </button>{" "}
                          <button
                            type="button"
                            onClick={() => setDeleteConfirming(null)}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setDeleteConfirming(model.id)}
                          disabled={isEditing}
                          className="danger"
                        >
                          Delete
                        </button>
                      )}
                    </>
                  )}
                  {error && <p className="error">{error}</p>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
