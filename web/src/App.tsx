import { useEffect, useState } from 'react'
import { type CourseSummary, fetchCourses } from './api.ts'
import { CourseList } from './CourseList.tsx'
import { TreeIcon } from './TreeIcon.tsx'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; courses: CourseSummary[] }

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    fetchCourses()
      .then((courses) => setState({ status: 'ready', courses }))
      .catch((error: Error) => setState({ status: 'error', message: error.message }))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-redwood-600 to-redwood-800 px-6 py-8 text-cream shadow-lg shadow-redwood-900/20">
        <div className="flex items-center gap-4">
          <div className="grid size-16 shrink-0 place-items-center rounded-2xl bg-redwood-900/30">
            <TreeIcon className="size-11" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">RedwoodSearch</h1>
            <p className="mt-1 text-redwood-100">Plan your Stanford quarter in plain English.</p>
          </div>
        </div>
        {state.status === 'ready' && (
          <p className="mt-5 inline-block rounded-full bg-cream/15 px-3 py-1 text-sm font-semibold text-redwood-50">
            {state.courses.length.toLocaleString()} courses offered in 2026–27
          </p>
        )}
        {/* A little row of trees along the bottom edge. */}
        <div aria-hidden="true" className="pointer-events-none absolute -right-2 bottom-0 flex items-end opacity-20">
          <TreeIcon className="size-10" />
          <TreeIcon className="size-16" />
          <TreeIcon className="size-12" />
          <TreeIcon className="size-20" />
        </div>
      </header>

      <div className="mt-8">
        {state.status === 'loading' && (
          <p className="animate-pulse text-center text-bark-500">Gathering courses…</p>
        )}
        {state.status === 'error' && (
          <p className="rounded-2xl bg-bark-100 px-4 py-3 text-bark-800">{state.message}</p>
        )}
        {state.status === 'ready' && <CourseList courses={state.courses} />}
      </div>
    </main>
  )
}

export default App
