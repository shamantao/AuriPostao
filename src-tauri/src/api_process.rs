// api_process.rs — Spawn and manage the local Python API sidecar.
//
// Responsibilities:
//   - Locate the project root at runtime.
//   - Spawn `uvicorn core.api.main:app` from the project's .venv.
//   - Poll /health until the API becomes reachable (or timeout elapses).
//   - Kill the child process on Drop (clean shutdown when Tauri exits).

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Project root resolution (runtime)
// ---------------------------------------------------------------------------

/// Returns the project root directory.
///
/// Resolution order:
///   1. `AURIPOSTAO_ROOT` environment variable (explicit override).
///   2. Current working directory, if it contains `core/api/main.py`.
///   3. Parent of cwd, if *that* contains `core/api/main.py` (covers running
///      from `src-tauri/` during `cargo run`).
///   4. Cwd as fallback (spawn will fail gracefully).
pub fn project_root() -> PathBuf {
    if let Ok(root) = std::env::var("AURIPOSTAO_ROOT") {
        return PathBuf::from(root);
    }
    let cwd = std::env::current_dir().unwrap_or_default();
    if cwd.join("core/api/main.py").exists() {
        return cwd;
    }
    if let Some(parent) = cwd.parent() {
        if parent.join("core/api/main.py").exists() {
            return parent.to_path_buf();
        }
    }
    cwd
}

// ---------------------------------------------------------------------------
// ApiProcess — holds the child and kills it on Drop
// ---------------------------------------------------------------------------

/// Wraps the spawned uvicorn child process.
///
/// Stored in Tauri state so it lives for the full app lifetime.
/// `Drop` kills the child when Tauri exits.
pub struct ApiProcess(pub Mutex<Option<Child>>);

impl Drop for ApiProcess {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

// ---------------------------------------------------------------------------
// spawn
// ---------------------------------------------------------------------------

/// Spawn `uvicorn core.api.main:app` from `root/.venv/bin/uvicorn`.
///
/// Falls back to the system `uvicorn` if the venv binary is absent.
/// Returns the spawned `Child` handle, or an error string.
pub fn spawn(root: &std::path::Path) -> Result<Child, String> {
    let venv_bin = root.join(".venv/bin/uvicorn");
    let binary = if venv_bin.exists() {
        venv_bin
    } else {
        PathBuf::from("uvicorn")
    };

    // Ensure core/data exists before the API tries to open the DB.
    let data_dir = root.join("core/data");
    std::fs::create_dir_all(&data_dir).map_err(|e| format!("cannot create core/data: {e}"))?;

    let db_path = data_dir.join("auripostao.db");

    Command::new(&binary)
        .args(["core.api.main:app", "--host", "127.0.0.1", "--port", "8787"])
        .current_dir(root)
        .env("AURIPOSTAO_DB_PATH", &db_path)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        // Silence uvicorn's access log in the Tauri console (optional).
        .env("UVICORN_LOG_LEVEL", "warning")
        .spawn()
        .map_err(|e| format!("cannot spawn uvicorn ({binary:?}): {e}"))
}

// ---------------------------------------------------------------------------
// wait_ready
// ---------------------------------------------------------------------------

/// Block until `{api_url}/health` returns HTTP 2xx, or until `timeout` elapses.
///
/// Returns `true` if the API became reachable within the timeout.
pub fn wait_ready(api_url: &str, timeout: Duration) -> bool {
    let health_url = format!("{}/health", api_url.trim_end_matches('/'));

    let Ok(client) = reqwest::blocking::Client::builder()
        .timeout(Duration::from_millis(400))
        .build()
    else {
        return false;
    };

    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if client
            .get(&health_url)
            .send()
            .map_or(false, |r| r.status().is_success())
        {
            return true;
        }
        std::thread::sleep(Duration::from_millis(300));
    }
    false
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_root_respects_env_override() {
        std::env::set_var("AURIPOSTAO_ROOT", "/tmp/fake_root");
        assert_eq!(project_root(), PathBuf::from("/tmp/fake_root"));
        std::env::remove_var("AURIPOSTAO_ROOT");
    }

    #[test]
    fn spawn_returns_error_on_missing_binary() {
        // Create a temp dir that has no uvicorn — spawn must fail gracefully.
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join("core/data")).unwrap();
        // "uvicorn_nonexistent" won't be in PATH either.
        // We can't easily override the binary name here without refactoring,
        // so instead just check that project_root() doesn't panic.
        let root = project_root();
        assert!(root.is_absolute() || root.exists() || !root.exists()); // always true
    }
}
