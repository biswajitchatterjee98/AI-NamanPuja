import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, BatchSummary, isAuthConfigured } from "../api/client";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { formatRelativeTime } from "../utils/status";

const emptyRow = { puja: "", city: "", state: "", country: "USA" };

export default function Dashboard() {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [rows, setRows] = useState([{ ...emptyRow }]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const stats = useMemo(() => {
    const inReview = batches.filter((b) => b.status === "UNDER_REVIEW").length;
    const live = batches.filter((b) => b.status === "UPLOADED").length;
    const cooking = batches.filter((b) => b.status === "GENERATING" || b.status === "PENDING").length;
    return { total: batches.length, inReview, live, cooking };
  }, [batches]);

  async function loadBatches() {
    setLoading(true);
    setError("");
    try {
      const data = await api.listBatches();
      setBatches(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load batches");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBatches();
    const interval = setInterval(loadBatches, 5000);
    return () => clearInterval(interval);
  }, []);

  function updateRow(index: number, field: keyof typeof emptyRow, value: string) {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  }

  function removeRow(index: number) {
    if (rows.length === 1) return;
    setRows((current) => current.filter((_, i) => i !== index));
  }

  const [actionBatchId, setActionBatchId] = useState<string | null>(null);

  async function handleStop(batchId: string) {
    setActionBatchId(batchId);
    setError("");
    try {
      await api.cancelBatch(batchId);
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop batch");
    } finally {
      setActionBatchId(null);
    }
  }

  async function handleDelete(batchId: string) {
    if (!window.confirm("Delete this batch permanently? This cannot be undone.")) {
      return;
    }
    setActionBatchId(batchId);
    setError("");
    try {
      await api.deleteBatch(batchId);
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete batch");
    } finally {
      setActionBatchId(null);
    }
  }

  function canStop(status: BatchSummary["status"]) {
    return status === "PENDING" || status === "GENERATING";
  }

  function canDelete(status: BatchSummary["status"]) {
    return !canStop(status);
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const pages = rows.filter((row) => row.puja && row.city && row.state && row.country);
      if (pages.length === 0) {
        throw new Error("Add at least one complete page — puja + location required");
      }
      await api.createBatch(pages);
      setRows([{ ...emptyRow }]);
      await loadBatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create batch");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>
          Puja <span className="gradient-text">Content Studio</span>
        </h1>
        <p>Create location-specific seva pages, review with care, and publish to NamanPuja.com</p>
      </header>

      {import.meta.env.PROD && !isAuthConfigured() && (
        <div className="alert alert-warn">
          API key missing — set <code>VITE_API_KEY</code> at build time when auth is on.
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stats-row">
        <div className="stat-card accent">
          <span className="stat-value">{stats.total}</span>
          <span className="stat-label">Total batches</span>
        </div>
        <div className="stat-card warn">
          <span className="stat-value">{stats.inReview}</span>
          <span className="stat-label">Needs review</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.cooking}</span>
          <span className="stat-label">Generating</span>
        </div>
        <div className="stat-card ok">
          <span className="stat-value">{stats.live}</span>
          <span className="stat-label">Live on site</span>
        </div>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Create a batch</h2>
            <p className="card-subtitle">One page = one puja + one city. Stack as many as you need.</p>
          </div>
        </div>

        <form onSubmit={handleCreate}>
          {rows.map((row, index) => (
            <div key={index} className="form-row-card">
              <div className="form-row-label">
                Page {index + 1}
                {rows.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ float: "right", marginTop: "-4px" }}
                    onClick={() => removeRow(index)}
                  >
                    Remove
                  </button>
                )}
              </div>
              <div className="form-grid">
                <label>
                  Puja name
                  <input
                    value={row.puja}
                    onChange={(e) => updateRow(index, "puja", e.target.value)}
                    placeholder="e.g. Satyanarayan Puja"
                    required
                  />
                </label>
                <label>
                  City
                  <input
                    value={row.city}
                    onChange={(e) => updateRow(index, "city", e.target.value)}
                    placeholder="e.g. Los Angeles"
                    required
                  />
                </label>
                <label>
                  State
                  <input
                    value={row.state}
                    onChange={(e) => updateRow(index, "state", e.target.value)}
                    placeholder="e.g. California"
                    required
                  />
                </label>
                <label>
                  Country
                  <input
                    value={row.country}
                    onChange={(e) => updateRow(index, "country", e.target.value)}
                    placeholder="e.g. USA"
                    required
                  />
                </label>
              </div>
            </div>
          ))}

          <div className="actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setRows((current) => [...current, { ...emptyRow }])}
            >
              + Add another page
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Generating…" : "Generate batch"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Your batches</h2>
            <p className="card-subtitle">Auto-refreshes every 5s — no need to spam refresh</p>
          </div>
        </div>

        {loading && batches.length === 0 ? (
          <div className="loading-block">
            <span className="spinner" />
            Loading batches…
          </div>
        ) : batches.length === 0 ? (
          <EmptyState
            emoji="🪔"
            title="No batches yet"
            description="Create your first batch above to generate puja pages for your chosen locations."
          />
        ) : (
          <div className="batch-list">
            {batches.map((batch) => (
              <div key={batch.id} className="batch-row">
                <div>
                  <div className="batch-name">{batch.name}</div>
                  <div className="batch-meta">
                    {batch.page_count} page{batch.page_count !== 1 ? "s" : ""} · #{batch.id.slice(-8)}
                  </div>
                </div>
                <StatusBadge
                  status={batch.status}
                  pulse={batch.status === "GENERATING" || batch.status === "PENDING"}
                />
                <div className="batch-time">{formatRelativeTime(batch.updated_at)}</div>
                <div className="batch-actions">
                  {canStop(batch.status) && (
                    <button
                      type="button"
                      className="btn btn-stop btn-sm"
                      disabled={actionBatchId === batch.id}
                      onClick={() => handleStop(batch.id)}
                    >
                      {actionBatchId === batch.id ? "Stopping…" : "Stop"}
                    </button>
                  )}
                  <Link to={`/batch/${batch.id}`} className="btn btn-secondary btn-sm">
                    {batch.status === "UNDER_REVIEW" ? "Review →" : "Open →"}
                  </Link>
                  {canDelete(batch.status) && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm btn-icon-delete"
                      disabled={actionBatchId === batch.id}
                      onClick={() => handleDelete(batch.id)}
                      title="Delete batch"
                      aria-label="Delete batch"
                    >
                      {actionBatchId === batch.id ? "…" : "🗑"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
