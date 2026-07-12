import { apiPost } from './api';

export const confirmReview = (data: unknown) => apiPost('/api/review/confirm', data);
