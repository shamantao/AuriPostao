// main.rs — Application entry point (facade)
// All IPC handlers live in commands/; HTTP helpers in http_client.rs.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api_process;
mod commands;
mod config;
mod errors;
mod http_client;
mod logger;
mod paths;

use errors::AppError;

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
        None
    } else {
        match api_process::spawn(&root) {
            Ok(child) => {
                tracing::info!(
                    root = root.display().to_string().as_str(),
                    "api sidecar spawned"
                );
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
            commands::bootstrap::healthcheck,
            commands::bootstrap::bootstrap_status,
            commands::workflows::workflows_list,
            commands::workflows::workflows_create,
            commands::workflows::workflows_update,
            commands::workflows::workflows_delete,
            commands::channels::channels_status,
            commands::channels::channels_set_dummy,
            commands::channels::workflow_channels_get,
            commands::channels::workflow_channels_set,
            commands::sources::workflow_sources_get,
            commands::sources::workflow_sources_set,
            commands::sources::workflow_ingestion_preview,
            commands::sources::ingestion_preview,
            commands::sources::pick_text_files,
            commands::sources::pick_directory,
            commands::ai::workflow_ai_config_get,
            commands::ai::workflow_ai_config_set,
            commands::ai::workflow_voice_criteria_get,
            commands::ai::workflow_voice_criteria_set,
            commands::generation::workflow_generate,
            commands::scheduling::workflow_schedule_get,
            commands::scheduling::workflow_schedule_set,
            commands::scheduling::workflow_schedule_next_slots,
            commands::scheduling::workflow_schedule_missed_slots,
            commands::scheduling::workflow_schedule_mark_run,
            commands::confidentiality::confidentiality_forbidden_words_get,
            commands::confidentiality::confidentiality_forbidden_words_set,
            commands::confidentiality::workflow_forbidden_words_get,
            commands::confidentiality::workflow_forbidden_words_set,
            commands::drafts::workflow_drafts_list,
            commands::drafts::workflow_draft_approve,
            commands::drafts::workflow_draft_reject,
            commands::drafts::workflow_drafts_abandon_stale,
        ])
        .run(tauri::generate_context!())
        .map_err(|e| AppError::Tauri(e.to_string()))
}
