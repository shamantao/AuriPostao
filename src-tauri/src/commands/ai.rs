// commands/ai.rs — AI config + voice criteria

use crate::commands::{AiConfigDto, AiConfigInput, VoiceCriteriaDto, VoiceCriteriaInput};
use crate::http_client::{api_get, api_put};

#[tauri::command]
pub fn workflow_ai_config_get(workflow_id: i64) -> Result<AiConfigDto, String> {
    api_get(&format!("/workflows/{workflow_id}/ai-config"))
}

#[tauri::command]
pub fn workflow_ai_config_set(
    workflow_id: i64,
    payload: AiConfigInput,
) -> Result<AiConfigDto, String> {
    api_put(&format!("/workflows/{workflow_id}/ai-config"), &payload)
}

#[tauri::command]
pub fn workflow_voice_criteria_get(workflow_id: i64) -> Result<VoiceCriteriaDto, String> {
    api_get(&format!("/workflows/{workflow_id}/voice-criteria"))
}

#[tauri::command]
pub fn workflow_voice_criteria_set(
    workflow_id: i64,
    payload: VoiceCriteriaInput,
) -> Result<VoiceCriteriaDto, String> {
    api_put(
        &format!("/workflows/{workflow_id}/voice-criteria"),
        &payload,
    )
}
