import { useEffect, useState } from 'react'
import { type CourseDetail as Detail, fetchCourse, type Meeting, type PrereqStatus, type Section } from './api.ts'
import { componentName, formatDate, formatTime, formatUnits } from './format.ts'

type State = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; course: Detail }

const PREREQ_BADGES: Record<PrereqStatus, { label: string; className: string }> = {
  none: { label: 'No prerequisites', className: 'bg-redwood-100 text-redwood-800' },
  recommended: { label: 'No required prerequisites', className: 'bg-redwood-50 text-redwood-700' },
  consent: { label: 'Instructor consent required', className: 'bg-bark-100 text-bark-700' },
  required: { label: 'Has prerequisites', className: 'bg-bark-200 text-bark-800' },
}

const QUARTER_EMOJI: Record<string, string> = { Autumn: '🍂', Winter: '❄️', Spring: '🌱', Summer: '☀️' }

export function CourseDetail({ subject, code }: { subject: string; code: string }) {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    fetchCourse(subject, code)
      .then((course) => setState({ status: 'ready', course }))
      .catch((error: Error) => setState({ status: 'error', message: error.message }))
  }, [subject, code])

  if (state.status === 'loading') return <p className="mt-4 animate-pulse text-sm text-bark-400">Loading…</p>
  if (state.status === 'error') return <p className="mt-4 text-sm text-bark-700">{state.message}</p>

  const { course } = state
  const badge = PREREQ_BADGES[course.prereq.status]
  return (
    <div className="mt-4 space-y-4 text-sm text-bark-700">
      {course.cross_listings.length > 0 && (
        <p className="text-bark-500">Also listed as {course.cross_listings.join(', ')}</p>
      )}
      {course.description && <p className="leading-relaxed text-bark-800">{course.description}</p>}

      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${badge.className}`}>{badge.label}</span>
        {course.prereq.text && <span className="text-bark-500 italic">“{course.prereq.text}”</span>}
      </div>
      {course.grading && (
        <p>
          <span className="font-semibold text-bark-600">Grading:</span> {course.grading}
        </p>
      )}

      {course.terms.map((term) => (
        <section key={term.term} className="rounded-xl bg-bark-50 px-4 py-3">
          <h3 className="font-bold text-redwood-800">
            <span aria-hidden="true">{QUARTER_EMOJI[term.quarter]} </span>
            {term.term}
          </h3>
          <TermSections sections={term.sections} />
        </section>
      ))}
    </div>
  )
}

// Above this many sections of one kind (e.g. CS 106B's ~60 discussions), show a summary line instead.
const COLLAPSE_OVER = 3

function TermSections({ sections }: { sections: Section[] }) {
  const byComponent = new Map<string, Section[]>()
  for (const section of sections.filter((s) => s.timing !== 'arranged')) {
    byComponent.set(section.component, [...(byComponent.get(section.component) ?? []), section])
  }
  const arranged = sections.filter((s) => s.timing === 'arranged')
  return (
    <ul className="mt-2 space-y-1.5">
      {[...byComponent].map(([component, group]) =>
        group.length > COLLAPSE_OVER ? (
          <CollapsedGroup key={component} component={component} sections={group} />
        ) : (
          group.map((section) => <SectionRow key={section.class_id} section={section} />)
        ),
      )}
      {arranged.length > 0 && <ArrangedRow sections={arranged} />}
    </ul>
  )
}

function CollapsedGroup({ component, sections }: { component: string; sections: Section[] }) {
  const [expanded, setExpanded] = useState(false)
  if (expanded) return sections.map((section) => <SectionRow key={section.class_id} section={section} />)
  return (
    <li className="flex flex-wrap gap-x-3">
      <span className="w-32 shrink-0 font-semibold text-bark-600">{componentName(component)}</span>
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="cursor-pointer font-semibold text-redwood-600 underline decoration-redwood-200 underline-offset-2 hover:text-redwood-800"
      >
        Show all {sections.length} sections
      </button>
    </li>
  )
}

function SectionRow({ section }: { section: Section }) {
  const timed = section.meetings.filter((m) => m.start_minute !== null)
  const instructors = uniqueNames(section.meetings)
  return (
    <li className="flex flex-wrap gap-x-3">
      <span className="w-32 shrink-0 font-semibold text-bark-600">
        {componentName(section.component)} {section.section_number}
      </span>
      <span className="min-w-0 text-bark-900">
        {timed.length > 0 ? (
          timed.map((m, i) => <MeetingTime key={i} meeting={m} />)
        ) : (
          <span className="text-bark-400 italic">Time TBA</span>
        )}
      </span>
      {instructors.length > 0 && <span className="text-bark-500">{instructors.join(', ')}</span>}
      {section.max_enrolled !== null && section.max_enrolled > 0 && (
        <span className={section.enroll_status === 'Closed' ? 'text-bark-700' : 'text-bark-400'}>
          {section.num_enrolled}/{section.max_enrolled} enrolled
          {section.enroll_status === 'Closed' && ' · Closed'}
        </span>
      )}
      <span className="text-bark-400">{formatUnits(section.units_min, section.units_max)}</span>
    </li>
  )
}

function MeetingTime({ meeting }: { meeting: Meeting }) {
  const { days, start_minute, end_minute, start_date, end_date, location } = meeting
  return (
    <span className="block">
      {days.join(' ')} {start_minute !== null && formatTime(start_minute)}–
      {end_minute !== null && formatTime(end_minute)}
      {start_date && end_date && (
        <span className="text-bark-400">
          {' '}
          ({formatDate(start_date)}–{formatDate(end_date)})
        </span>
      )}
      {location && <span className="text-bark-400"> · {location}</span>}
    </span>
  )
}

// Independent study, thesis, and clerkship sections: one per faculty member, collapsed to one line.
function ArrangedRow({ sections }: { sections: Section[] }) {
  const kinds = [...new Set(sections.map((s) => componentName(s.component)))]
  const names = [...new Set(sections.flatMap((s) => uniqueNames(s.meetings)))]
  const shown = names.slice(0, 5)
  return (
    <li className="flex flex-wrap gap-x-3">
      <span className="w-32 shrink-0 font-semibold text-bark-600">{kinds.join(', ')}</span>
      <span className="text-bark-700">
        By arrangement{names.length > 0 && ` with ${shown.join(', ')}`}
        {names.length > shown.length && ` and ${names.length - shown.length} more`}
      </span>
    </li>
  )
}

function uniqueNames(meetings: Meeting[]): string[] {
  return [...new Set(meetings.flatMap((m) => m.instructors.filter((i) => i.role !== 'TA').map((i) => i.name)))]
}
