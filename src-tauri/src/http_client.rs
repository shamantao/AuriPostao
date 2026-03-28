// http_client.rs — Shared HTTP helpers for Tauri ↔ Python-API calls.
//
// Provides `api_get` / `api_post` / `api_put` / `api_delete` generic helpers
// so every command module avoids duplicating client-build + error-handling logic.

use serde::de::DeserializeOwned;
use serde::Serialize;
use std::time::Duration;

/// Default JSON-API timeout (seconds).
const DEFAULT_TIMEOUT_SECS: u64 = 3;

/// Base URL for the Python API (env override or localhost:8787).
pub fn api_base_url() -> String {
    std::env::var("AURIPOSTAO_API_URL").unwrap_or_else(|_| "http://127.0.0.1:8787".to_string())
}

fn build_client(timeout: Duration) -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .timeout(timeout)
        .build()
        .map_err(|e| format!("failed to build HTTP client: {e}"))
}

fn default_client() -> Result<reqwest::blocking::Client, String> {
    build_client(Duration::from_secs(DEFAULT_TIMEOUT_SECS))
}

#[derive(serde::Deserialize)]
struct ApiError {
    code: String,
    message: String,
}

fn error_from_response(resp: reqwest::blocking::Response) -> String {
    let status = resp.status();
    let body = resp.text().unwrap_or_else(|_| "<empty body>".to_string());
    if let Ok(parsed) = serde_json::from_str::<ApiError>(&body) {
        return format!("{}: {}", parsed.code, parsed.message);
    }
    format!("HTTP {}: {}", status, body)
}

/// GET `{api}/path` and deserialize the JSON response into `T`.
pub fn api_get<T: DeserializeOwned>(path: &str) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .get(&url)
        .send()
        .map_err(|e| format!("api unreachable (GET {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    resp.json()
        .map_err(|e| format!("invalid JSON (GET {path}): {e}"))
}

/// GET with optional query parameters.
pub fn api_get_query<T: DeserializeOwned>(path: &str, query: &[(&str, &str)]) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .get(&url)
        .query(query)
        .send()
        .map_err(|e| format!("api unreachable (GET {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    resp.json()
        .map_err(|e| format!("invalid JSON (GET {path}): {e}"))
}

/// POST `{api}/path` with a JSON body and deserialize the response into `T`.
pub fn api_post<T: DeserializeOwned, B: Serialize>(path: &str, body: &B) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .post(&url)
        .json(body)
        .send()
        .map_err(|e| format!("api unreachable (POST {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    resp.json()
        .map_err(|e| format!("invalid JSON (POST {path}): {e}"))
}

/// POST without a body (trigger endpoints).
pub fn api_post_empty<T: DeserializeOwned>(path: &str) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .post(&url)
        .send()
        .map_err(|e| format!("api unreachable (POST {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    resp.json()
        .map_err(|e| format!("invalid JSON (POST {path}): {e}"))
}

/// PUT `{api}/path` with a JSON body and deserialize the response into `T`.
pub fn api_put<T: DeserializeOwned, B: Serialize>(path: &str, body: &B) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .put(&url)
        .json(body)
        .send()
        .map_err(|e| format!("api unreachable (PUT {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    resp.json()
        .map_err(|e| format!("invalid JSON (PUT {path}): {e}"))
}

/// DELETE `{api}/path`.  Returns `true` on success.
pub fn api_delete(path: &str) -> Result<bool, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = default_client()?;
    let resp = client
        .delete(&url)
        .send()
        .map_err(|e| format!("api unreachable (DELETE {path}): {e}"))?;
    if !resp.status().is_success() {
        return Err(error_from_response(resp));
    }
    Ok(true)
}

/// Async POST with a custom timeout (used by `workflow_generate`).
pub async fn api_post_async_empty<T: DeserializeOwned>(
    path: &str,
    timeout: Duration,
) -> Result<T, String> {
    let url = format!("{}{}", api_base_url().trim_end_matches('/'), path);
    let client = reqwest::Client::builder()
        .timeout(timeout)
        .build()
        .map_err(|e| format!("failed to build async HTTP client: {e}"))?;
    let resp = client
        .post(&url)
        .send()
        .await
        .map_err(|e| format!("api unreachable (POST {path}): {e}"))?;
    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        if let Ok(parsed) = serde_json::from_str::<ApiError>(&body) {
            return Err(format!("{}: {}", parsed.code, parsed.message));
        }
        return Err(format!("HTTP {}: {}", status, body));
    }
    resp.json::<T>()
        .await
        .map_err(|e| format!("invalid JSON (POST {path}): {e}"))
}
