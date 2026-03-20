// main.rs — Application entry point
// Generated from tao-init v1.0.0 (tauri-rust adapter)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api_process;
mod config;
mod errors;
mod logger;
mod paths;

use config::AppConfig;
use errors::AppError;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Serialize)]
struct ApiHealthStatus {
    api_state: String,
    api_url: String,
    service: Option<String>,
    version: Option<String>,
    time_utc: Option<String>,
    message: String,
}

#[tauri::command]
fn healthcheck() -> Result<ApiHealthStatus, String> {
    let api_url =
        std::env::var("AURIPOSTAO_API_URL").unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());
    let health_url = format!("{}/health", api_url.trim_end_matches('/'));

    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| format!("failed to build HTTP client: {e}"))?;

    let response = client.get(&health_url).send();
    match response {
        Ok(resp) if resp.status().is_success() => {
            let json: serde_json::Value = resp
                .json()
                .map_err(|e| format!("invalid /health JSON response: {e}"))?;

            let service = json
                .get("service")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            let version = json
                .get("version")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            let time_utc = json
                .get("time_utc")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());

            Ok(ApiHealthStatus {
                api_state: "connectee".to_string(),
                api_url,
                service,
                version,
                time_utc,
                message: "API locale joignable".to_string(),
            })
        }
        Ok(resp) => Ok(ApiHealthStatus {
            api_state: "deconnectee".to_string(),
            api_url,
            service: None,
            version: None,
            time_utc: None,
            message: format!("API locale joignable mais statut HTTP {}", resp.status()),
        }),
        Err(err) => Ok(ApiHealthStatus {
            api_state: "deconnectee".to_string(),
            api_url,
            service: None,
            version: None,
            time_utc: None,
            message: format!("API locale non joignable: {err}"),
        }),
    }
}

// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
struct BootstrapStatus {
    app_version: String,
    db_path: String,
    db_exists: bool,
    mode: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct WorkflowDto {
    id: i64,
    local_user: String,
    name: String,
    description: String,
    is_active: bool,
    created_at: String,
    updated_at: String,
    channels: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct WorkflowListResponse {
    items: Vec<WorkflowDto>,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowCreateInput {
    name: String,
    description: String,
    is_active: bool,
    channels: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowChannelsResponse {
    channels: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowChannelsInput {
    channels: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowSourcesDto {
    file_paths: Vec<String>,
    directory_path: Option<String>,
    recursive: bool,
    max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowSourcesInput {
    file_paths: Vec<String>,
    directory_path: Option<String>,
    recursive: bool,
    max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct IngestionPreviewInput {
    file_paths: Vec<String>,
    directory_path: Option<String>,
    recursive: bool,
    max_file_size_bytes: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct IngestionPreviewResponse {
    accepted_files: Vec<serde_json::Value>,
    ignored_files: Vec<serde_json::Value>,
    errors: Vec<serde_json::Value>,
    summary: serde_json::Value,
}

#[tauri::command]
fn pick_text_files() -> Result<Vec<String>, String> {
    let files = rfd::FileDialog::new()
        .add_filter("Text files", &["txt", "md"])
        .pick_files();

    let selected = files
        .unwrap_or_default()
        .into_iter()
        .map(|p| p.display().to_string())
        .collect();
    Ok(selected)
}

#[tauri::command]
fn pick_directory() -> Result<Option<String>, String> {
    let dir = rfd::FileDialog::new().pick_folder();
    Ok(dir.map(|p| p.display().to_string()))
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkflowUpdateInput {
    name: Option<String>,
    description: Option<String>,
    is_active: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct ChannelStatusDto {
    has_valid_channel: bool,
    valid_channels: Vec<String>,
    config_url: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ChannelDummyInput {
    enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct AiConfigDto {
    workflow_id: i64,
    provider: String,
    base_url: String,
    model: String,
    timeout_seconds: i64,
}

#[derive(Debug, Serialize, Deserialize)]
struct AiConfigInput {
    provider: String,
    base_url: String,
    model: String,
    timeout_seconds: i64,
}

#[derive(Debug, Serialize, Deserialize)]
struct VoiceCriteriaDto {
    workflow_id: i64,
    preset: String,
    custom_instructions: String,
    min_length: i64,
    max_length: i64,
}

#[derive(Debug, Serialize, Deserialize)]
struct VoiceCriteriaInput {
    preset: String,
    custom_instructions: String,
    min_length: i64,
    max_length: i64,
}

#[derive(Debug, Serialize, Deserialize)]
struct GenerationResultDto {
    workflow_id: i64,
    journal: Option<String>,
    post: Option<String>,
    provider: String,
    model: String,
    error_type: Option<String>,
    error_message: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ApiError {
    code: String,
    message: String,
}

fn api_base_url() -> String {
    std::env::var("AURIPOSTAO_API_URL").unwrap_or_else(|_| "http://127.0.0.1:8787".to_string())
}

fn build_client() -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .map_err(|e| format!("failed to build HTTP client: {e}"))
}

fn api_error_from_response(resp: reqwest::blocking::Response) -> String {
    let status = resp.status();
    let body = resp.text().unwrap_or_else(|_| "<empty body>".to_string());
    if let Ok(parsed) = serde_json::from_str::<ApiError>(&body) {
        return format!("{}: {}", parsed.code, parsed.message);
    }
    format!("HTTP {}: {}", status, body)
}

#[tauri::command]
fn bootstrap_status(cfg: tauri::State<AppConfig>) -> Result<BootstrapStatus, String> {
    let api_url =
        std::env::var("AURIPOSTAO_API_URL").unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());
    let bootstrap_url = format!("{}/bootstrap", api_url.trim_end_matches('/'));

    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| format!("failed to build HTTP client: {e}"))?;

    let (db_path, mode) = match client.get(&bootstrap_url).send() {
        Ok(resp) if resp.status().is_success() => {
            let json: serde_json::Value = resp
                .json()
                .map_err(|e| format!("invalid /bootstrap JSON: {e}"))?;
            let db = json
                .get("db_path")
                .and_then(|v| v.as_str())
                .unwrap_or("inconnu")
                .to_string();
            let m = json
                .get("mode")
                .and_then(|v| v.as_str())
                .unwrap_or("debug")
                .to_string();
            (db, m)
        }
        _ => ("API non joignable".to_string(), cfg.app.mode.clone()),
    };

    let db_exists = std::path::Path::new(&db_path).exists();

    Ok(BootstrapStatus {
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        db_path,
        db_exists,
        mode,
    })
}

#[tauri::command]
fn workflows_list() -> Result<Vec<WorkflowDto>, String> {
    let api_url = api_base_url();
    let url = format!("{}/workflows", api_url.trim_end_matches('/'));
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for list_workflows: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    let data: WorkflowListResponse = resp
        .json()
        .map_err(|e| format!("invalid /workflows JSON response: {e}"))?;
    Ok(data.items)
}

#[tauri::command]
fn workflows_create(payload: WorkflowCreateInput) -> Result<WorkflowDto, String> {
    let api_url = api_base_url();
    let url = format!("{}/workflows", api_url.trim_end_matches('/'));
    let client = build_client()?;
    let resp = client
        .post(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for create_workflow: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid create_workflow JSON response: {e}"))
}

#[tauri::command]
fn workflows_update(workflow_id: i64, payload: WorkflowUpdateInput) -> Result<WorkflowDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for update_workflow: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid update_workflow JSON response: {e}"))
}

#[tauri::command]
fn workflows_delete(workflow_id: i64) -> Result<bool, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .delete(&url)
        .send()
        .map_err(|e| format!("api unreachable for delete_workflow: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    Ok(true)
}

#[tauri::command]
fn channels_status() -> Result<ChannelStatusDto, String> {
    let api_url = api_base_url();
    let url = format!("{}/channels/status", api_url.trim_end_matches('/'));
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for channels_status: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid channels_status JSON response: {e}"))
}

#[tauri::command]
fn channels_set_dummy(payload: ChannelDummyInput) -> Result<ChannelStatusDto, String> {
    let api_url = api_base_url();
    let url = format!("{}/channels/dummy", api_url.trim_end_matches('/'));
    let client = build_client()?;
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for channels_set_dummy: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid channels_set_dummy JSON response: {e}"))
}

#[tauri::command]
fn workflow_channels_get(workflow_id: i64) -> Result<Vec<String>, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/channels",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_channels_get: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    let data: WorkflowChannelsResponse = resp
        .json()
        .map_err(|e| format!("invalid workflow_channels_get JSON response: {e}"))?;
    Ok(data.channels)
}

#[tauri::command]
fn workflow_channels_set(workflow_id: i64, channels: Vec<String>) -> Result<Vec<String>, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/channels",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let payload = WorkflowChannelsInput { channels };
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for workflow_channels_set: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    let data: WorkflowChannelsResponse = resp
        .json()
        .map_err(|e| format!("invalid workflow_channels_set JSON response: {e}"))?;
    Ok(data.channels)
}

#[tauri::command]
fn workflow_sources_get(workflow_id: i64) -> Result<WorkflowSourcesDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/sources",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_sources_get: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_sources_get JSON response: {e}"))
}

#[tauri::command]
fn workflow_sources_set(
    workflow_id: i64,
    payload: WorkflowSourcesInput,
) -> Result<WorkflowSourcesDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/sources",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for workflow_sources_set: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_sources_set JSON response: {e}"))
}

#[tauri::command]
fn workflow_ingestion_preview(workflow_id: i64) -> Result<IngestionPreviewResponse, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/ingestion/preview",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .post(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_ingestion_preview: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_ingestion_preview JSON response: {e}"))
}

#[tauri::command]
fn ingestion_preview(payload: IngestionPreviewInput) -> Result<IngestionPreviewResponse, String> {
    let api_url = api_base_url();
    let url = format!("{}/ingestion/preview", api_url.trim_end_matches('/'));
    let client = build_client()?;
    let resp = client
        .post(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for ingestion_preview: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid ingestion_preview JSON response: {e}"))
}

#[tauri::command]
fn workflow_ai_config_get(workflow_id: i64) -> Result<AiConfigDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/ai-config",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_ai_config_get: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_ai_config_get JSON response: {e}"))
}

