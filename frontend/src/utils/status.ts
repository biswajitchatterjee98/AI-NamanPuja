import type { BatchStatus } from "../api/client";

export const STATUS_META: Record<
  BatchStatus,
  { label: string; tone: "neutral" | "active" | "success" | "warning" | "danger" | "glow" }
> = {
  PENDING: { label: "Queued", tone: "neutral" },
  GENERATING: { label: "Generating", tone: "glow" },
  UNDER_REVIEW: { label: "Awaiting review", tone: "warning" },
  APPROVED: { label: "Approved", tone: "active" },
  REJECTED: { label: "Rejected", tone: "danger" },
  FAILED: { label: "Failed", tone: "danger" },
  CANCELLED: { label: "Stopped", tone: "neutral" },
  UPLOADED: { label: "Published", tone: "success" },
  UPLOAD_PARTIAL: { label: "Partial upload", tone: "warning" },
};

/** Parse API ISO timestamps reliably (UTC when timezone is omitted). */
export function parseApiDate(iso: string): Date | null {
  if (!iso) return null;
  const trimmed = iso.trim();
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(trimmed);
  const normalized = hasTimezone ? trimmed : `${trimmed}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Full datetime for tooltips and detail views. */
export function formatFullDateTime(iso: string): string {
  const date = parseApiDate(iso);
  if (!date) return "Unknown time";

  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** Compact label for batch lists — relative when recent, date+time when older. */
export function formatBatchTime(iso: string): string {
  const date = parseApiDate(iso);
  if (!date) return "—";

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return formatFullDateTime(iso);

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined,
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** @deprecated Use formatBatchTime — kept for existing imports */
export function formatRelativeTime(iso: string): string {
  return formatBatchTime(iso);
}
