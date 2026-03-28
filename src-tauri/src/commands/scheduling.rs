// commands/scheduling.rs — Schedule CRUD + next/missed slots + mark-run

use crate::commands::{
    ScheduleDto, ScheduleInput, ScheduleMissedSlotsResponse, ScheduleNextSlotsResponse,
    ScheduleRunMarkInput,
};
use crate::http_client::{api_get, api_get_query, api_post, api_put};

#[tauri::command]
pub fn workflow_schedule_get(workflow_id: i64) -> Result<ScheduleDto, String> {
    api_get(&format!("/workflows/{workflow_id}/schedule"))
}

#[tauri::command]
pub fn workflow_schedule_set(
    workflow_id: i64,
    payload: ScheduleInput,
) -> Result<ScheduleDto, String> {
    api_put(&format!("/workflows/{workflow_id}/schedule"), &payload)
}

#[tauri::command]
pub fn workflow_schedule_next_slots(workflow_id: i64) -> Result<ScheduleNextSlotsResponse, String> {
    api_get(&format!("/workflows/{workflow_id}/schedule/next-slots"))
}

#[tauri::command]
pub fn workflow_schedule_missed_slots(
    workflow_id: i64,
    since: Option<String>,
) -> Result<ScheduleMissedSlotsResponse, String> {
    let path = format!("/workflows/{workflow_id}/schedule/missed-slots");
    match since.as_deref() {
        Some(s) if !s.is_empty() => api_get_query(&path, &[("since", s)]),
        _ => api_get(&path),
    }
}

#[tauri::command]
pub fn workflow_schedule_mark_run(
    workflow_id: i64,
    payload: ScheduleRunMarkInput,
) -> Result<serde_json::Value, String> {
    api_post(
        &format!("/workflows/{workflow_id}/schedule/mark-run"),
        &payload,
    )
}
