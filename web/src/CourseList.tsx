import { useState } from 'react'
import type { CourseSummary } from './api.ts'
import { CourseDetail } from './CourseDetail.tsx'
import { formatUnits } from './format.ts'

const key = (course: CourseSummary) => `${course.subject} ${course.code}`

export function CourseList({ courses }: { courses: CourseSummary[] }) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <ul className="space-y-3">
      {courses.map((course) => {
        const isOpen = open === key(course)
        return (
          <li
            key={key(course)}
            className={`rounded-2xl border bg-white transition ${
              isOpen
                ? 'border-redwood-200 shadow-md shadow-redwood-900/10'
                : 'border-bark-100 shadow-sm hover:-translate-y-0.5 hover:border-bark-200 hover:shadow-md'
            }`}
          >
            <button
              type="button"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : key(course))}
              className="w-full cursor-pointer rounded-2xl px-5 py-4 text-left focus-visible:outline-2 focus-visible:outline-redwood-400"
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="rounded-full bg-redwood-50 px-2.5 py-0.5 text-sm font-bold text-redwood-700">
                  {key(course)}
                </span>
                <span className="font-bold text-bark-900">{course.title}</span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-bark-500">
                <span>{formatUnits(course.units_min, course.units_max)}</span>
                {course.terms.length > 0 && <span>{course.terms.join(', ')}</span>}
                {course.gers.map((ger) => (
                  <span key={ger} className="rounded-full bg-bark-50 px-2 text-xs leading-5 font-semibold text-bark-600">
                    {ger}
                  </span>
                ))}
              </div>
            </button>
            {isOpen && (
              <div className="border-t border-bark-100 px-5 pb-5">
                <CourseDetail subject={course.subject} code={course.code} />
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
