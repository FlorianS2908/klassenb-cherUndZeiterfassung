import { apiGet, apiPost } from './api';
import type { ApiMessage, OpenAiKeyFileCheck, SetupCheckResult, SetupDefaults, SetupPayload } from '../types';

export async function checkSetup() {
  return apiPost<ApiMessage<SetupCheckResult>>('/api/setup/check');
}

export async function getSetupDefaults() {
  return apiGet<SetupDefaults>('/api/setup/defaults');
}

export async function validateOpenAiKeyFile(path: string) {
  return apiPost<OpenAiKeyFileCheck>('/api/setup/validate-openai-key-file', { path });
}

export async function saveSetup(payload: SetupPayload) {
  return apiPost<ApiMessage>('/api/setup/save', payload);
}
