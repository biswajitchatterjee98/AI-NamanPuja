import type { BatchStatus } from "../api/client";
import { STATUS_META } from "../utils/status";

type Props = {
  status: BatchStatus | string;
  pulse?: boolean;
};

export default function StatusBadge({ status, pulse }: Props) {
  const meta = STATUS_META[status as BatchStatus] ?? { label: status, tone: "neutral" };
  return (
    <span className={`status-badge tone-${meta.tone}${pulse ? " pulse" : ""}`}>
      <span className="status-dot" />
      {meta.label}
    </span>
  );
}
