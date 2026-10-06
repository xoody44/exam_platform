from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AdminLogIn(BaseModel):
    """схема входа администратора по логину и паролю"""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AdminInfoOut(BaseModel):
    """публичная информация об администраторе"""

    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    """ответ с JWT-токеном доступа"""

    access_token: str
    token_type: str = "bearer"


class AdminLoginOut(TokenOut):
    """ответ входа администратора: токен и данные пользователя"""

    user: AdminInfoOut


class StudentLoginIn(BaseModel):
    """схема входа ученика по ФИО и школе (без пароля)"""

    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    school_id: int = Field(ge=1, description="ID школы из выпадающего списка")

    @field_validator("last_name", "first_name", "middle_name", mode="before")
    @classmethod
    def _normalize_names(cls, v: str | None) -> str | None:
        """удаляет лишние пробелы и проверяет, что поле не пустое"""
        if v is None:
            return v
        if not isinstance(v, str):
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("поле не может состоять только из пробелов")
        return v


class SchoolOut(BaseModel):
    """публичная информация о школе"""

    id: int
    name: str
    city: str
    model_config = ConfigDict(from_attributes=True)


class StudentOut(BaseModel):
    """информация об ученике для клиента"""

    id: int
    full_name: str
    school_name: str


class StudentLoginOut(TokenOut):
    """ответ входа ученика: токен и данные ученика"""

    student: StudentOut


class TaskFileOut(BaseModel):
    """файл задания, доступный ученику или админу"""

    id: int
    original_name: str
    mime_type: str | None
    size_bytes: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StudentFieldOut(BaseModel):
    """поле ответа задания в клиенте ученика"""

    id: int
    code: str
    label: str
    input_type: Literal["string", "number"]
    sort_order: int
    model_config = ConfigDict(from_attributes=True)


class StudentTaskOut(BaseModel):
    """задание в том виде, в котором его видит ученик"""

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
    """запуск попытки экзамена, опционально с идентификатором машины"""

    machine_id: str | None = Field(default=None, max_length=100)


class AttemptInfoOut(BaseModel):
    """основные данные о попытке экзамена"""

    id: int
    status: str
    started_at: datetime
    expires_at: datetime | None
    finished_at: datetime | None
    duration_seconds: int | None
    machine_id: str | None
    model_config = ConfigDict(from_attributes=True)


class AttemptStateOut(BaseModel):
    """полное состояние попытки для восстановления экрана ученика"""

    attempt: AttemptInfoOut
    variant_title: str
    instruction_text: str
    server_time: datetime
    tasks: list[StudentTaskOut]


class AnswerItemIn(BaseModel):
    """один ответ ученика на поле задания"""

    task_id: int
    field_id: int
    value: str = Field(max_length=2000)

    @field_validator("value", mode="before")
    @classmethod
    def _value_to_str(cls, v: Any) -> Any:
        """разрешает пустые ответы: null приходит как пустая строка"""
        if v is None:
            return ""
        return v


class SaveAnswersIn(BaseModel):
    """пакет сохранённых ответов ученика"""

    answers: list[AnswerItemIn] = Field(default_factory=list)


class EventItemIn(BaseModel):
    """одно событие телеметрии с клиента ученика"""

    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] | None = None
    client_timestamp: datetime | None = None


class SendEventsIn(BaseModel):
    """пакет событий телеметрии"""

    events: list[EventItemIn] = Field(default_factory=list)


class FinishAttemptIn(BaseModel):
    """завершение попытки с причиной и финальными ответами"""

    reason: Literal["finished", "time_expired", "aborted"] = "finished"
    answers: list[AnswerItemIn] | None = None


class StudentAnswerOut(BaseModel):
    """ответ ученика на одно поле в результатах"""

    field_id: int
    label: str
    value: str


class TaskResultOut(BaseModel):
    """результат одного задания для ученика"""

    task_id: int
    number: int
    score: int | None
    max_score: int
    answers: list[StudentAnswerOut] = []


class ScoresOut(BaseModel):
    """первичные и тестовые баллы попытки"""

    primary_score: int | None
    max_primary_score: int
    test_score: int | None
    max_test_score: int | None
    conversion_table_id: int | None


class AttemptResultOut(BaseModel):
    """итоги попытки для экрана результатов ученика"""

    attempt: AttemptInfoOut
    scores: ScoresOut
    tasks: list[TaskResultOut] = []


