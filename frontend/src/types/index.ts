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
  ai_used: boolean;
  ai_model: string;
  ai_warnings: string[];
  ai_truncated: boolean;
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

export interface KlassenbuchEntry {
  id: string;
  tab?: string;
  raum?: string;
  nummer?: string;
  titel?: string;
  beginn?: string;
  ende?: string;
  einsatzzeit_von?: string;
  einsatzzeit_bis?: string;
  status?: string;
  datum?: string;
  editable?: boolean;
  edit_href?: string;
  row_index?: string;
  raw?: string;
  title?: string;
  date?: string;
  number?: string;
}

export interface KlassenbuchDiagnostics {
  run_id?: string;
  diagnostics_folder?: string;
  summary_path?: string;
  step?: string;
  current_url?: string;
  page_title?: string;
  tabs_found?: string[];
  tab_names_found?: string[];
  tab_errors?: Array<Record<string, string>>;
  table_count?: number;
  row_count?: number;
  tables_found?: number;
  rows_found?: number;
  tbody_row_count?: number;
  screenshots?: string[];
  html_snapshots?: string[];
  screenshot_path?: string;
  html_snapshot_path?: string;
  trace_path?: string;
  trace_file?: string;
  console_log?: string;
  network_log?: string;
  exception_type?: string;
  entries_returned?: number;
  error_message?: string;
  success?: boolean;
}

export interface KlassenbuchOpenResponse {
  ok?: boolean;
  items: KlassenbuchEntry[];
  groups?: Record<string, KlassenbuchEntry[]>;
  diagnostics?: KlassenbuchDiagnostics;
  count: number;
}

export interface SetupDefaults {
  klassenbuch_url: string;
  timebutler_url: string;
  klassenbuch_username: string;
  timebutler_username: string;
  use_separate_timebutler_credentials: boolean;
  openai_api_key_file: string;
  openai_model: string;
  openai_max_input_chars: number;
  openai_timeout_seconds: number;
  openai_retry_count: number;
  openai_temperature: number;
  auto_submit: boolean;
  default_signature: string;
  upload_folder: string;
  screenshot_folder: string;
  log_folder: string;
  error_report_folder: string;
  analysis_history_folder: string;
  reference_screenshot_dir: string;
  timebutler_project: string;
  timebutler_category: string;
  timebutler_start: string;
  timebutler_end: string;
  timebutler_pause: string;
  timebutler_remark: string;
  federal_state: string;
  blocked_dates: string;
  vacation_dates: string;
  sick_dates: string;
  desktop_notifications: boolean;
  auto_open_browser: boolean;
  auto_dry_run_on_start: boolean;
  github_remote_url: string;
  git_default_branch: string;
}

export interface SetupPayload extends SetupDefaults {
  klassenbuch_password: string;
  timebutler_password: string;
  openai_api_key: string;
}

export interface SetupCheckResult {
  env_exists: boolean;
  setup_required: boolean;
  missing: string[];
  messages: string[];
  config_public: Record<string, unknown>;
}

export interface ApiMessage<T = Record<string, unknown>> {
  ok: boolean;
  message: string;
  data: T;
}

export interface OpenAiKeyFileCheck {
  exists: boolean;
  readable: boolean;
  non_empty: boolean;
  message: string;
}
