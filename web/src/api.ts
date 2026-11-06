// Mirrors api/models.py on the server; keep the two in sync.
export type CourseSummary = {
  subject: string
  code: string
  title: string
  units_min: number
  units_max: number
  gers: string[]
  terms: string[]
  career: string | null
}

export type PrereqStatus = 'none' | 'recommended' | 'consent' | 'required'
export type Timing = 'scheduled' | 'arranged' | 'tba'

export type Instructor = { sunet: string; name: string; role: string | null }

export type Meeting = {
  days: string[]
  start_minute: number | null
  end_minute: number | null
  start_date: string | null
  end_date: string | null
  location: string | null
  instructors: Instructor[]
}

export type Section = {
  class_id: number
  section_number: string
  component: string
  units_min: number
  units_max: number
  timing: Timing
  instruction_mode: string | null
  enroll_status: string | null
  num_enrolled: number | null
  max_enrolled: number | null
  num_waitlist: number | null
  max_waitlist: number | null
  notes: string | null
  meetings: Meeting[]
}

export type TermSections = { term: string; quarter: string; sections: Section[] }

export type CourseDetail = {
  subject: string
  code: string
  title: string
  description: string
  units_min: number
  units_max: number
  gers: string[]
  grading: string | null
  career: string | null
  final_exam: string | null
  remote: boolean | null
  repeatable: boolean | null
  prereq: { status: PrereqStatus; text: string | null; courses: string[] }
  cross_listings: string[]
  terms: TermSections[]
}

async function getJson<T>(path: string, what: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`Failed to load ${what} (HTTP ${response.status})`)
  }
  return response.json()
}

export function fetchCourses(): Promise<CourseSummary[]> {
  return getJson('/api/courses', 'courses')
}

export function fetchCourse(subject: string, code: string): Promise<CourseDetail> {
  const path = `/api/courses/${encodeURIComponent(subject)}/${encodeURIComponent(code)}`
  return getJson(path, `${subject} ${code}`)
}
