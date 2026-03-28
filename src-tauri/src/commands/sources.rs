// commands/sources.rs — Workflow sources, ingestion preview, file pickers

use crate::commands::{
    IngestionPreviewInput, IngestionPreviewResponse, WorkflowSourcesDto, WorkflowSourcesInput,
};
use crate::http_client::{api_get, api_post, api_post_empty, api_put};

#[tauri::command]
pub fn workflow_sources_get(workflow_id: i64) -> Result<WorkflowSourcesDto, String> {
    api_get(&format!("/workflows/{workflow_id}/sources"))
}

#[tauri::command]
pub fn workflow_sources_set(
    workflow_id: i64,
    payload: WorkflowSourcesInput,
) -> Result<WorkflowSourcesDto, String> {
    api_put(&format!("/workflows/{workflow_id}/sources"), &payload)
}

#[tauri::command]
pub fn workflow_ingestion_preview(workflow_id: i64) -> Result<IngestionPreviewResponse, String> {
    api_post_empty(&format!("/workflows/{workflow_id}/ingestion/preview"))
}

#[tauri::command]
pub fn ingestion_preview(
    payload: IngestionPreviewInput,
) -> Result<IngestionPreviewResponse, String> {
    api_post("/ingestion/preview", &payload)
}

#[tauri::command]
pub fn pick_text_files() -> Result<Vec<String>, String> {
    let files = rfd::FileDialog::new()
        .add_filter("Text files", &["txt", "md"])
        .pick_files();

    let selected = files
        .unwrap_or_default()
        .into_iter()
        .map(|p| p.display().to_string())
        .collect();
    Ok(selected)
}

#[tauri::command]
pub fn pick_directory() -> Result<Option<String>, String> {
    let dir = rfd::FileDialog::new().pick_folder();
    Ok(dir.map(|p| p.display().to_string()))
}
