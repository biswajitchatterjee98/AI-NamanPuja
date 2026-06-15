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
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "FAILED"
  | "CANCELLED"
  | "UPLOADED"
  | "UPLOAD_PARTIAL";

export type BatchSummary = {
  id: string;
  name: string;
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

export type GenerationProgressData = {
  phase?: string;
  message?: string;
  page_index?: number;
  page_total?: number;
  puja?: string;
  city?: string;
  slug?: string;
  image_index?: number | null;
  image_total?: number;
  content_preview?: string;
  updated_at?: string;
};

export type GenerationMetadata = {
  error?: string;
  progress?: GenerationProgressData;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  generation_job_id?: string;
  qc_results?: { slug: string; passed: boolean; issues: string[] }[];
};

export type BatchDetail = {
  batch: {
    id: string;
    status: BatchStatus;
    created_at: string;
    updated_at: string;
    page_inputs: PageInput[];
    page_count: number;
    parent_batch_id?: string | null;
    generation_metadata?: GenerationMetadata;
  };
  pages: PageDocument[];
};

export function isAuthConfigured(): boolean {
  return API_KEY.length > 0;
}

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
  cancelBatch: (batchId: string) =>
    request<{ batch_id: string; status: BatchStatus }>(`/batch/${batchId}/cancel`, {
      method: "POST",
    }),
  deleteBatch: (batchId: string) =>
    request<{ batch_id: string; deleted: boolean }>(`/batch/${batchId}`, {
      method: "DELETE",
    }),
};

async function downloadBlob(path: string, filename: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export type ExportFormat = "docx" | "pdf";

export const downloads = {
  pageDocument: (batchId: string, slug: string, format: ExportFormat) =>
    downloadBlob(
      `/batch/${batchId}/page/${slug}/download?format=${format}`,
      `${slug}.${format}`,
    ),
  batchZip: (batchId: string, format: ExportFormat) =>
    downloadBlob(
      `/batch/${batchId}/download?format=${format}`,
      `batch-${batchId.slice(-8)}-${format}.zip`,
    ),
};
