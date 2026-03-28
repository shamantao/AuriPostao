// commands/drafts.rs — Draft listing, approve, reject, abandon stale

use crate::commands::{DraftDto, DraftListResponse};
use crate::http_client::api_get;
use crate::http_client::api_post_empty;

#[tauri::command]
pub fn workflow_drafts_list(workflow_id: i64) -> Result<DraftListResponse, String> {
    api_get(&format!("/workflows/{workflow_id}/drafts"))
}

#[tauri::command]
pub fn workflow_draft_approve(workflow_id: i64, draft_id: i64) -> Result<DraftDto, String> {
    api_post_empty(&format!(
        "/workflows/{workflow_id}/drafts/{draft_id}/approve"
    ))
}

#[tauri::command]
pub fn workflow_draft_reject(workflow_id: i64, draft_id: i64) -> Result<DraftDto, String> {
    api_post_empty(&format!(
        "/workflows/{workflow_id}/drafts/{draft_id}/reject"
    ))
}

#[tauri::command]
pub fn workflow_drafts_abandon_stale(workflow_id: i64) -> Result<serde_json::Value, String> {
    api_post_empty(&format!("/workflows/{workflow_id}/drafts/abandon-stale"))
}
