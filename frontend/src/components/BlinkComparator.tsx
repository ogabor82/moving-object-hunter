import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { cachedFrame, loadFrame } from '../api/frameCache'
import type { BlinkPreset, FrameCutoutParams, FrameCutoutResponse } from '../api/types'

type FrameState =
  | { status: 'loading' }
  | { status: 'ready'; data: FrameCutoutResponse; bitmap: HTMLCanvasElement }
  | { status: 'error'; message: string }

const DISPLAY_SIZE = 540 // canvas edge in CSS pixels
const MIN_INTERVAL_MS = 150
const MAX_INTERVAL_MS = 2000
const DEFAULT_INTERVAL_MS = 600
const SCALE_BAR_ARCSEC = 10

function frameParams(preset: BlinkPreset): FrameCutoutParams[] {
  return preset.product_ids.map((productId) => ({
    product_id: productId,
    ra: preset.center_ra,
    dec: preset.center_dec,
    size_arcsec: preset.size_arcsec,
  }))
}

/** Frames already loaded this session are ready at once, the rest loading. */
function initialStates(preset: BlinkPreset): FrameState[] {
  return frameParams(preset).map((params) => {
    const frame = cachedFrame(params)
    return frame ? { status: 'ready', ...frame } : { status: 'loading' }
  })
}

function utcTime(iso: string, offsetSeconds = 0): string {
  const date = new Date(new Date(iso).getTime() + offsetSeconds * 1000)
  return date.toISOString().slice(11, 19)
}

