import type { CourseSummary } from './api.ts'

function formatUnits({ units_min, units_max }: CourseSummary): string {
  const range = units_min === units_max ? `${units_min}` : `${units_min}–${units_max}`
  return `${range} ${units_max === 1 ? 'unit' : 'units'}`
}

export function CourseList({ courses }: { courses: CourseSummary[] }) {
  return (
    <ul className="divide-y divide-gray-200 border-y border-gray-200">
      {courses.map((course) => (
        <li key={`${course.subject} ${course.code}`} className="py-3">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-mono text-sm font-semibold text-red-800">
              {course.subject} {course.code}
            </span>
            <span className="font-medium text-gray-900">{course.title}</span>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-gray-500">
            <span>{formatUnits(course)}</span>
            {course.terms.length > 0 && <span>{course.terms.join(', ')}</span>}
            {course.gers.map((ger) => (
              <span key={ger} className="rounded bg-gray-100 px-1.5 text-xs leading-5 text-gray-700">
                {ger}
              </span>
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}
