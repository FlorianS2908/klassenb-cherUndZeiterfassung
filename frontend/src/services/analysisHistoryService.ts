import { apiGet, apiPost } from './api';

export interface AnalysisHistoryItem {
  id: string;
  saved_at?: string;
  filename?: string;
  selection?: string;
  confidence_score?: number;
  topics?: string[];
  ue_items?: unknown[];
}

export const getAnalysisHistory = () => apiGet<{ items: AnalysisHistoryItem[] }>('/api/analysis-history');
export const saveAnalysisHistory = (payload: unknown) => apiPost('/api/analysis-history/save', payload);
export const reopenAnalysisHistory = (id: string) => apiPost<AnalysisHistoryItem>('/api/analysis-history/reopen', { id });

export async function deleteAnalysisHistory(id: string) {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/api/analysis-history/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
