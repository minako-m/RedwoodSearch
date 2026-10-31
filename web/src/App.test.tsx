import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import type { CourseSummary } from './api.ts'

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

function mockFetch(response: Response) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('lists courses from the API', async () => {
    mockFetch(new Response(JSON.stringify(COURSES)))
    render(<App />)
    expect(await screen.findByText('Programming Abstractions')).toBeInTheDocument()
    expect(screen.getByText('CS 106B')).toBeInTheDocument()
    expect(screen.getByText('3–5 units')).toBeInTheDocument()
    expect(screen.getByText('Autumn, Spring')).toBeInTheDocument()
    expect(screen.getByText('1 courses offered in 2026–27')).toBeInTheDocument()
  })

  it('shows an error when the API fails', async () => {
    mockFetch(new Response('', { status: 500 }))
    render(<App />)
    expect(await screen.findByText('Failed to load courses (HTTP 500)')).toBeInTheDocument()
  })
})
