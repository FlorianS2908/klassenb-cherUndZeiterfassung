import { apiGet, apiPost } from './api';
import type { KlassenbuchOpenResponse } from '../types';

export const getOpenKlassenbuecher = () => apiGet<KlassenbuchOpenResponse>('/api/klassenbuch/open');
export const prepareKlassenbuch = (payload: unknown) => apiPost('/api/klassenbuch/prepare', payload);
export const fillClassbookAndOpenSignature = (payload: unknown, review_confirmed: boolean) => apiPost('/api/klassenbuch/fill-and-open-signature', { payload, review_confirmed });
export const prepareKlassenbuchSignature = (payload: unknown, review_confirmed: boolean) => apiPost('/api/klassenbuch/prepare-signature', { payload, review_confirmed });
export const submitKlassenbuch = (payload: unknown, review_confirmed: boolean, signature_confirmed: boolean) => apiPost('/api/klassenbuch/submit', { payload, review_confirmed, signature_confirmed });
export const getKlassenbuchCredentialStatus = () => apiGet('/api/klassenbuch/credentials/status');
export const saveKlassenbuchCredentials = (username: string, password: string) => apiPost('/api/klassenbuch/credentials/save', { username, password });
export const deleteKlassenbuchCredentials = () => apiPost('/api/klassenbuch/credentials/delete');
export const testKlassenbuchLoginDirect = (username?: string, password?: string) => apiPost('/api/klassenbuch/login-test', username && password ? { username, password } : {});
