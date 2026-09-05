export interface User {
  id: number
  username: string
  role: 'viewer' | 'hr'
  permissions: string[]
}
export interface Person {
  id: number
  name: string
  work_email: string
  department: string
}
export interface Classification {
  id: number
  name: string
}
export interface Employment {
  id: number
  person_id: number
  job_title: string
  start_date: string
  end_date: string | null
  status: string
  classification: Classification
}
export interface Compliance {
  id: number
  person_id: number
  requirement: string
  status: string
  completion_date: string | null
  expiry_date: string | null
}
export interface Profile extends Person {
  employments: Employment[]
  compliance_records: Compliance[]
}
export interface Confidential {
  person_id: number
  private_notes: string
  employments: { employment_id: number; job_title: string; salary: string }[]
}
export interface Audit {
  id: number
  actor: string
  target_person_id: number | null
  requested_person_id: number
  action: string
  field_names: string[]
  timestamp: string
  outcome: string
}
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
