export type AppTab = "studio" | "planning" | "dashboard" | "settings";

export type ApiHealthStatus = {
  api_state: "connectee" | "deconnectee";
  api_url: string;
  service?: string | null;
  version?: string | null;
  time_utc?: string | null;
  message: string;
};

export type BootstrapStatus = {
  app_version: string;
  db_path: string;
  db_exists: boolean;
  mode: string;
};

export type Workflow = {
  id: number;
  local_user: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  channels: string[];
};

export type WorkflowForm = {
  name: string;
  description: string;
  is_active: boolean;
  channels: string[];
};

export type ChannelStatus = {
  has_valid_channel: boolean;
  valid_channels: string[];
  config_url: string;
};

export type IngestionAcceptedFile = {
  path: string;
  size_bytes: number;
  encoding: string;
  preview: string;
};

export type IngestionMessage = {
  path: string;
  reason: string;
};

export type IngestionPreview = {
  accepted_files: IngestionAcceptedFile[];
  ignored_files: IngestionMessage[];
  errors: IngestionMessage[];
  summary: {
    accepted: number;
    ignored: number;
    errors: number;
    total_candidates: number;
    total_size_bytes: number;
  };
};

export type WorkflowSourcesConfig = {
  file_paths: string[];
  directory_path: string | null;
  recursive: boolean;
  max_file_size_bytes: number;
};

export type AiConfig = {
  workflow_id: number;
  provider: string;
  base_url: string;
  model: string;
  timeout_seconds: number;
};

export type VoiceCriteria = {
  workflow_id: number;
  preset: string;
  custom_instructions: string;
  min_length: number;
  max_length: number;
};

export type GenerationResult = {
  workflow_id: number;
  journal: string | null;
  post: string | null;
  provider: string;
  model: string;
  error_type: string | null;
  error_message: string | null;
  draft_id: number | null;
  draft_status?: string | null;
  require_approval?: boolean | null;
};

export type GenerationHistoryEntry = {
  timestamp: string;
  journal: string | null;
  post: string | null;
  provider: string;
  model: string;
};

export type ScheduleDto = {
  workflow_id: number;
  schedule_type: string;
  timezone: string;
  run_at: string | null;
  times: string[];
  weekdays: number[];
  monthdays: number[];
  catchup_enabled: boolean;
  require_approval: boolean;
};

export type DraftStatus =
  | "pending_approval"
  | "approved"
  | "rejected"
  | "abandoned"
  | "blocked_confidentiality";

export type DraftDto = {
  id: number;
  workflow_id: number;
  slot_iso: string | null;
  journal: string;
  post: string;
  status: DraftStatus;
  forbidden_words_matched: string[];
  created_at: string;
  updated_at: string;
};

export type DraftListResponse = {
  workflow_id: number;
  items: DraftDto[];
};
