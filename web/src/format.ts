export function formatUnits(min: number, max: number): string {
  const range = min === max ? `${min}` : `${min}–${max}`
  return `${range} ${max === 1 ? 'unit' : 'units'}`
}

// 900 -> "3:00 PM"
export function formatTime(minute: number): string {
  const hour = Math.floor(minute / 60)
  const suffix = hour < 12 || hour === 24 ? 'AM' : 'PM'
  const hour12 = hour % 12 === 0 ? 12 : hour % 12
  return `${hour12}:${String(minute % 60).padStart(2, '0')} ${suffix}`
}

// "2026-09-21" -> "Sep 21"
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Section component codes that students will see on the page.
const COMPONENT_NAMES: Record<string, string> = {
  LEC: 'Lecture',
  DIS: 'Discussion',
  SEM: 'Seminar',
  LAB: 'Lab',
  LBS: 'Lab section',
  ACT: 'Activity',
  PRA: 'Practicum',
  WKS: 'Workshop',
  LNG: 'Language',
  COL: 'Colloquium',
  CAS: 'Case study',
  INS: 'Independent study',
  'T/D': 'Thesis/dissertation',
  CLK: 'Clerkship',
}

export function componentName(code: string): string {
  return COMPONENT_NAMES[code] ?? code
}
