import { apiGet, apiPost } from './api';

export const getOpenKlassenbuecher = () => apiGet<{ items: any[] }>('/api/klassenbuch/open');
export const prepareKlassenbuch = (payload: unknown) => apiPost('/api/klassenbuch/prepare', payload);
export const submitKlassenbuch = (payload: unknown, review_confirmed: boolean, signature_confirmed: boolean) => apiPost('/api/klassenbuch/submit', { payload, review_confirmed, signature_confirmed });
