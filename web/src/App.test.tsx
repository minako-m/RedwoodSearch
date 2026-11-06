import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import type { CourseDetail, CourseSummary } from './api.ts'
import { formatTime } from './format.ts'

const COURSES: CourseSummary[] = [
  {
    subject: 'CS',
    code: '106B',
    title: 'Programming Abstractions',
    units_min: 3,
    units_max: 5,
    gers: ['WAY-FR'],
    terms: ['Autumn', 'Spring'],
    career: 'UG',
  },
]

const DETAIL: CourseDetail = {
  ...COURSES[0],
  description: 'Abstraction and recursion.',
  grading: 'Letter or Credit/No Credit',
  final_exam: 'Y',
  remote: false,
  repeatable: false,
  prereq: { status: 'required', text: 'Prerequisite: CS 106A.', courses: ['CS 106A'] },
  cross_listings: ['ENGR 70B'],
  terms: [
    {
      term: '2026-2027 Autumn',
      quarter: 'Autumn',
      sections: [
        {
          class_id: 1,
          section_number: '01',
          component: 'LEC',
          units_min: 5,
          units_max: 5,
          timing: 'scheduled',
          instruction_mode: 'P',
          enroll_status: 'Open',
          num_enrolled: 300,
          max_enrolled: 400,
          num_waitlist: 0,
          max_waitlist: 0,
          notes: null,
          meetings: [
            {
              days: ['Mon', 'Wed', 'Fri'],
              start_minute: 690,
              end_minute: 740,
              start_date: '2026-09-21',
              end_date: '2026-12-04',
              location: null,
              instructors: [{ sunet: 'htiek', name: 'Schwarz, K.', role: 'PI' }],
            },
          ],
        },
        {
          class_id: 2,
          section_number: '01',
          component: 'INS',
          units_min: 1,
          units_max: 5,
          timing: 'arranged',
          instruction_mode: 'IS',
          enroll_status: 'Open',
          num_enrolled: 0,
          max_enrolled: 0,
          num_waitlist: 0,
          max_waitlist: 0,
          notes: null,
          meetings: [
            {
              days: [],
              start_minute: null,
              end_minute: null,
              start_date: null,
              end_date: null,
              location: null,
              instructors: [{ sunet: 'cain', name: 'Cain, J.', role: 'PI' }],
            },
          ],
        },
      ],
    },
  ],
}

function mockApi(routes: Record<string, unknown>, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(routes[path] ?? null), { status }))),
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('lists courses from the API', async () => {
    mockApi({ '/api/courses': COURSES })
    render(<App />)
    expect(await screen.findByText('Programming Abstractions')).toBeInTheDocument()
    expect(screen.getByText('CS 106B')).toBeInTheDocument()
    expect(screen.getByText('3–5 units')).toBeInTheDocument()
    expect(screen.getByText('Autumn, Spring')).toBeInTheDocument()
  })

  it('shows an error when the API fails', async () => {
    mockApi({}, 500)
    render(<App />)
    expect(await screen.findByText('Failed to load courses (HTTP 500)')).toBeInTheDocument()
  })

  it('expands a course to show its details', async () => {
    mockApi({ '/api/courses': COURSES, '/api/courses/CS/106B': DETAIL })
    render(<App />)
    const row = await screen.findByRole('button', { name: /Programming Abstractions/ })
    fireEvent.click(row)

    expect(await screen.findByText('Abstraction and recursion.')).toBeInTheDocument()
    expect(row).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Also listed as ENGR 70B')).toBeInTheDocument()
    expect(screen.getByText(/Prerequisite: CS 106A\./)).toBeInTheDocument()
    expect(screen.getByText('Lecture 01')).toBeInTheDocument()
    expect(screen.getByText(/Mon Wed Fri 11:30 AM/)).toBeInTheDocument()
    expect(screen.getByText('300/400 enrolled')).toBeInTheDocument()
    expect(screen.getByText('By arrangement with Cain, J.')).toBeInTheDocument()
  })
})

describe('CourseDetail', () => {
  it('collapses many sections of one kind until asked', async () => {
    const lecture = DETAIL.terms[0].sections[0]
    const discussions = Array.from({ length: 5 }, (_, i) => ({
      ...lecture,
      class_id: 100 + i,
      component: 'DIS',
      section_number: `0${i + 2}`,
    }))
    const detail = { ...DETAIL, terms: [{ ...DETAIL.terms[0], sections: [lecture, ...discussions] }] }
    mockApi({ '/api/courses': COURSES, '/api/courses/CS/106B': detail })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /Programming Abstractions/ }))

    fireEvent.click(await screen.findByRole('button', { name: 'Show all 5 sections' }))
    expect(screen.getByText('Discussion 02')).toBeInTheDocument()
    expect(screen.getByText('Discussion 06')).toBeInTheDocument()
  })
})

describe('formatTime', () => {
  it('formats minutes since midnight', () => {
    expect(formatTime(0)).toBe('12:00 AM')
    expect(formatTime(690)).toBe('11:30 AM')
    expect(formatTime(720)).toBe('12:00 PM')
    expect(formatTime(980)).toBe('4:20 PM')
  })
})
