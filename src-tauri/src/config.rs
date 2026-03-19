// config.rs — Configuration module
// Loads and merges TOML layers: default → user → project → runtime

use serde::Deserialize;
use std::path::PathBuf;

use crate::errors::AppError;

// ---------------------------------------------------------------------------
// Schema

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct AppConfig {
    pub app: AppSection,
    pub config: ConfigSection,
    pub path_manager: PathManagerSection,
    pub logger: LoggerSection,
    pub reporting: ReportingSection,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct AppSection {
    pub name: String,
    pub version: String,
    pub mode: String, // "debug" | "normal"
    pub language: String,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct ConfigSection {
    pub schema_version: u32,
    pub enable_layered_merge: bool,
    pub strict_mode: bool,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct PathManagerSection {
    pub allowed_roots: Vec<PathBuf>,
    pub temp_dir: PathBuf,
    pub logs_dir: PathBuf,
    pub reports_dir: PathBuf,
    pub collision_strategy: String, // "increment" | "suffix" | "short_hash"
    pub normalize_unicode: bool,
    pub trim_whitespace: bool,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct LoggerSection {
    pub level: String,
    pub console_pretty: bool,
    pub file_json: bool,
    pub rotation_enabled: bool,
    pub max_file_mb: u64,
    pub max_files: usize,
    pub include_context_ids: bool,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct ReportingSection {
    pub enabled: bool,
    pub json_report: bool,
    pub csv_report: bool,
    pub include_failed: bool,
}

// ---------------------------------------------------------------------------
// Loader

/// Merge priority: default (bundled) → user (~/.config/<app>/user.toml)
/// → project (./config/project.toml) → runtime (env vars / CLI flags).
pub fn load() -> Result<AppConfig, AppError> {
    let mut builder = config::Config::builder();

    // Layer 1: bundled default
    let default_path = bundled_default_path();
    builder = builder.add_source(config::File::from(default_path.as_path()).required(true));

    // Layer 2: user override (optional)
    if let Some(user_path) = user_config_path() {
        builder = builder.add_source(config::File::from(user_path.as_path()).required(false));
    }

    // Layer 3: project-local override (optional)
    let project_path = PathBuf::from("config/project.toml");
    builder = builder.add_source(config::File::from(project_path.as_path()).required(false));

    // Layer 4: machine-local override, git-ignored (optional)
    let local_path = PathBuf::from("config/config.toml");
    builder = builder.add_source(config::File::from(local_path.as_path()).required(false));

    // Layer 5: environment variables (APP__ prefix)
    builder = builder.add_source(config::Environment::with_prefix("APP").separator("__"));

    let cfg = builder
        .build()
        .map_err(|e| AppError::Config(e.to_string()))?
        .try_deserialize::<AppConfig>()
        .map_err(|e| AppError::Config(e.to_string()))?;

    validate(&cfg)?;
    Ok(cfg)
}

fn bundled_default_path() -> PathBuf {
    let mut p = std::env::current_exe().unwrap_or_default();
    p.pop();
    p.push("config");
    p.push("default.toml");
    if p.exists() {
        return p;
    }
    // Dev: cargo runs from src-tauri/, config/ is one level up
    let dev = PathBuf::from("../config/default.toml");
    if dev.exists() {
        return dev;
    }
    // Fallback: relative to CWD (e.g. `tauri dev` from project root)
    PathBuf::from("config/default.toml")
}

fn user_config_path() -> Option<PathBuf> {
    dirs::config_dir().map(|mut p| {
        p.push("auripostao");
        p.push("user.toml");
        p
    })
}

fn validate(cfg: &AppConfig) -> Result<(), AppError> {
    let valid_modes = ["debug", "normal"];
    if !valid_modes.contains(&cfg.app.mode.as_str()) {
        return Err(AppError::Config(format!(
            "app.mode must be 'debug' or 'normal', got '{}'",
            cfg.app.mode
        )));
    }
    // In debug mode, allowed_roots may be empty (sandbox disabled)
    if cfg.app.mode == "normal" && cfg.path_manager.allowed_roots.is_empty() {
        return Err(AppError::Config(
            "path_manager.allowed_roots must not be empty in normal mode".into(),
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_deserializes() {
        // Minimal inline TOML for unit testing
        let toml_str = r#"
[app]
name     = "TestApp"
version  = "0.1.0"
mode     = "debug"
language = "fr"

[config]
schema_version       = 1
enable_layered_merge = true
strict_mode          = false

[path_manager]
allowed_roots      = ["/tmp"]
temp_dir           = "/tmp/.tmp"
logs_dir           = "/tmp/logs"
reports_dir        = "/tmp/reports"
collision_strategy = "increment"
normalize_unicode  = false
trim_whitespace    = true

[logger]
level               = "info"
console_pretty      = true
file_json           = true
rotation_enabled    = true
max_file_mb         = 20
max_files           = 5
include_context_ids = true

[reporting]
enabled         = true
json_report     = true
csv_report      = true
include_failed  = true
"#;
        let cfg: AppConfig = toml::from_str(toml_str).expect("should parse");
        assert_eq!(cfg.app.mode, "debug");
        assert_eq!(cfg.path_manager.collision_strategy, "increment");
    }

    #[test]
    fn validate_rejects_invalid_mode() {
        let cfg: AppConfig = toml::from_str(
            r#"[app]
name                = "T"
version             = "0.1.0"
mode                = "bad"
language            = "fr"

[config]
schema_version      = 1
enable_layered_merge = true
strict_mode          = false

[path_manager]
allowed_roots      = ["/tmp"]
temp_dir           = "/tmp/.tmp"
logs_dir           = "/tmp/logs"
reports_dir        = "/tmp/reports"
collision_strategy = "increment"
normalize_unicode  = false
trim_whitespace    = true

[logger]
level               = "info"
console_pretty      = true
file_json           = true
rotation_enabled    = true
max_file_mb         = 20
max_files           = 5
include_context_ids = true

[reporting]
enabled         = true
json_report     = true
csv_report      = true
include_failed  = true"#,
        )
        .expect("should parse invalid-mode fixture");
        assert!(validate(&cfg).is_err());
    }
}
