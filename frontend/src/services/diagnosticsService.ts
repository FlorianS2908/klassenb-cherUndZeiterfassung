import { apiGet } from './api';

export const getLatestKlassenbuchDiagnostics = () => apiGet<Record<string, unknown>>('/api/diagnostics/klassenbuch/latest');

export const diagnosticFileUrl = (runId: string, name: string) =>
  `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/api/diagnostics/klassenbuch/${encodeURIComponent(runId)}/file?name=${encodeURIComponent(name)}`;
