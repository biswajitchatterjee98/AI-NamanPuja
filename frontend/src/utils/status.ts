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

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString();
}
