from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminLogIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AdminInfoOut(BaseModel):
    id: int
    username: int
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminLoginOut(TokenOut):
    user: AdminInfoOut


class StudentLoginIn(BaseModel):
    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    school_id: int = Field(ge=1, description="ID школы из выпадающего списка")

    @field_validator("last_name", "first_name", "middle_name")
    @classmethod
    def _collapse_spaces(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("Поле не может состоять из пробелов")
        return v


class SchoolOut(BaseModel):
    id: int
    name: str
    city: str
    model_config = ConfigDict(from_attributes=True)


class StudentOut(BaseModel):
    id: int
    full_name: str
    school_name: str


class StudentLoginOut(TokenOut):
    student: StudentOut


class TaskFileOut(BaseModel):
    id: int
    original_name: str
    mime_type: str | None
    size_bytes: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StudentFieldOut(BaseModel):
    id: int
    code: str
    label: str
    input_type: Literal["string", "number"]
    sort_order: int
    model_config = ConfigDict(from_attributes=True)


class StudentTaskOut(BaseModel):
    id: int
    number: int
    title: str
    statement_text: str | None
    instruction_text: str | None
    source_data_text: str | None
    max_score: int
    scoring_type: str
    files: list[TaskFileOut] = []
    fields: list[StudentFieldOut] = []
    model_config = ConfigDict(from_attributes=True)


class StartAttemptIn(BaseModel):
    machine_id: str | None = Field(default=None, max_length=100)


class AttemptInfoOut(BaseModel):
    id: int
    status: str
    started_at: datetime
    expires_at: datetime | None
    finished_at: datetime | None
    duration_seconds: int | None
    machine_id: str | None
    model_config = ConfigDict(from_attributes=True)


class AttemptStateOut(BaseModel):
    attempt: AttemptInfoOut
    variant_title: str
    instruction_text: str
    server_time: datetime
    tasks: list[StudentTaskOut]


class AnswerItemIn(BaseModel):
    task_id: int
    field_id: int
    value: str = Field(max_length=2000)


class SaveAnswersIn(BaseModel):
    answers: list[AnswerItemIn] = Field(default_factory=list)


class EventItemIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] | None = None
    client_timestamp: datetime | None = None


class SendEventsIn(BaseModel):
    events: list[EventItemIn] = Field(default_factory=list)


class FinishAttemptIn(BaseModel):
    reason: Literal["finished", "time_expired", "aborted"] = "finished"
    answers: list[AnswerItemIn] | None = None


class StudentAnswerOut(BaseModel):
    field_id: int
    label: str
    value: str


class TaskResultOut(BaseModel):
    task_id: int
    number: int
    score: int | None
    max_score: int
    answers: list[StudentAnswerOut] = []


class ScoresOut(BaseModel):
    primary_score: int | None
    max_primary_score: int
    secondary_score: int | None
    max_secondary_score: int | None
    conversion_table_id: int | None


class AttemptResultOut(BaseModel):
    attempt: AttemptInfoOut
    scores: ScoresOut
    tasks: list[TaskResultOut] = []


class VariantCreateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class VariantPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class VariantOut(BaseModel):
    id: int
    title: str
    is_active: bool
    created_at: datetime
    archived_at: datetime | None
    tasks_count: int = 0
    attempts_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class FieldCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    input_type: Literal["string", "number"] = "string"
    sort_order: int = 0
    points: int = Field(default=1, ge=0)
    expected_answer: str = ""


