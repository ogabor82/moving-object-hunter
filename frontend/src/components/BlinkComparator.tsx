import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { BlinkPreset } from '../api/types'
import { useBlinkFrames, type BlinkFrames } from './blinkFrames'
import TrackletPanel from './TrackletPanel'
import { drawTrack, useTrackletOverlay, type OverlayTrack } from './trackletOverlay'

const DISPLAY_SIZE = 540 // canvas edge in CSS pixels
const MIN_INTERVAL_MS = 150
const MAX_INTERVAL_MS = 2000
const DEFAULT_INTERVAL_MS = 600
const SCALE_BAR_ARCSEC = 10

function utcTime(iso: string, offsetSeconds = 0): string {
  const date = new Date(new Date(iso).getTime() + offsetSeconds * 1000)
  return date.toISOString().slice(11, 19)
}

/**
 * The blink comparator: one canvas, epoch buttons, step / blink transport
 * and the tracklet overlay. `tracks[i]` is the tracklet drawn on frame i.
 */
export function BlinkViewer({
  heading,
  productIds,
  blink,
  tracks,
  overlayVisible,
  onToggleOverlay,
}: {
  heading: ReactNode
  productIds: number[]
  blink: BlinkFrames
  tracks: (OverlayTrack | undefined)[]
  overlayVisible: boolean
  onToggleOverlay: () => void
}) {
  const { frames, retry } = blink
  const [rawIndex, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [intervalMs, setIntervalMs] = useState(DEFAULT_INTERVAL_MS)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const frameCount = frames.length
  const index = Math.min(rawIndex, Math.max(frameCount - 1, 0))

  const readyIndices = useMemo(
    () => frames.flatMap((frame, i) => (frame.status === 'ready' ? [i] : [])),
    [frames],
  )

  const step = useCallback(
    (direction: 1 | -1) => {
      setIndex((current) => (current + direction + frameCount) % frameCount)
    },
    [frameCount],
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

  // Keyboard: ← / → step, space toggles blink, o toggles the overlay.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) return
      if (event.key === 'ArrowRight') step(1)
      else if (event.key === 'ArrowLeft') step(-1)
      else if (event.key === ' ') setPlaying((value) => !value)
      else if (event.key === 'o') onToggleOverlay()
      else return
      event.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, onToggleOverlay])

  const current = frames[index]
  const reference = frames.find((frame) => frame.status === 'ready')
  const sourceSize =
    reference?.status === 'ready' ? Math.max(reference.data.width, reference.data.height) : 1
  const zoom = DISPLAY_SIZE / sourceSize

  // Draw the current frame so that the requested sky centre sits at the
  // canvas centre (aligns epochs without resampling pixel values).
  const track = tracks[index]
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

    // Tracklet overlay: detections projected onto this very cutout by the
    // backend, in the same display pixels as the image.
    if (overlayVisible && track) {
      drawTrack(context, track, index, ({ x, y }) => ({
        x: originX + (x + 0.5) * zoom,
        y: originY + (y + 0.5) * zoom,
      }))
    }
  }, [current, zoom, index, track, overlayVisible])

  const ready = current?.status === 'ready' ? current.data : null
  const scaleBarPx = ready ? (SCALE_BAR_ARCSEC / ready.pixel_scale_arcsec) * zoom : 0
  const loadedCount = readyIndices.length

  return (
    <section className="blink">
      <header className="blink-header">
        <div>{heading}</div>
        <span className="muted" data-testid="frames-loaded">
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
            {SCALE_BAR_ARCSEC}″ · {ready.pixel_scale_arcsec.toFixed(2)}″/px · {ready.size_arcsec}″
            field · zscale [{ready.stretch.vmin.toFixed(0)}, {ready.stretch.vmax.toFixed(0)}] ·
            rot {ready.rotation_deg.toFixed(2)}°
          </>
        ) : (
          <span className="muted">—</span>
        )}
      </div>

      <div className="controls">
        <div className="epochs" role="group" aria-label="epochs">
          {frames.map((frame, i) => (
            <button
              key={productIds[i]}
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
          ← / → step · space blink/pause · o overlay · per-frame zscale (display only) · frames
          aligned on the requested sky centre (≤ 0.5 px, no resampling)
        </p>
      </div>
    </section>
  )
}

/** Blink comparator of one frozen validation sequence, with its tracklet panel. */
export default function BlinkComparator({
  preset,
  onReview,
}: {
  preset: BlinkPreset
  onReview: (buildId: string) => void
}) {
  const blink = useBlinkFrames(preset)
  const overlay = useTrackletOverlay(preset, blink.params, blink.geometry)
  const [overlayVisible, setOverlayVisible] = useState(true)
  const toggleOverlay = useCallback(() => setOverlayVisible((value) => !value), [])
  const tracks = useMemo(
    () =>
      overlay.tracks.map((onFrame) =>
        onFrame?.find((t) => t.tracklet.tracklet_id === overlay.selectedId),
      ),
    [overlay.tracks, overlay.selectedId],
  )

  return (
    <div className="workspace">
      <BlinkViewer
        heading={
          <>
            <h2>{preset.label}</h2>
            <p className="muted">
              {preset.role === 'control' ? 'POC control' : 'Canonical target'} · {preset.field_id} ·
              V {preset.v_magnitude.toFixed(1)} · predicted{' '}
              {preset.predicted_rate_arcsec_per_min.toFixed(2)}″/min (SkyBoT)
            </p>
          </>
        }
        productIds={preset.product_ids}
        blink={blink}
        tracks={tracks}
        overlayVisible={overlayVisible}
        onToggleOverlay={toggleOverlay}
      />
      <TrackletPanel
        preset={preset}
        state={overlay}
        overlayVisible={overlayVisible}
        onToggleOverlay={toggleOverlay}
        onReview={onReview}
      />
    </div>
  )
}
