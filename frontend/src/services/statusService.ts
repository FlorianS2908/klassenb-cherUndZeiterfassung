import { apiGet } from './api';
import type { AppStatus } from '../types';

export const getStatus = () => apiGet<AppStatus>('/api/status');
