// commands/workflows.rs — CRUD workflows

use crate::commands::{
    WorkflowCreateInput, WorkflowDto, WorkflowListResponse, WorkflowUpdateInput,
};
use crate::http_client::{api_delete, api_get, api_post, api_put};

#[tauri::command]
pub fn workflows_list() -> Result<Vec<WorkflowDto>, String> {
    let data: WorkflowListResponse = api_get("/workflows")?;
    Ok(data.items)
}

#[tauri::command]
pub fn workflows_create(payload: WorkflowCreateInput) -> Result<WorkflowDto, String> {
    api_post("/workflows", &payload)
}

#[tauri::command]
pub fn workflows_update(
    workflow_id: i64,
    payload: WorkflowUpdateInput,
) -> Result<WorkflowDto, String> {
    api_put(&format!("/workflows/{workflow_id}"), &payload)
}

#[tauri::command]
pub fn workflows_delete(workflow_id: i64) -> Result<bool, String> {
    api_delete(&format!("/workflows/{workflow_id}"))
}
