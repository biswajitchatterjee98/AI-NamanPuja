import type { GenerationProgressData } from "../api/client";

const PHASE_LABELS: Record<string, string> = {
  content: "Writing content",
  images: "Generating images",
  humanize: "Polishing tone",
  qc: "Quality check",
};

type Props = {
  progress: GenerationProgressData | null | undefined;
  status: string;
};

export default function GenerationProgress({ progress, status }: Props) {
  const isActive = status === "PENDING" || status === "GENERATING";

  if (!isActive) {
    return null;
  }

  const phase = progress?.phase ?? (status === "PENDING" ? "queued" : "content");
  const phaseLabel = PHASE_LABELS[phase] ?? "Working";
  const message =
    progress?.message ??
    (status === "PENDING" ? "Queued — waiting for the background worker…" : "Starting generation…");

  const pageTotal = progress?.page_total ?? 1;
  const pageIndex = (progress?.page_index ?? 0) + 1;
  const imageTotal = progress?.image_total ?? 3;
  const imageIndex = progress?.image_index != null ? progress.image_index + 1 : null;

  return (
    <div className="generation-progress">
      <div className="generation-progress-header">
        <span className="spinner" aria-hidden="true" />
        <div>
          <p className="generation-progress-phase">{phaseLabel}</p>
          <p className="generation-progress-message">{message}</p>
        </div>
      </div>

      <div className="generation-progress-meta">
        {progress?.puja && (
          <span>
            Page {pageIndex} of {pageTotal}: {progress.puja}
            {progress.city ? ` · ${progress.city}` : ""}
          </span>
        )}
        {phase === "images" && imageIndex != null && (
          <span className="generation-progress-images">
            <span className="spinner spinner-sm" aria-hidden="true" />
            Image {imageIndex} of {imageTotal}
          </span>
        )}
      </div>

      {progress?.content_preview && phase === "content" && (
        <div className="generation-preview">
          <p className="generation-preview-label">Latest draft</p>
          <p className="generation-preview-text">{progress.content_preview}…</p>
        </div>
      )}
    </div>
  );
}
