"use client";

import { useState } from "react";
import { updateModel, type CapabilityInfo, type ModelInfo } from "@/lib/api";

export function EditModelForm({
  model,
  capabilities,
  onSave,
  onCancel,
}: {
  model: ModelInfo;
  capabilities: CapabilityInfo[];
  onSave: (updated: ModelInfo) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(model.name);
  const [displayName, setDisplayName] = useState(model.display_name ?? "");
  const [contextWindow, setContextWindow] = useState(
    model.context_window ? String(model.context_window) : "",
  );
  const [selected, setSelected] = useState<string[]>(model.capabilities);
  const [isActive, setIsActive] = useState(model.is_active);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function toggle(value: string) {
    setSelected((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateModel(model.id, {
        name,
        display_name: displayName || undefined,
        capabilities: selected,
        context_window: contextWindow ? Number(contextWindow) : undefined,
        is_active: isActive,
      });
      onSave(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update model");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h3>Edit {model.name}</h3>
      <div>
        <label>
          Model ID
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
      </div>
      <div>
        <label>
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="optional"
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
            placeholder="optional"
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
      <div>
        <label>
          Active
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />{" "}
          Enabled
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="two-col">
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Save"}
        </button>
        <button type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  );
}
