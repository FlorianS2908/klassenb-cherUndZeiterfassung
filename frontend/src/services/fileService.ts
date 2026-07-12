import { apiGet, apiPost } from './api';
import type { AnalysisResult } from '../types';

export async function uploadFile(file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiPost<{ ok: boolean; message: string; data: any }>('/api/files/upload', form);
}

export async function previewRange(fileId: string, filename: string, selection: string) {
  const form = new FormData();
  form.append('file_id', fileId);
  form.append('filename', filename);
  form.append('selection', selection);
  return apiPost<any>('/api/files/preview-range', form);
}

export async function analyzeFile(fileId: string, filename: string, selection: string) {
  const form = new FormData();
  form.append('file_id', fileId);
  form.append('filename', filename);
  form.append('selection', selection);
  return apiPost<AnalysisResult>('/api/files/analyze', form);
}

export async function getOpenAiStatus() {
  return apiGet<{ active: boolean; key_present: boolean; source: string; message: string; display_path: string; model: string; max_input_chars: number }>('/api/files/openai-status');
}
