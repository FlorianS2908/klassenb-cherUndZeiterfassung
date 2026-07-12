import { apiGet } from './api';

export const getScreenshots = () => apiGet<{ items: { name: string; path: string }[] }>('/api/screenshots');
