"use client";

import { useState } from "react";
import { type ModelProvider } from "@/lib/api";
import { EditProviderForm } from "@/components/edit-provider-form";

export function EditProviderButton({ provider }: { provider: ModelProvider }) {
  const [editing, setEditing] = useState(false);

  if (!editing) {
    return (
      <button type="button" onClick={() => setEditing(true)}>
        Edit
      </button>
    );
  }

  return <EditProviderForm provider={provider} onClose={() => setEditing(false)} />;
}