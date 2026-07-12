import { apiGet, apiPost } from './api';
import type { TimebutlerPayload } from '../types';

export const getTimebutlerDefaults = () => apiGet<TimebutlerPayload>('/api/timebutler/defaults');
export const prepareTimebutler = (payload: TimebutlerPayload) => apiPost('/api/timebutler/prepare', payload);
export const submitTimebutler = (payload: TimebutlerPayload, review_confirmed: boolean) => apiPost('/api/timebutler/submit', { payload, review_confirmed });
