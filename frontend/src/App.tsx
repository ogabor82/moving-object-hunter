import { useCallback, useEffect, useState } from 'react'
import { ApiError, getHealth } from './api/client'

type HealthState =
  | { kind: 'checking' }
  | { kind: 'ok'; status: string; checkedAt: Date }
  | { kind: 'error'; message: string; checkedAt: Date }

async function fetchHealth(): Promise<HealthState> {
  try {
    const response = await getHealth()
    return { kind: 'ok', status: response.status, checkedAt: new Date() }
  } catch (error) {
    const message =
      error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
    return { kind: 'error', message, checkedAt: new Date() }
  }
}

function App() {
  const [health, setHealth] = useState<HealthState>({ kind: 'checking' })

  useEffect(() => {
    let active = true
    void fetchHealth().then((state) => {
      if (active) setHealth(state)
    })
    return () => {
      active = false
    }
  }, [])

  const check = useCallback(async () => {
    setHealth({ kind: 'checking' })
    setHealth(await fetchHealth())
  }, [])

  return (
    <main className="app">
      <h1>Moving Object Hunter</h1>
      <p className="subtitle">ZTF moving-object pipeline — frontend skeleton</p>

      <section className="panel" aria-live="polite">
        <h2>Backend</h2>
        {health.kind === 'checking' && <p>Checking /api/health…</p>}
        {health.kind === 'ok' && (
          <p className="ok" data-testid="health-ok">
            Connected — status: <strong>{health.status}</strong>{' '}
            <span className="muted">({health.checkedAt.toLocaleTimeString()})</span>
          </p>
        )}
        {health.kind === 'error' && (
          <p className="error" data-testid="health-error">
            Not reachable — {health.message}{' '}
            <span className="muted">({health.checkedAt.toLocaleTimeString()})</span>
          </p>
        )}
        <button type="button" onClick={() => void check()}>
          Check again
        </button>
      </section>
    </main>
  )
}

export default App
