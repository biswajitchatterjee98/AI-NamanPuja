const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

type PageInput = {
  puja: string;
  city: string;
  state: string;
  country: string;
};

export type BatchStatus =
  | "PENDING"
  | "GENERATING"
  | "QC_COMPLETE"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "UPLOADED";

export type BatchSummary = {
  id: string;
  status: BatchStatus;
  created_at: string;
  updated_at: string;
  page_count: number;
  parent_batch_id?: string | null;
};

export type PageDocument = {
  id?: string;
  batch_id: string;
  puja: string;
  city: string;
  state: string;
  country: string;
  slug: string;
  content: string;
  faq: { question: string; answer: string }[];
  seo?: { title: string; description: string; keywords: string[] } | null;
  images: { path: string; caption: string; alt: string }[];
  qc?: { passed: boolean; issues: string[] } | null;
  upload_status?: string | null;
};

export type BatchDetail = {
  batch: {
    id: string;
    status: BatchStatus;
    created_at: string;
    updated_at: string;
    page_inputs: PageInput[];
    parent_batch_id?: string | null;
  };
  pages: PageDocument[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listBatches: () => request<BatchSummary[]>("/batches"),
  getBatch: (batchId: string) => request<BatchDetail>(`/batch/${batchId}`),
  createBatch: (pages: PageInput[]) =>
    request<{ batch_id: string; status: BatchStatus; job_id: string }>("/batch/create", {
      method: "POST",
      body: JSON.stringify({ pages }),
    }),
  approveBatch: (batchId: string) =>
    request<{ batch_id: string; status: BatchStatus; upload_job_id: string }>(
      `/batch/${batchId}/approve`,
      { method: "POST" },
    ),
  rejectBatch: (batchId: string, comments: string) =>
    request<{ batch_id: string; status: BatchStatus }>(`/batch/${batchId}/reject`, {
      method: "POST",
      body: JSON.stringify({ comments }),
    }),
  regenerateBatch: (batchId: string) =>
    request<{ batch_id: string; parent_batch_id: string; job_id: string }>(
      `/batch/${batchId}/regenerate`,
      { method: "POST" },
    ),
};
