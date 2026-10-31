import { useEffect, useState } from 'react'
import { type CourseSummary, fetchCourses } from './api.ts'
import { CourseList } from './CourseList.tsx'

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
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-semibold text-red-800">RedwoodSearch</h1>
      <p className="mt-2 text-gray-600">
        {state.status === 'ready'
          ? `${state.courses.length.toLocaleString()} courses offered in 2026–27`
          : 'Plan your Stanford quarter in plain English.'}
      </p>
      <div className="mt-8">
        {state.status === 'loading' && <p className="text-gray-500">Loading courses…</p>}
        {state.status === 'error' && <p className="text-red-700">{state.message}</p>}
        {state.status === 'ready' && <CourseList courses={state.courses} />}
      </div>
    </main>
  )
}

export default App
