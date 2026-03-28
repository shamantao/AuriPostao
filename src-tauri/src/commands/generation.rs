// commands/generation.rs — Workflow text generation (async, long timeout)

use crate::commands::GenerationResultDto;
use crate::http_client::api_post_async_empty;
use std::time::Duration;

#[tauri::command]
pub async fn workflow_generate(workflow_id: i64) -> Result<GenerationResultDto, String> {
    api_post_async_empty(
        &format!("/workflows/{workflow_id}/generate"),
        Duration::from_secs(600),
    )
    .await
}
