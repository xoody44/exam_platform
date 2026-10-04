export interface Paginated {
  page: number
  per_page: number
  total: number
  pages: number
}

export interface AdminInfo {
  id: number
  username: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: AdminInfo
}

export interface Dashboard {
  students_count: number
  attempts_in_progress: number
  attempts_finished: number
  attempts_aborted: number
  variants_active: number
}

export type AttemptStatus = 'in_progress' | 'finished' | 'time_expired' | 'aborted'

export interface AttemptListItem {
  id: number
  student_full_name: string
  school_name: string
  variant_title: string
  status: AttemptStatus
  started_at: string
  finished_at: string | null
  duration_seconds: number | null
  primary_score: number | null
  test_score: number | null
  machine_id: string | null
}

export interface AttemptsList {
  items: AttemptListItem[]
  pagination: Paginated
}

export interface AttemptInfo {
  id: number
  status: AttemptStatus
  started_at: string
  expires_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  machine_id: string | null
}

export interface Scores {
  primary_score: number | null
  max_primary_score: number
  test_score: number | null
  max_test_score: number | null
  conversion_table_id: number | null
}

export interface StudentAnswerView {
  field_id: number
  field_label: string
  input_type: string
  student_answer: string
  expected_answer: string
  is_correct: boolean | null
  score: number | null
}

export interface AdminTaskResult {
  task_id: number
  number: number
  title: string
  score: number
  max_score: number
  answers: StudentAnswerView[]
}

export interface AttemptDetail {
  attempt: AttemptInfo
  student: { id: number; full_name: string; school_name: string }
  variant_title: string
  conversion_table_name: string | null
  scores: Scores
  tasks: AdminTaskResult[]
}

export interface Variant {
  id: number
  title: string
  is_active: boolean
  created_at: string
  archived_at: string | null
  tasks_count: number
  attempts_count: number
}

export interface School {
  id: number
  name: string
  city: string
}

export interface StudentWithAttempts {
  id: number
  full_name: string
  school_name: string
  attempts_count: number
  last_attempt_at: string | null
  best_primary_score: number | null
}

export interface StudentsList {
  items: StudentWithAttempts[]
  pagination: Paginated
}

export interface StatsOverview {
  attempts_count: number
  avg_primary: number | null
  avg_test: number | null
  min_primary: number | null
  min_test: number | null
  max_primary: number | null
  max_test: number | null
}

export interface StatsTask {
  task_number: number
  title: string
  max_score: number
  completion_percent: number
  avg_score: number
}

export interface Stats {
  overview: StatsOverview
  tasks: StatsTask[]
}

export interface Settings {
  exam_duration_minutes: number
  instruction_text: string
  max_file_size_bytes: number
}

export interface ConversionTable {
  id: number
  name: string
  year: number | null
  max_primary: number
  is_active: boolean
  created_at: string
  entries: Array<{ id: number; primary_score: number; test_score: number }>
}

export interface VariantDetail extends Variant {
  tasks: AdminTask[]
}

export interface AdminTask {
  id: number
  variant_id: number
  number: number
  title: string
  statement_text: string | null
  instruction_text: string | null
  source_data_text: string | null
  teacher_comment: string | null
  max_score: number
  scoring_type: 'all_or_nothing' | 'partial_sum'
  created_at: string
  updated_at: string
  archived_at: string | null
  fields: AdminField[]
  files: Array<{
    id: number
    original_name: string
    mime_type: string | null
    size_bytes: number
    created_at: string
  }>
}

export interface AdminField {
  id: number
  code: string
  label: string
  input_type: 'string' | 'number'
  sort_order: number
  points: number
  expected_answer: string
}