class FieldPatchIn(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    input_type: Literal["string", "number"] | None = None
    sort_order: int | None = None
    points: int | None = Field(default=None, ge=0)
    expected_answer: str | None = None


class AdminFieldOut(BaseModel):
    id: int
    code: str
    label: str
    input_type: str
    sort_order: int
    points: int
    expected_answer: str
    model_config = ConfigDict(from_attributes=True)


class TaskCreateIn(BaseModel):
    number: int = Field(ge=1, le=27)
    title: str = Field(min_length=1, max_length=300)
    statement_text: str | None = None
    instruction_text: str | None = None
    source_data_text: str | None = None
    teacher_comment: str | None = None
    max_score: int = Field(default=1, ge=0, le=4)
    scoring_type: Literal["all_or_nothing", "partial_sum"] = "all_or_nothing"


class TaskPatchIn(BaseModel):
    number: int | None = Field(default=None, ge=1, le=27)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    statement_text: str | None = None
    instruction_text: str | None = None
    source_data_text: str | None = None
    teacher_comment: str | None = None
    max_score: int | None = Field(default=None, ge=0, le=4)
    scoring_type: Literal["all_or_nothing", "partial_sum"] | None = None


class AdminTaskOut(BaseModel):
    id: int
    variant_id: int
    number: int
    title: str
    statement_text: str | None
    instruction_text: str | None
    source_data_text: str | None
    teacher_comment: str | None
    max_score: int
    scoring_type: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    fields: list[AdminFieldOut] = []
    files: list[TaskFileOut] = []
    model_config = ConfigDict(from_attributes=True)


class ConversionEntryIn(BaseModel):
    primary_score: int = Field(ge=0)
    secondary_score: int = Field(ge=0, le=100)


class ConversionTableCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    year: int | None = None
    max_primary: int = Field(default=29, ge=1, le=100)
    entries: list[ConversionEntryIn] = Field(default_factory=list)


class ConversionEntryOut(BaseModel):
    id: int
    primary_score: int
    secondary_score: int
    model_config = ConfigDict(from_attributes=True)


class ConversionTableOut(BaseModel):
    id: int
    name: str
    year: int | None
    max_primary: int
    is_active: bool
    created_at: datetime
    entries: list[ConversionEntryOut] = []
    model_config = ConfigDict(from_attributes=True)


class SettingsOut(BaseModel):
    exam_duration_minutes: int
    instruction_text: str
    max_file_size_bytes: int


class SettingsPatchIn(BaseModel):
    exam_duration_minutes: int | None = Field(default=None, ge=1, le=600)
    instruction_text: str | None = None
    max_file_size_bytes: int | None = Field(default=None, ge=1)


class AttemptListItemOut(BaseModel):
    id: int
    student_full_name: str
    school_name: str
    variant_title: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: int | None
    primary_score: int | None
    secondary_score: int | None
    machine_id: str | None


class AdminAnswerOut(BaseModel):
    field_id: int
    field_label: str
    input_type: str
    student_answer: str
    expected_answer: str
    is_correct: bool | None
    score: int | None


class AdminTaskResultOut(BaseModel):
    task_id: int
    number: int
    title: str
    score: int
    max_score: int
    answers: list[AdminAnswerOut] = []


class AttemptDetailOut(BaseModel):
    attempt: AttemptInfoOut
    student: StudentOut
    variant_title: str
    conversion_table_name: str | None
    scores: ScoresOut
    tasks: list[AdminTaskResultOut] = []


class ClearResultsIn(BaseModel):
    mode: Literal["attempt", "student", "all", "filter"]
    attempt_id: int | None = None
    student_id: int | None = None
    status: str | None = None
    variant_id: int | None = None


class StatsOverviewOut(BaseModel):
    attempts_count: int
    avg_primary: float | None
    avg_secondary: float | None
    min_primary: int | None
    min_secondary: int | None
    max_primary: int | None
    max_secondary: int | None


class StatsTaskOut(BaseModel):
    task_number: int
    title: str
    max_score: int
    completion_percent: float
    avg_score: float


class StatsOut(BaseModel):
    overview: StatsOverviewOut
    tasks: list[StatsTaskOut] = []


class DashboardOut(BaseModel):
    students_count: int
    attempts_in_progress: int
    attempts_finished: int
    attempts_aborted: int
    variants_active: int
