// commands/bootstrap.rs — healthcheck + bootstrap_status

use crate::commands::{ApiHealthStatus, BootstrapStatus};
use crate::config::AppConfig;
use crate::http_client::api_base_url;
use std::time::Duration;

#[tauri::command]
pub fn healthcheck() -> Result<ApiHealthStatus, String> {
    let api_url = api_base_url();
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

#[tauri::command]
pub fn bootstrap_status(cfg: tauri::State<AppConfig>) -> Result<BootstrapStatus, String> {
    let api_url = api_base_url();
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
