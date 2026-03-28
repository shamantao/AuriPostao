// commands/confidentiality.rs — Global + workflow forbidden words

use crate::commands::{
    ForbiddenWordsDto, ForbiddenWordsInput, WorkflowForbiddenWordsDto, WorkflowForbiddenWordsInput,
};
use crate::http_client::{api_get, api_put};

#[tauri::command]
pub fn confidentiality_forbidden_words_get() -> Result<ForbiddenWordsDto, String> {
    api_get("/confidentiality/forbidden-words")
}

#[tauri::command]
pub fn confidentiality_forbidden_words_set(
    payload: ForbiddenWordsInput,
) -> Result<ForbiddenWordsDto, String> {
    api_put("/confidentiality/forbidden-words", &payload)
}

#[tauri::command]
pub fn workflow_forbidden_words_get(workflow_id: i64) -> Result<WorkflowForbiddenWordsDto, String> {
    api_get(&format!("/workflows/{workflow_id}/forbidden-words"))
}

#[tauri::command]
pub fn workflow_forbidden_words_set(
    workflow_id: i64,
    payload: WorkflowForbiddenWordsInput,
) -> Result<WorkflowForbiddenWordsDto, String> {
    api_put(
        &format!("/workflows/{workflow_id}/forbidden-words"),
        &payload,
    )
}
