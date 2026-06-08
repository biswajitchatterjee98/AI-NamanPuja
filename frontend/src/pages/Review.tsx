import DOMPurify from "dompurify";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, BatchDetail } from "../api/client";

function renderSafeHtml(content: string) {
  return { __html: DOMPurify.sanitize(content) };
}

export default function Review() {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const [comments, setComments] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadDetail() {
    if (!batchId) return;
    setError("");
    try {
      const data = await api.getBatch(batchId);
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load batch");
    }
  }

  useEffect(() => {
    loadDetail();
    const interval = setInterval(loadDetail, 5000);
    return () => clearInterval(interval);
  }, [batchId]);

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
    return <p>Loading batch...</p>;
  }

  const canReview = detail.batch.status === "UNDER_REVIEW";
  const canRegenerate = detail.batch.status === "REJECTED" || detail.batch.status === "FAILED";

  return (
    <div>
      <p>
        <Link to="/">← Back to dashboard</Link>
      </p>
      <section className="card">
        <h2>Batch Summary</h2>
        <p>
          <strong>Status:</strong> {detail.batch.status}
        </p>
        <p>
          <strong>Pages:</strong> {detail.pages.length || detail.batch.page_count}
        </p>
        {detail.batch.parent_batch_id && (
          <p>
            <strong>Parent batch:</strong> {detail.batch.parent_batch_id}
          </p>
        )}
      </section>

      {error && <p style={{ color: "#b42318" }}>{error}</p>}

      {canReview && (
        <section className="card">
          <h3>Review Decision</h3>
          <div className="actions">
            <button className="primary" onClick={handleApprove} disabled={busy}>
              Approve Batch
            </button>
          </div>
          <form onSubmit={handleReject} style={{ marginTop: "1rem" }}>
            <label>
              Rejection feedback
              <textarea
                rows={4}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Explain what needs to change for the next generation"
                required
              />
            </label>
            <button type="submit" className="danger" disabled={busy}>
              Reject Batch
            </button>
          </form>
        </section>
      )}

      {canRegenerate && (
        <section className="card">
          <button className="primary" onClick={handleRegenerate} disabled={busy}>
            Regenerate Batch
          </button>
        </section>
      )}

      {detail.pages.map((page) => (
        <section className="card" key={page.slug}>
          <h3>{page.slug}</h3>
          <p>
            {page.puja} — {page.city}, {page.state}, {page.country}
          </p>
          {page.seo && (
            <div>
              <p>
                <strong>SEO Title:</strong> {page.seo.title}
              </p>
              <p>
                <strong>SEO Description:</strong> {page.seo.description}
              </p>
            </div>
          )}
          {page.qc && (
            <p>
              <strong>QC:</strong> {page.qc.passed ? "Passed" : "Issues"} — {page.qc.issues.join(", ")}
            </p>
          )}
          {page.images.length > 0 && (
            <div>
              <strong>Images</strong>
              <ul>
                {page.images.map((image) => (
                  <li key={image.path}>
                    {image.path} — {image.alt}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div dangerouslySetInnerHTML={renderSafeHtml(page.content)} />
          {page.faq.length > 0 && (
            <div>
              <h4>FAQ</h4>
              {page.faq.map((item) => (
                <div key={item.question}>
                  <p>
                    <strong>Q:</strong> {item.question}
                  </p>
                  <p>
                    <strong>A:</strong> {item.answer}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