function describeError(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

export default function BlinkComparator({ preset }: { preset: BlinkPreset }) {
  const [frames, setFrames] = useState<FrameState[]>(() => initialStates(preset))
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [intervalMs, setIntervalMs] = useState(DEFAULT_INTERVAL_MS)
  const [reloadToken, setReloadToken] = useState(0)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Load every frame of the preset in parallel; each resolves on its own.
  // Frames loaded earlier in the session come from memory, not the network.
  useEffect(() => {
    let active = true
    frameParams(preset).forEach((params, frameIndex) => {
      loadFrame(params)
        .then((frame): FrameState => ({ status: 'ready', ...frame }))
        .catch(
          (error: unknown): FrameState => ({ status: 'error', message: describeError(error) }),
        )
        .then((state) => {
          if (!active) return
          setFrames((current) =>
            current.map((frame, i) => (i === frameIndex ? state : frame)),
          )
        })
    })
    return () => {
      active = false
    }
  }, [preset, reloadToken])

  const retry = () => {
    setFrames((current) =>
      current.map((frame) => (frame.status === 'error' ? { status: 'loading' } : frame)),
    )
    setReloadToken((token) => token + 1)
  }

  const readyIndices = useMemo(
    () => frames.flatMap((frame, i) => (frame.status === 'ready' ? [i] : [])),
    [frames],
  )

  const step = useCallback(
    (direction: 1 | -1) => {
      setIndex((current) => {
        const count = preset.product_ids.length
        return (current + direction + count) % count
      })
    },
    [preset.product_ids.length],
  )

  // Auto blink: cycle through the frames that have loaded.
  useEffect(() => {
    if (!playing || readyIndices.length < 2) return
    const timer = window.setInterval(() => {
      setIndex((current) => {
        const position = readyIndices.indexOf(current)
        return readyIndices[(position + 1) % readyIndices.length]
      })
    }, intervalMs)
    return () => window.clearInterval(timer)
  }, [playing, intervalMs, readyIndices])

  // Keyboard: ← / → step, space toggles blink.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) return
      if (event.key === 'ArrowRight') step(1)
      else if (event.key === 'ArrowLeft') step(-1)
      else if (event.key === ' ') setPlaying((value) => !value)
      else return
      event.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step])

  const current = frames[index]
  const reference = frames.find((frame) => frame.status === 'ready')
  const sourceSize =
    reference?.status === 'ready'
      ? Math.max(reference.data.width, reference.data.height)
      : preset.size_arcsec
  const zoom = DISPLAY_SIZE / sourceSize

  // Draw the current frame so that the requested sky centre sits at the
  // canvas centre (aligns epochs without resampling pixel values).
  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) return
    context.fillStyle = '#05070a'
    context.fillRect(0, 0, canvas.width, canvas.height)
    if (current?.status !== 'ready') return
    const { data, bitmap } = current
    context.imageSmoothingEnabled = false
    const originX = DISPLAY_SIZE / 2 - (data.center_x + 0.5) * zoom
    const originY = DISPLAY_SIZE / 2 - (data.center_y + 0.5) * zoom
    context.drawImage(bitmap, originX, originY, data.width * zoom, data.height * zoom)
  }, [current, zoom])

  const ready = current?.status === 'ready' ? current.data : null
  const scaleBarPx = ready ? (SCALE_BAR_ARCSEC / ready.pixel_scale_arcsec) * zoom : 0
  const loadedCount = readyIndices.length

  return (
    <section className="blink">
      <header className="blink-header">
        <div>
          <h2>{preset.label}</h2>
          <p className="muted">
            {preset.role === 'control' ? 'POC control' : 'Canonical target'} ·{' '}
            {preset.field_id} · V {preset.v_magnitude.toFixed(1)} · predicted{' '}
            {preset.predicted_rate_arcsec_per_min.toFixed(2)}″/min (SkyBoT)
          </p>
        </div>
        <span className="muted">
          {loadedCount}/{frames.length} frames loaded
        </span>
      </header>

      <div className="frame-bar" data-testid="frame-info">
        <strong>
          FRAME {index + 1}/{frames.length}
        </strong>
        {ready && (
          <>
            {' '}
            · E{index + 1} {utcTime(ready.observation.observed_at)} UT start
            {ready.observation.exposure_seconds !== null &&
              ` · mid ${utcTime(
                ready.observation.observed_at,
                ready.observation.exposure_seconds / 2,
              )}`}{' '}
            · {ready.observation.filter_code} · pid {ready.observation.product_id}
          </>
        )}
      </div>

      <div className="viewer">
        <canvas
          ref={canvasRef}
          width={DISPLAY_SIZE}
          height={DISPLAY_SIZE}
          className="frame-canvas"
          aria-label="ZTF frame"
          data-testid="frame-canvas"
        />
        <div className="overlay top-right compass" aria-label="orientation">
          <span>N ↑</span>
          <span>← E</span>
        </div>
        {current?.status === 'loading' && (
          <div className="overlay center">Loading frame {index + 1}…</div>
        )}
        {current?.status === 'error' && (
          <div className="overlay center error" data-testid="frame-error">
            Frame {index + 1} failed — {current.message}
            <button type="button" onClick={retry}>
              Retry
            </button>
          </div>
        )}
      </div>

      <div className="frame-bar">
        {ready ? (
          <>
            <div className="scale-bar" style={{ width: scaleBarPx }} />
            {SCALE_BAR_ARCSEC}″ · {ready.pixel_scale_arcsec.toFixed(2)}″/px ·{' '}
            {ready.size_arcsec}″ field · zscale [{ready.stretch.vmin.toFixed(0)},{' '}
            {ready.stretch.vmax.toFixed(0)}] · rot {ready.rotation_deg.toFixed(2)}°
          </>
        ) : (
          <span className="muted">—</span>
        )}
      </div>

      <div className="controls">
        <div className="epochs" role="group" aria-label="epochs">
          {frames.map((frame, i) => (
            <button
              key={preset.product_ids[i]}
              type="button"
              className={i === index ? 'epoch active' : 'epoch'}
              onClick={() => {
                setPlaying(false)
                setIndex(i)
              }}
            >
              E{i + 1}{' '}
              {frame.status === 'ready'
                ? `${utcTime(frame.data.observation.observed_at).slice(0, 5)} · ${frame.data.observation.filter_code}`
                : frame.status === 'loading'
                  ? '…'
                  : '✗'}
            </button>
          ))}
        </div>
        <div className="transport">
          <button type="button" onClick={() => step(-1)} aria-label="previous frame">
            ◀ Prev
          </button>
          <button
            type="button"
            className="play"
            onClick={() => setPlaying((value) => !value)}
            disabled={loadedCount < 2}
            aria-label={playing ? 'pause blink' : 'start blink'}
          >
            {playing ? '❚❚ Pause' : '▶ Blink'}
          </button>
          <button type="button" onClick={() => step(1)} aria-label="next frame">
            Next ▶
          </button>
          <label className="speed">
            Speed
            <input
              type="range"
              min={MIN_INTERVAL_MS}
              max={MAX_INTERVAL_MS}
              step={50}
              value={MAX_INTERVAL_MS + MIN_INTERVAL_MS - intervalMs}
              onChange={(event) =>
                setIntervalMs(MAX_INTERVAL_MS + MIN_INTERVAL_MS - Number(event.target.value))
              }
              aria-label="blink speed"
            />
            <span className="muted">
              {intervalMs} ms ({(1000 / intervalMs).toFixed(1)} Hz)
            </span>
          </label>
        </div>
        <p className="muted hint">
          ← / → step · space blink/pause · per-frame zscale (display only) ·
          frames aligned on the requested sky centre (≤ 0.5 px, no resampling)
        </p>
      </div>
    </section>
  )
}