#[tauri::command]
fn workflow_ai_config_set(workflow_id: i64, payload: AiConfigInput) -> Result<AiConfigDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/ai-config",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for workflow_ai_config_set: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_ai_config_set JSON response: {e}"))
}

#[tauri::command]
fn workflow_voice_criteria_get(workflow_id: i64) -> Result<VoiceCriteriaDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/voice-criteria",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_voice_criteria_get: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_voice_criteria_get JSON response: {e}"))
}

#[tauri::command]
fn workflow_voice_criteria_set(
    workflow_id: i64,
    payload: VoiceCriteriaInput,
) -> Result<VoiceCriteriaDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/voice-criteria",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = build_client()?;
    let resp = client
        .put(&url)
        .json(&payload)
        .send()
        .map_err(|e| format!("api unreachable for workflow_voice_criteria_set: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_voice_criteria_set JSON response: {e}"))
}

#[tauri::command]
fn workflow_generate(workflow_id: i64) -> Result<GenerationResultDto, String> {
    let api_url = api_base_url();
    let url = format!(
        "{}/workflows/{}/generate",
        api_url.trim_end_matches('/'),
        workflow_id
    );
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(120))
        .build()
        .map_err(|e| format!("failed to build HTTP client for generate: {e}"))?;
    let resp = client
        .post(&url)
        .send()
        .map_err(|e| format!("api unreachable for workflow_generate: {e}"))?;

    if !resp.status().is_success() {
        return Err(api_error_from_response(resp));
    }

    resp.json()
        .map_err(|e| format!("invalid workflow_generate JSON response: {e}"))
}

fn main() -> Result<(), AppError> {
    // 1. Load merged config (default → user → project → runtime)
    let cfg = config::load()?;

    // 2. Build and validate runtime paths (creates logs/ dir before logger init)
    let paths = paths::build(&cfg)?;

    // 3. Initialize logger (console + JSON file)
    let _guard = logger::init(&cfg.logger)?;

    // 4. Resolve the API base URL (env override or default)
    let api_url =
        std::env::var("AURIPOSTAO_API_URL").unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());

    // 5. Spawn the Python API sidecar — skip if one is already running.
    let root = api_process::project_root();
    let api_child = if api_process::wait_ready(&api_url, std::time::Duration::from_millis(500)) {
        tracing::info!("api already running on {api_url} — reusing existing instance");
        None // no child to manage; we did not spawn it
    } else {
        match api_process::spawn(&root) {
            Ok(child) => {
                tracing::info!(
                    root = root.display().to_string().as_str(),
                    "api sidecar spawned"
                );
                // Poll /health for up to 8 s so the first UI call usually succeeds.
                if api_process::wait_ready(&api_url, std::time::Duration::from_secs(8)) {
                    tracing::info!("api sidecar ready");
                } else {
                    tracing::warn!(
                        "api sidecar did not become ready within 8 s — UI will show deconnectee"
                    );
                }
                Some(child)
            }
            Err(e) => {
                tracing::warn!(
                    error = e.as_str(),
                    "api sidecar spawn failed — app will start without it"
                );
                None
            }
        }
    };
    let api_process = api_process::ApiProcess(std::sync::Mutex::new(api_child));

    tracing::info!(
        app = cfg.app.name.as_str(),
        version = env!("CARGO_PKG_VERSION"),
        mode = cfg.app.mode.as_str(),
        logs = paths.logs_dir.display().to_string().as_str(),
        "startup"
    );

    // 6. Launch Tauri
    tauri::Builder::default()
        .manage(cfg)
        .manage(paths)
        .manage(api_process)
        .invoke_handler(tauri::generate_handler![
            healthcheck,
            bootstrap_status,
            workflows_list,
            workflows_create,
            workflows_update,
            workflows_delete,
            channels_status,
            channels_set_dummy,
            workflow_channels_get,
            workflow_channels_set,
            workflow_sources_get,
            workflow_sources_set,
            workflow_ingestion_preview,
            ingestion_preview,
            workflow_ai_config_get,
            workflow_ai_config_set,
            workflow_voice_criteria_get,
            workflow_voice_criteria_set,
            workflow_generate,
            pick_text_files,
            pick_directory
        ])
        .run(tauri::generate_context!())
        .map_err(|e| AppError::Tauri(e.to_string()))
}
