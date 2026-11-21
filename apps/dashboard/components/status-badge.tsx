const OK_STATUSES = new Set(["succeeded", "completed", "running", "in_progress", "ready"]);
const WARN_STATUSES = new Set(["pending", "assigned", "blocked", "review", "draft"]);
const BAD_STATUSES = new Set(["failed", "cancelled"]);

export function StatusBadge({ status }: { status: string }) {
  const className = BAD_STATUSES.has(status)
    ? "badge bad"
    : WARN_STATUSES.has(status)
      ? "badge warn"
      : OK_STATUSES.has(status)
        ? "badge ok"
        : "badge";
  return <span className={className}>{status}</span>;
}
