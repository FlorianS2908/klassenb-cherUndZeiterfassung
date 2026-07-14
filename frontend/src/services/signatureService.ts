import { apiGet, apiPost } from './api';

export type SignaturePoint = { x: number; y: number; t: number };
export type SignatureStroke = SignaturePoint[];

export type SignatureStatus = {
  exists: boolean;
  source: string;
  stroke_count: number;
  point_count: number;
  has_preview: boolean;
  path: string;
  format: string;
};

export const getSignatureStatus = () => apiGet<{ ok: boolean; data: SignatureStatus }>('/api/signature/status');
export const getSignaturePreview = () => apiGet<{ ok: boolean; data: { preview_png_data_url: string } }>('/api/signature/preview');
export const saveSignatureProfile = (payload: { canvas: { width: number; height: number }; strokes: SignatureStroke[]; preview_png_data_url: string }) => apiPost('/api/signature/save', payload);
export const deleteSignatureProfile = () => apiPost('/api/signature/delete', {});
