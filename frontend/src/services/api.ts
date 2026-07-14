const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  data: unknown;

  constructor(message: string, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.data = data;
  }
}

async function readError(response: Response): Promise<ApiError> {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    const detail = data.detail ?? data;
    return new ApiError(detail.message ?? data.message ?? text, detail);
  } catch {
    return new ApiError(text || `HTTP ${response.status}`, { message: text, status: response.status });
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw await readError(response);
  return response.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit = body instanceof FormData
    ? { method: 'POST', body }
    : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) };
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw await readError(response);
  return response.json();
}
