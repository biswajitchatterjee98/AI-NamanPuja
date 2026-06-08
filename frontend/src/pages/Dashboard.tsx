import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, BatchSummary, isAuthConfigured } from "../api/client";

const emptyRow = { puja: "", city: "", state: "", country: "USA" };

function statusClass(status: string) {
  if (status === "UNDER_REVIEW") return "badge review";
  if (status === "UPLOADED") return "badge uploaded";
  if (status === "REJECTED" || status === "FAILED") return "badge rejected";
  if (status === "UPLOAD_PARTIAL") return "badge review";
  return "badge";
}

export default function Dashboard() {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [rows, setRows] = useState([{ ...emptyRow }]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

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

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const pages = rows.filter((row) => row.puja && row.city && row.state && row.country);
      if (pages.length === 0) {
        throw new Error("Add at least one complete page input");
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
      {import.meta.env.PROD && !isAuthConfigured() && (
        <section className="card" style={{ borderColor: "#b42318" }}>
          <p style={{ color: "#b42318", margin: 0 }}>
            VITE_API_KEY is not set. API requests will fail when authentication is enforced.
          </p>
        </section>
      )}
      <section className="card">
        <h2>Create Batch</h2>
        <form onSubmit={handleCreate}>
          {rows.map((row, index) => (
            <div key={index} className="grid-2" style={{ marginBottom: "0.75rem" }}>
              <label>
                Puja
                <input value={row.puja} onChange={(e) => updateRow(index, "puja", e.target.value)} required />
              </label>
              <label>
                City
                <input value={row.city} onChange={(e) => updateRow(index, "city", e.target.value)} required />
              </label>
              <label>
                State
                <input value={row.state} onChange={(e) => updateRow(index, "state", e.target.value)} required />
              </label>
              <label>
                Country
                <input
                  value={row.country}
                  onChange={(e) => updateRow(index, "country", e.target.value)}
                  required
                />
              </label>
            </div>
          ))}
          <div className="actions">
            <button type="button" className="ghost" onClick={() => setRows((current) => [...current, { ...emptyRow }])}>
              Add Page
            </button>
            <button type="submit" className="primary" disabled={submitting}>
              {submitting ? "Creating..." : "Create Batch"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Existing Batches</h2>
        {error && <p style={{ color: "#b42318" }}>{error}</p>}
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Pages</th>
                <th>Updated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr key={batch.id}>
                  <td>{batch.id.slice(-8)}</td>
                  <td>
                    <span className={statusClass(batch.status)}>{batch.status}</span>
                  </td>
                  <td>{batch.page_count}</td>
                  <td>{new Date(batch.updated_at).toLocaleString()}</td>
                  <td>
                    <Link to={`/batch/${batch.id}`}>Review</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
