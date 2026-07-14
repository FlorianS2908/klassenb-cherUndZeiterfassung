import { apiGet, apiPost } from './api';
import type { ApiMessage, OpenAiKeyFileCheck, SetupCheckResult, SetupDefaults, SetupPayload } from '../types';

export async function checkSetup() {
  return apiPost<ApiMessage<SetupCheckResult>>('/api/setup/check');
}

export async function getSetupDefaults() {
  return apiGet<SetupDefaults>('/api/setup/defaults');
}

export async function validateOpenAiKeyFile(path: string) {
  const response = await apiPost<ApiMessage<OpenAiKeyFileCheck>>('/api/setup/validate-openai-key-file', { openai_api_key_file: path });
  return response.data;
}

export async function saveSetup(payload: SetupPayload) {
  return apiPost<ApiMessage>('/api/setup/save', payload);
}
