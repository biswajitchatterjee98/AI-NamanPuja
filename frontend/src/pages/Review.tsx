import DOMPurify from "dompurify";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import StatusBadge from "../components/StatusBadge";
import { api, BatchDetail, PageDocument } from "../api/client";
import { formatBatchName } from "../utils/batchNames";
import { formatRelativeTime } from "../utils/status";

function sanitizePages(pages: PageDocument[]): Record<string, string> {
  return Object.fromEntries(pages.map((page) => [page.slug, DOMPurify.sanitize(page.content)]));
}

export default function Review() {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const [comments, setComments] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!batchId) return;
    setError("");
    try {
      const data = await api.getBatch(batchId);
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load batch");
    }
  }, [batchId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (!detail) return;
    const isGenerating = detail.batch.status === "PENDING" || detail.batch.status === "GENERATING";
    if (!isGenerating) return;

    const interval = setInterval(loadDetail, 5000);
    return () => clearInterval(interval);
  }, [detail?.batch.status, loadDetail]);

  useEffect(() => {
    if (!detail?.pages.length) return;

    const slugs = new Set(detail.pages.map((page) => page.slug));
    if (!selectedSlug || !slugs.has(selectedSlug)) {
      setSelectedSlug(detail.pages[0].slug);
    }
  }, [detail?.pages, selectedSlug]);

  const sanitizedContentBySlug = useMemo(
    () => (detail ? sanitizePages(detail.pages) : {}),
    [detail?.pages],
  );

  const selectedPage = useMemo(
    () => detail?.pages.find((page) => page.slug === selectedSlug) ?? null,
    [detail?.pages, selectedSlug],
  );

  async function handleApprove() {
    if (!batchId) return;
    setBusy(true);
    setError("");
    try {
      await api.approveBatch(batchId);
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject(event: FormEvent) {
    event.preventDefault();
    if (!batchId) return;
    setBusy(true);
    setError("");
    try {
      await api.rejectBatch(batchId, comments);
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerate() {
    if (!batchId) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.regenerateBatch(batchId);
      navigate(`/batch/${result.batch_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regenerate failed");
    } finally {
      setBusy(false);
    }
  }

  if (!detail) {
    return (
      <div className="loading-block">
        <span className="spinner" />
        Loading batch…
      </div>
    );
  }

  const canReview = detail.batch.status === "UNDER_REVIEW";
  const canRegenerate = detail.batch.status === "REJECTED" || detail.batch.status === "FAILED";

  return (
    <div>
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>

      <header className="page-header">
        <h1>
          <span className="gradient-text">{formatBatchName(detail.batch.page_inputs)}</span>
        </h1>
        <p>Review every page in this batch — approve or reject the whole thing at once.</p>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Overview</h2>
            <p className="card-subtitle">Updated {formatRelativeTime(detail.batch.updated_at)}</p>
          </div>
          <StatusBadge
            status={detail.batch.status}
            pulse={detail.batch.status === "GENERATING"}
          />
        </div>

        <div className="summary-grid">
          <div className="summary-item">
            <span>Pages</span>
            <strong>{detail.pages.length || detail.batch.page_count}</strong>
          </div>
          <div className="summary-item">
            <span>Status</span>
            <strong>{detail.batch.status.replace(/_/g, " ")}</strong>
          </div>
          {detail.batch.parent_batch_id && (
            <div className="summary-item">
              <span>Regenerated from</span>
              <strong>#{detail.batch.parent_batch_id.slice(-8)}</strong>
            </div>
          )}
        </div>
      </section>

      {canReview && (
        <section className="card">
          <div className="card-header">
            <div>
              <h2>Review decision</h2>
              <p className="card-subtitle">Approve or reject the entire batch together</p>
            </div>
          </div>

          <div className="review-actions">
            <div className="approve-panel">
              <h3>Approve for publishing</h3>
              <p style={{ margin: "0 0 1rem", fontSize: "0.92rem", color: "var(--text-muted)" }}>
                All pages in this batch will be uploaded to NamanPuja.com.
              </p>
              <button className="btn btn-success" onClick={handleApprove} disabled={busy}>
                {busy ? "Shipping…" : "Approve batch"}
              </button>
            </div>

            <div className="reject-panel">
              <h3>Request changes</h3>
              <p style={{ margin: "0 0 0.75rem", fontSize: "0.92rem", color: "var(--text-muted)" }}>
                Share feedback — it will guide the next generation.
              </p>
              <form onSubmit={handleReject}>
                <label>
                  Feedback
                  <textarea
                    rows={3}
                    value={comments}
                    onChange={(e) => setComments(e.target.value)}
                    placeholder="Tone is too formal, missing samagri details, SEO title too long…"
                    required
                  />
                </label>
                <button type="submit" className="btn btn-danger" disabled={busy} style={{ marginTop: "0.5rem" }}>
                  Reject batch
                </button>
              </form>
            </div>
          </div>
        </section>
      )}

      {canRegenerate && (
        <section className="card">
          <div className="card-header">
            <div>
              <h2>Regenerate batch</h2>
              <p className="card-subtitle">Create a new batch using previous feedback</p>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleRegenerate} disabled={busy}>
            {busy ? "Starting…" : "Regenerate batch"}
          </button>
        </section>
      )}

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Generated pages</h2>
            <p className="card-subtitle">{detail.pages.length} page{detail.pages.length !== 1 ? "s" : ""} in this batch</p>
          </div>
        </div>

        {detail.pages.length === 0 ? (
          <div className="loading-block" style={{ flexDirection: "column" }}>
            {(detail.batch.status === "PENDING" || detail.batch.status === "GENERATING") && (
              <>
                <span className="spinner" />
                <p style={{ margin: "0.75rem 0 0", fontWeight: 600 }}>
                  {detail.batch.status === "PENDING"
                    ? "Queued — waiting for the background worker…"
                    : "Generating content with Groq AI…"}
                </p>
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.88rem", color: "var(--text-muted)" }}>
                  This usually takes 1–3 minutes per page. This page refreshes automatically.
                </p>
              </>
            )}
            {detail.batch.status === "FAILED" && (
              <p style={{ margin: 0, color: "var(--danger)" }}>
                Generation failed. Go back and regenerate this batch.
              </p>
            )}
            {!["PENDING", "GENERATING", "FAILED"].includes(detail.batch.status) && (
              <p style={{ margin: 0, color: "var(--text-muted)" }}>No pages generated yet.</p>
            )}
          </div>
        ) : (
          <>
            <div className="page-selector" role="tablist" aria-label="Pages in batch">
              {detail.pages.map((page) => {
                const isActive = selectedSlug === page.slug;
                return (
                  <button
                    key={page.slug}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    className={`page-selector-item${isActive ? " is-active" : ""}`}
                    onClick={() => setSelectedSlug(page.slug)}
                  >
                    <span className="page-selector-title">{page.puja}</span>
                    <span className="page-selector-location">
                      {page.city}, {page.state}
                    </span>
                  </button>
                );
              })}
            </div>

            {selectedPage && (
              <div className="page-detail" role="tabpanel">
                <p className="page-detail-slug">{selectedPage.slug}</p>

                {selectedPage.seo && (
                  <div className="seo-block">
                    <p style={{ margin: "0 0 0.35rem" }}>
                      <strong>Title:</strong> {selectedPage.seo.title}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>Description:</strong> {selectedPage.seo.description}
                    </p>
                  </div>
                )}

                {selectedPage.qc && (
                  <p className={selectedPage.qc.passed ? "qc-pass" : "qc-fail"} style={{ fontSize: "0.88rem" }}>
                    QC: {selectedPage.qc.passed ? "✓ Passed" : "✗ Issues"} —{" "}
                    {selectedPage.qc.issues.join(", ") || "none"}
                  </p>
                )}

                {selectedPage.images.length > 0 && (
                  <div style={{ margin: "0.75rem 0" }}>
                    {selectedPage.images.map((image) => (
                      <span key={image.path} className="image-chip">
                        🖼 {image.alt || image.path}
                      </span>
                    ))}
                  </div>
                )}

                <div
                  className="page-preview-content"
                  dangerouslySetInnerHTML={{ __html: sanitizedContentBySlug[selectedPage.slug] ?? "" }}
                />

                {selectedPage.faq.length > 0 && (
                  <div style={{ marginTop: "1rem" }}>
                    <h4 style={{ fontFamily: "var(--font-display)", margin: "0 0 0.75rem" }}>FAQ</h4>
                    {selectedPage.faq.map((item) => (
                      <div key={item.question} className="faq-item">
                        <strong>{item.question}</strong>
                        <p>{item.answer}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
