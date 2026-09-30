import { useEffect, useState } from 'react'
import { ApiError, getFramePresets, getHealth } from './api/client'
import type { BlinkPreset } from './api/types'
import BlinkComparator from './components/BlinkComparator'

const DEFAULT_DESIGNATION = '48606' // 1995 DH, validated POC control

type Health = { kind: 'checking' } | { kind: 'ok' } | { kind: 'error'; message: string }

type Presets =
  | { kind: 'loading' }
  | { kind: 'ready'; items: BlinkPreset[] }
  | { kind: 'error'; message: string }

function message(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

function App() {
  const [health, setHealth] = useState<Health>({ kind: 'checking' })
  const [presets, setPresets] = useState<Presets>({ kind: 'loading' })
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getHealth()
      .then(() => active && setHealth({ kind: 'ok' }))
      .catch((error: unknown) => active && setHealth({ kind: 'error', message: message(error) }))
    getFramePresets()
      .then((items) => {
        if (!active) return
        setPresets({ kind: 'ready', items })
        const preferred = items.find((p) => p.designation === DEFAULT_DESIGNATION)
        setSelectedId((preferred ?? items[0])?.preset_id ?? null)
      })
      .catch((error: unknown) => active && setPresets({ kind: 'error', message: message(error) }))
    return () => {
      active = false
    }
  }, [])

  const selected =
    presets.kind === 'ready'
      ? presets.items.find((p) => p.preset_id === selectedId) ?? null
      : null

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <span className="brand">Moving Object Hunter</span>
          <span className="muted"> · ZTF blink comparator</span>
        </div>
        <span className={`status ${health.kind}`} data-testid="backend-status">
          {health.kind === 'checking' && 'backend: checking…'}
          {health.kind === 'ok' && '● backend connected'}
          {health.kind === 'error' && `● backend not reachable — ${health.message}`}
        </span>
      </header>

      <div className="layout">
        <nav className="sidebar" aria-label="frame sequences">
          <h3>Validation sequences</h3>
          {presets.kind === 'loading' && <p className="muted">Loading…</p>}
          {presets.kind === 'error' && <p className="error">{presets.message}</p>}
          {presets.kind === 'ready' && (
            <ul>
              {presets.items.map((preset) => (
                <li key={preset.preset_id}>
                  <button
                    type="button"
                    className={preset.preset_id === selectedId ? 'preset active' : 'preset'}
                    onClick={() => setSelectedId(preset.preset_id)}
                  >
                    <span>{preset.label}</span>
                    <span className="muted small">
                      {preset.role} · V {preset.v_magnitude.toFixed(1)} ·{' '}
                      {preset.field_id.split('-').slice(0, 4).join('-')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>

        <main className="main">
          {selected ? (
            <BlinkComparator key={selected.preset_id} preset={selected} />
          ) : (
            presets.kind === 'ready' && <p className="muted">No sequence selected.</p>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