class VariantCreateIn(BaseModel):
    """создание варианта, заголовок можно не указывать — сгенерируется"""

    title: str | None = Field(default=None, min_length=1, max_length=200)


class VariantPatchIn(BaseModel):
    """частичное обновление варианта"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class VariantOut(BaseModel):
    """вариант экзамена со счётчиками заданий и попыток"""

    id: int
    title: str
    is_active: bool
    created_at: datetime
    archived_at: datetime | None
    tasks_count: int = 0
    attempts_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class FieldCreateIn(BaseModel):
    """создание поля ответа внутри задания"""

    code: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    input_type: Literal["string", "number"] = "string"
    sort_order: int = 0
    points: int = Field(default=1, ge=0)
    expected_answer: str = ""


class FieldPatchIn(BaseModel):
    """частичное обновление поля ответа"""

    code: str | None = Field(default=None, min_length=1, max_length=50)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    input_type: Literal["string", "number"] | None = None
    sort_order: int | None = None
    points: int | None = Field(default=None, ge=0)
    expected_answer: str | None = None


class AdminFieldOut(BaseModel):
    """поле ответа задания в админ-панели (с ожидаемым ответом)"""

    id: int
    code: str
    label: str
    input_type: str
    sort_order: int
    points: int
    expected_answer: str
    model_config = ConfigDict(from_attributes=True)


class TaskCreateIn(BaseModel):
    """создание задания варианта"""

    number: int = Field(ge=1, le=27)
    title: str = Field(min_length=1, max_length=300)
    statement_text: str | None = None
    instruction_text: str | None = None
    source_data_text: str | None = None
    teacher_comment: str | None = None
    max_score: int = Field(default=1, ge=0, le=4)
    scoring_type: Literal["all_or_nothing", "partial_sum"] = "all_or_nothing"


class TaskPatchIn(BaseModel):
    """частичное обновление задания"""

    number: int | None = Field(default=None, ge=1, le=27)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    statement_text: str | None = None
    instruction_text: str | None = None
    source_data_text: str | None = None
    teacher_comment: str | None = None
    max_score: int | None = Field(default=None, ge=0, le=4)
    scoring_type: Literal["all_or_nothing", "partial_sum"] | None = None


class AdminTaskOut(BaseModel):
    """задание целиком в админ-панели: поля, файлы и служебные тексты"""

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
    """одна строка переводной таблицы: первичный балл -> тестовый"""

    primary_score: int = Field(ge=0)
    test_score: int = Field(ge=0, le=100)


class ConversionTableCreateIn(BaseModel):
    """создание переводной таблицы со списком строк"""

    name: str = Field(min_length=1, max_length=200)
    year: int | None = None
    max_primary: int = Field(default=29, ge=1, le=100)
    entries: list[ConversionEntryIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_entries(self) -> "ConversionTableCreateIn":
        """проверяет отсутствие дублей первичных баллов и превышение максимума"""
        primaries = [e.primary_score for e in self.entries]
        if len(primaries) != len(set(primaries)):
            raise ValueError("первичные баллы в таблице не должны повторяться")
        over = [p for p in primaries if p > self.max_primary]
        if over:
            raise ValueError(
                f"первичный балл {max(over)} превышает максимум {self.max_primary}"
            )
        return self


class ConversionEntryOut(BaseModel):
    """строка переводной таблицы в ответе API"""

    id: int
    primary_score: int
    test_score: int
    model_config = ConfigDict(from_attributes=True)


class ConversionTableOut(BaseModel):
    """переводная таблица вместе со всеми строками"""

    id: int
    name: str
    year: int | None
    max_primary: int
    is_active: bool
    created_at: datetime
    entries: list[ConversionEntryOut] = []
    model_config = ConfigDict(from_attributes=True)


class SettingsOut(BaseModel):
    """текущие настройки системы"""

    exam_duration_minutes: int
    instruction_text: str
    max_file_size_bytes: int


class SettingsPatchIn(BaseModel):
    """частичное обновление настроек системы"""

    exam_duration_minutes: int | None = Field(default=None, ge=1, le=600)
    instruction_text: str | None = None
    max_file_size_bytes: int | None = Field(default=None, ge=1)


class AttemptListItemOut(BaseModel):
    """строка списка попыток в админ-панели"""

    id: int
    student_full_name: str
    school_name: str
    variant_title: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: int | None
    primary_score: int | None
    test_score: int | None
    machine_id: str | None


class AdminAnswerOut(BaseModel):
    """ответ ученика в сравнении с ожидаемым для ручной проверки"""

    field_id: int
    field_label: str
    input_type: str
    student_answer: str
    expected_answer: str
    is_correct: bool | None
    score: int | None


class AdminTaskResultOut(BaseModel):
    """результат задания в детальном просмотре попытки админом"""

    task_id: int
    number: int
    title: str
    score: int
    max_score: int
    answers: list[AdminAnswerOut] = []


class AttemptDetailOut(BaseModel):
    """полная детальная информация о попытке для админа"""

    attempt: AttemptInfoOut
    student: StudentOut
    variant_title: str
    conversion_table_name: str | None
    scores: ScoresOut
    tasks: list[AdminTaskResultOut] = []


class ClearResultsIn(BaseModel):
    """запрос очистки результатов: режим и параметры фильтра"""

    mode: Literal["attempt", "student", "all", "filter"]
    attempt_id: int | None = None
    student_id: int | None = None
    status: str | None = None
    variant_id: int | None = None

    @model_validator(mode="after")
    def _check_required_ids(self) -> "ClearResultsIn":
        """проверяет, что для выбранного режима передан обязательный id"""
        if self.mode == "attempt" and self.attempt_id is None:
            raise ValueError("для режима attempt требуется attempt_id")
        if self.mode == "student" and self.student_id is None:
            raise ValueError("для режима student требуется student_id")
        return self


class StatsOverviewOut(BaseModel):
    """сводная статистика по попыткам"""

    attempts_count: int
    avg_primary: float | None
    avg_test: float | None
    min_primary: int | None
    min_test: int | None
    max_primary: int | None
    max_test: int | None


class StatsTaskOut(BaseModel):
    """статистика выполнения одного задания"""

    task_number: int
    title: str
    max_score: int
    completion_percent: float
    avg_score: float


class StatsOut(BaseModel):
    """ответ со всей статистикой: обзор и разбивка по заданиям"""

    overview: StatsOverviewOut
    tasks: list[StatsTaskOut] = []


class DashboardOut(BaseModel):
    """счётчики для главного экрана админ-панели"""

    students_count: int
    attempts_in_progress: int
    attempts_finished: int
    attempts_aborted: int
    variants_active: int


class VariantDetailOut(VariantOut):
    """вариант вместе со списком всех его заданий"""

    tasks: list[AdminTaskOut] = []


class ConversionTablePatchIn(BaseModel):
    """частичное обновление переводной таблицы; entries заменяет целиком"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    year: int | None = None
    max_primary: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None
    entries: list[ConversionEntryIn] | None = None

    @model_validator(mode="after")
    def _check_entries(self) -> "ConversionTablePatchIn":
        """проверяет дубли и превышение максимума в новых строках таблицы"""
        if self.entries is None:
            return self
        primaries = [e.primary_score for e in self.entries]
        if len(primaries) != len(set(primaries)):
            raise ValueError("первичные баллы в таблице не должны повторяться")
        if self.max_primary is not None:
            over = [p for p in primaries if p > self.max_primary]
            if over:
                raise ValueError(
                    f"первичный балл {max(over)} превышает максимум {self.max_primary}"
                )
        return self


class PaginatedOut(BaseModel):
    """метаданные постраничной выдачи"""

    page: int
    per_page: int
    total: int
    pages: int


class AttemptFilters(BaseModel):
    """фильтры списка попыток в админ-панели"""

    student_id: int | None = None
    school_id: int | None = None
    variant_id: int | None = None
    status: str | None = None
    min_primary: int | None = None
    max_primary: int | None = None
    min_test: int | None = None
    max_test: int | None = None
    search: str | None = None


class AttemptsListOut(BaseModel):
    """страница списка попыток с пагинацией"""

    items: list[AttemptListItemOut]
    pagination: PaginatedOut


class StudentWithAttemptsOut(BaseModel):
    """ученик со сводкой по его попыткам"""

    id: int
    full_name: str
    school_name: str
    attempts_count: int
    last_attempt_at: datetime | None
    best_primary_score: int | None


class StudentsListOut(BaseModel):
    """страница списка учеников с пагинацией"""

    items: list[StudentWithAttemptsOut]
    pagination: PaginatedOut


class ClearResultsOut(BaseModel):
    """итог очистки результатов"""

    deleted_count: int
    deleted_ids: list[int]
