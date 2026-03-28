from __future__ import annotations

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    is_active: bool = True
    channels: list[str] = Field(min_length=1)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None


class WorkflowOut(BaseModel):
    id: int
    local_user: str
    name: str
    description: str
    is_active: bool
    created_at: str
    updated_at: str
    channels: list[str] = []


class WorkflowChannelsUpdate(BaseModel):
    channels: list[str] = Field(min_length=1)


class ChannelDummyUpdate(BaseModel):
    enabled: bool


class IngestionPreviewRequest(BaseModel):
    file_paths: list[str] = []
    directory_path: str | None = None
    recursive: bool = False
    max_file_size_bytes: int = Field(default=1_000_000, ge=1)


class WorkflowSourcesUpdate(BaseModel):
    file_paths: list[str] = []
    directory_path: str | None = None
    recursive: bool = False
    max_file_size_bytes: int = Field(default=1_000_000, ge=1)


class AIConfigUpdate(BaseModel):
    provider: str = Field(default="ollama", pattern="^(ollama|openai_compat)$")
    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3.2", min_length=1)
    timeout_seconds: int = Field(default=30, ge=5, le=300)


class VoiceCriteriaUpdate(BaseModel):
    preset: str = Field(default="professional_concise")
    custom_instructions: str = ""
    min_length: int = Field(default=100, ge=10, le=2000)
    max_length: int = Field(default=500, ge=50, le=5000)


class ScheduleUpdate(BaseModel):
    schedule_type: str = Field(default="none", pattern="^(none|one_shot|daily|weekly|monthly)$")
    timezone: str = "UTC"
    run_at: str | None = None
    times: list[str] = []
    weekdays: list[int] = []
    monthdays: list[int] = []
    catchup_enabled: bool = False
    require_approval: bool = False


class ScheduleRunMark(BaseModel):
    slot_iso: str
    status: str = Field(pattern="^(done|skipped|abandoned)$")


class ForbiddenWordsUpdate(BaseModel):
    words: list[str] = []


class WorkflowForbiddenWordEntry(BaseModel):
    word: str
    action: str = Field(default="add", pattern="^(add|remove)$")


class WorkflowForbiddenWordsUpdate(BaseModel):
    entries: list[WorkflowForbiddenWordEntry] = []


VOICE_PRESETS: dict[str, str] = {
    "professional_concise": "Write in a clear, professional tone. Be concise and factual.",
    "professional_detailed": "Write in a professional, thorough tone. Include context and nuance.",
    "casual": "Write in a friendly, conversational tone. Natural and warm.",
    "storytelling": "Write as an engaging narrative. Use vivid, concrete language.",
    "technical": "Write for a technical audience. Be precise and use correct terminology.",
}

TEXT_EXTENSIONS = {".txt", ".md"}
