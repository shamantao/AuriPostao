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
use serde::Serialize;
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
    let api_url = std::env::var("AURIPOSTAO_API_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());
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

#[tauri::command]
fn bootstrap_status(cfg: tauri::State<AppConfig>) -> Result<BootstrapStatus, String> {
    let api_url = std::env::var("AURIPOSTAO_API_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());
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
        app_version: cfg.app.version.clone(),
        db_path,
        db_exists,
        mode,
    })
}

fn main() -> Result<(), AppError> {
    // 1. Load merged config (default → user → project → runtime)
    let cfg = config::load()?;

    // 2. Build and validate runtime paths (creates logs/ dir before logger init)
    let paths = paths::build(&cfg)?;

    // 3. Initialize logger (console + JSON file)
    let _guard = logger::init(&cfg.logger)?;

    // 4. Resolve the API base URL (env override or default)
    let api_url = std::env::var("AURIPOSTAO_API_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8787".to_string());

    // 5. Spawn the Python API sidecar
    let root = api_process::project_root();
    let api_child = match api_process::spawn(&root) {
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
    };
    let api_process = api_process::ApiProcess(std::sync::Mutex::new(api_child));

    tracing::info!(
        app    = cfg.app.name.as_str(),
        version = cfg.app.version.as_str(),
        mode   = cfg.app.mode.as_str(),
        logs   = paths.logs_dir.display().to_string().as_str(),
        "startup"
    );

    // 6. Launch Tauri
    tauri::Builder::default()
        .manage(cfg)
        .manage(paths)
        .manage(api_process)
        .invoke_handler(tauri::generate_handler![healthcheck, bootstrap_status])
        .run(tauri::generate_context!())
        .map_err(|e| AppError::Tauri(e.to_string()))
}
