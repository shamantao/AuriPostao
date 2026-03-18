// logger.rs — Structured logging module
// Dual output: human-readable console + JSON log files with rotation.

use std::path::Path;
use tracing_appender::non_blocking::WorkerGuard;

use crate::config::LoggerSection;
use crate::errors::AppError;

/// Initialize the global tracing subscriber.
/// Returns the WorkerGuard — caller must keep it alive for the app lifetime.
pub fn init(cfg: &LoggerSection) -> Result<WorkerGuard, AppError> {
    let level_filter = cfg.level
        .parse::<tracing::Level>()
        .map_err(|_| AppError::Logger(format!("invalid log level: {}", cfg.level)))?;

    // Build JSON file appender with rotation by file count
    let file_appender = tracing_appender::rolling::Builder::new()
        .max_log_files(cfg.max_files)
        .filename_prefix("app")
        .filename_suffix("log")
        .build("logs")
        .map_err(|e| AppError::Logger(e.to_string()))?;

    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    let subscriber = tracing_subscriber::fmt()
        .with_max_level(level_filter)
        .with_writer(non_blocking)
        .json()
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .map_err(|e| AppError::Logger(e.to_string()))?;

    Ok(guard)
}

/// Create a span for a single job, attaching job_id and correlation_id.
/// Use inside an async task or conversion function:
/// ```rust
/// let _span = logger::job_span("encode-42", "corr-xyz").entered();
/// tracing::info!("starting encode");
/// ```
pub fn job_span(job_id: &str, correlation_id: &str) -> tracing::Span {
    tracing::info_span!("job", job_id, correlation_id)
}
