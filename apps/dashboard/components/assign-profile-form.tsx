"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  updateModelProfile,
  type ModelInfo,
  type ModelProfile,
} from "@/lib/api";

export function AssignProfileForm({
  profiles,
  models,
}: {
  profiles: ModelProfile[];
  models: ModelInfo[];
}) {
  const router = useRouter();
  const [values, setValues] = useState<Record<number, string>>(() =>
    Object.fromEntries(
      profiles.map((profile) => [
        profile.id,
        profile.primary_model_id != null ? String(profile.primary_model_id) : "",
      ]),
    ),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const valueFor = (profile: ModelProfile) =>
    values[profile.id] ??
    (profile.primary_model_id != null ? String(profile.primary_model_id) : "");

  function optionsFor(profile: ModelProfile): ModelInfo[] {
    const compatible = models.filter((model) =>
      profile.required_capabilities.every((capability) =>
        model.capabilities.includes(capability),
      ),
    );
    const current = models.find((model) => String(model.id) === valueFor(profile));
    if (current && !compatible.some((model) => model.id === current.id)) {
      compatible.unshift(current);
    }
    return compatible;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const changed = profiles.filter((profile) => {
        const original =
          profile.primary_model_id != null ? String(profile.primary_model_id) : "";
        return valueFor(profile) !== original;
      });
      if (changed.length === 0) {
        setMessage("No changes to save.");
        return;
      }
      await Promise.all(
        changed.map((profile) =>
          updateModelProfile(profile.id, {
            primary_model_id: valueFor(profile) ? Number(valueFor(profile)) : null,
          }),
        ),
      );
      setMessage(`Saved ${changed.length} role assignment${changed.length === 1 ? "" : "s"}.`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save assignments");
    } finally {
      setSaving(false);
    }
  }

  if (profiles.length === 0) {
    return <p className="placeholder">No model profiles configured.</p>;
  }

  return (
    <form onSubmit={onSubmit}>
      <table>
        <thead>
          <tr>
            <th>Role</th>
            <th>Requires</th>
            <th>Model</th>
          </tr>
        </thead>
        <tbody>
          {profiles.map((profile) => {
            const options = optionsFor(profile);
            return (
              <tr key={profile.id}>
                <td>
                  <span className="badge">{profile.name}</span>
                  {profile.description && (
                    <div className="muted">{profile.description}</div>
                  )}
                </td>
                <td className="muted">
                  {profile.required_capabilities.join(", ") || "chat"}
                </td>
                <td>
                  <select
                    aria-label={`Model for ${profile.name}`}
                    value={valueFor(profile)}
                    onChange={(e) =>
                      setValues((current) => ({
                        ...current,
                        [profile.id]: e.target.value,
                      }))
                    }
                  >
                    <option value="">unassigned</option>
                    {options.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                  {options.length === 0 && (
                    <div className="muted">No compatible model yet.</div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {error && <p className="error">{error}</p>}
      {message && <p className="muted">{message}</p>}
      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save role assignments"}
      </button>
    </form>
  );
}
