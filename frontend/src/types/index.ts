export type StepState = 'waiting' | 'running' | 'success' | 'error' | 'manual_review' | 'skipped';

export interface StepStatus {
  name: string;
  label: string;
  state: StepState;
  message: string;
}

export interface AppStatus {
  run_id: string;
  target_date: string | null;
  mode: 'dry-run' | 'productive';
  auto_submit: boolean;
  blocked: boolean;
  blocked_reason: string;
  progress: number;
  steps: StepStatus[];
  last_klassenbuch_run: string;
  last_timebutler_run: string;
  next_scheduled_run: string;
}

export interface UploadedFileInfo {
  file_id: string;
  filename: string;
  file_type: string;
  total_items: number;
  unit_label: string;
  size_bytes: number;
}

export interface UeItem {
  number: number;
  content: string;
  formats: string[];
}

export interface AnalysisResult {
  file_id: string;
  topics: string[];
  confidence_score: number;
  ue_items: UeItem[];
  range: { selection: string; selected: number[]; total_items: number; is_full_range: boolean; count: number };
  text_length: number;
}

export interface TimebutlerPayload {
  target_date: string;
  project: string;
  category: string;
  start: string;
  end: string;
  pause: string;
  remark: string;
}
