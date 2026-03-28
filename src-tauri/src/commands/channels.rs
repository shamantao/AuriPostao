// commands/channels.rs — Channel status + dummy + workflow channels

use crate::commands::{
    ChannelDummyInput, ChannelStatusDto, WorkflowChannelsInput, WorkflowChannelsResponse,
};
use crate::http_client::{api_get, api_put};

#[tauri::command]
pub fn channels_status() -> Result<ChannelStatusDto, String> {
    api_get("/channels/status")
}

#[tauri::command]
pub fn channels_set_dummy(payload: ChannelDummyInput) -> Result<ChannelStatusDto, String> {
    api_put("/channels/dummy", &payload)
}

#[tauri::command]
pub fn workflow_channels_get(workflow_id: i64) -> Result<Vec<String>, String> {
    let data: WorkflowChannelsResponse = api_get(&format!("/workflows/{workflow_id}/channels"))?;
    Ok(data.channels)
}

#[tauri::command]
pub fn workflow_channels_set(
    workflow_id: i64,
    channels: Vec<String>,
) -> Result<Vec<String>, String> {
    let payload = WorkflowChannelsInput { channels };
    let data: WorkflowChannelsResponse =
        api_put(&format!("/workflows/{workflow_id}/channels"), &payload)?;
    Ok(data.channels)
}
