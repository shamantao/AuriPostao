// errors.rs — Central error types
// All modules return these; callers never handle raw std::io::Error.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("Config error: {0}")]
    Config(String),

    #[error("Path error: {0}")]
    Path(String),

    #[error("Logger error: {0}")]
    Logger(String),

    #[error("Tauri error: {0}")]
    Tauri(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}
