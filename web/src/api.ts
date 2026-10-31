// Mirrors ingest.parse.CourseSummary on the server.
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

export async function fetchCourses(): Promise<CourseSummary[]> {
  const response = await fetch('/api/courses')
  if (!response.ok) {
    throw new Error(`Failed to load courses (HTTP ${response.status})`)
  }
  return response.json()
}
