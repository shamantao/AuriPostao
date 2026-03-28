// commands/mod.rs — All Tauri IPC command modules + shared DTOs.

pub mod ai;
pub mod bootstrap;
pub mod channels;
pub mod confidentiality;
pub mod drafts;
pub mod generation;
pub mod scheduling;
pub mod sources;
pub mod workflows;

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct ApiHealthStatus {
    pub api_state: String,
    pub api_url: String,
    pub service: Option<String>,
    pub version: Option<String>,
    pub time_utc: Option<String>,
    pub message: String,
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct BootstrapStatus {
    pub app_version: String,
    pub db_path: String,
    pub db_exists: bool,
    pub mode: String,
}

// ---------------------------------------------------------------------------
// Workflows
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WorkflowDto {
    pub id: i64,
    pub local_user: String,
    pub name: String,
    pub description: String,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
    pub channels: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct WorkflowListResponse {
    pub items: Vec<WorkflowDto>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowCreateInput {
    pub name: String,
    pub description: String,
    pub is_active: bool,
    pub channels: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowUpdateInput {
    pub name: Option<String>,
    pub description: Option<String>,
    pub is_active: Option<bool>,
}

// ---------------------------------------------------------------------------
// Channels
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChannelStatusDto {
    pub has_valid_channel: bool,
    pub valid_channels: Vec<String>,
    pub config_url: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChannelDummyInput {
    pub enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowChannelsResponse {
    pub channels: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowChannelsInput {
    pub channels: Vec<String>,
}

// ---------------------------------------------------------------------------
// Sources / Ingestion
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowSourcesDto {
    pub file_paths: Vec<String>,
    pub directory_path: Option<String>,
    pub recursive: bool,
    pub max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowSourcesInput {
    pub file_paths: Vec<String>,
    pub directory_path: Option<String>,
    pub recursive: bool,
    pub max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IngestionPreviewInput {
    pub file_paths: Vec<String>,
    pub directory_path: Option<String>,
    pub recursive: bool,
    pub max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IngestionPreviewResponse {
    pub accepted_files: Vec<serde_json::Value>,
    pub ignored_files: Vec<serde_json::Value>,
    pub errors: Vec<serde_json::Value>,
    pub summary: serde_json::Value,
}

// ---------------------------------------------------------------------------
// AI Config / Voice
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct AiConfigDto {
    pub workflow_id: i64,
    pub provider: String,
    pub base_url: String,
    pub model: String,
    pub timeout_seconds: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AiConfigInput {
    pub provider: String,
    pub base_url: String,
    pub model: String,
    pub timeout_seconds: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VoiceCriteriaDto {
    pub workflow_id: i64,
    pub preset: String,
    pub custom_instructions: String,
    pub min_length: i64,
    pub max_length: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VoiceCriteriaInput {
    pub preset: String,
    pub custom_instructions: String,
    pub min_length: i64,
    pub max_length: i64,
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerationResultDto {
    pub workflow_id: i64,
    pub journal: Option<String>,
    pub post: Option<String>,
    pub provider: String,
    pub model: String,
    pub error_type: Option<String>,
    pub error_message: Option<String>,
    #[serde(default)]
    pub draft_id: Option<i64>,
    #[serde(default)]
    pub draft_status: Option<String>,
    #[serde(default)]
    pub require_approval: Option<bool>,
}

// ---------------------------------------------------------------------------
// Scheduling
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleDto {
    pub workflow_id: i64,
    pub schedule_type: String,
    pub timezone: String,
    pub run_at: Option<String>,
    pub times: Vec<String>,
    pub weekdays: Vec<i64>,
    pub monthdays: Vec<i64>,
    pub catchup_enabled: bool,
    pub require_approval: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleInput {
    pub schedule_type: String,
    pub timezone: String,
    pub run_at: Option<String>,
    pub times: Vec<String>,
    pub weekdays: Vec<i64>,
    pub monthdays: Vec<i64>,
    pub catchup_enabled: bool,
    pub require_approval: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleRunMarkInput {
    pub slot_iso: String,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleNextSlotsResponse {
    pub workflow_id: i64,
    pub next_slots: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleMissedSlotsResponse {
    pub workflow_id: i64,
    pub missed_slots: Vec<String>,
}

// ---------------------------------------------------------------------------
// Confidentiality
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct ForbiddenWordsDto {
    pub words: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ForbiddenWordsInput {
    pub words: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WorkflowForbiddenWordEntry {
    pub word: String,
    pub action: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowForbiddenWordsDto {
    pub workflow_id: i64,
    pub entries: Vec<WorkflowForbiddenWordEntry>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowForbiddenWordsInput {
    pub entries: Vec<WorkflowForbiddenWordEntry>,
}

// ---------------------------------------------------------------------------
// Drafts
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct DraftDto {
    pub id: i64,
    pub workflow_id: i64,
    pub slot_iso: Option<String>,
    pub journal: String,
    pub post: String,
    pub status: String,
    pub forbidden_words_matched: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DraftListResponse {
    pub workflow_id: i64,
    pub items: Vec<DraftDto>,
}
