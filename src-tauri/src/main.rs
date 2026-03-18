// main.rs — Application entry point
// Generated from tao-init v1.0.0 (tauri-rust adapter)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod errors;
mod logger;
mod paths;

use errors::AppError;

fn main() -> Result<(), AppError> {
    // 1. Load merged config (default → user → project → runtime)
    let cfg = config::load()?;

    // 2. Initialize logger (console + JSON file)
    let _guard = logger::init(&cfg.logger)?;

    // 3. Build and validate runtime paths
    let paths = paths::build(&cfg)?;

    tracing::info!(
        app    = cfg.app.name.as_str(),
        version = cfg.app.version.as_str(),
        mode   = cfg.app.mode.as_str(),
        logs   = paths.logs_dir.display().to_string().as_str(),
        "startup"
    );

    // 4. Launch Tauri
    tauri::Builder::default()
        .manage(cfg)
        .manage(paths)
        .run(tauri::generate_context!())
        .map_err(|e| AppError::Tauri(e.to_string()))
}
