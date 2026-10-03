import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { cachedFrame, loadFrame } from '../api/frameCache'
import type { FrameCutoutParams, FrameCutoutResponse } from '../api/types'

export type FrameState =
  | { status: 'loading' }
  | { status: 'ready'; data: FrameCutoutResponse; bitmap: HTMLCanvasElement }
  | { status: 'error'; message: string }

/** Frames plus the cutout window around one sky position (a preset or a review view). */
export interface FrameSequence {
  product_ids: number[]
  center_ra: number
  center_dec: number
  size_arcsec: number
}

/** Loaded frame geometry, per frame (null until that frame has loaded). */
export type FrameGeometry = Pick<FrameCutoutResponse, 'width' | 'height' | 'center_x' | 'center_y'>

export function frameParams(sequence: FrameSequence): FrameCutoutParams[] {
  return sequence.product_ids.map((productId) => ({
    product_id: productId,
    ra: sequence.center_ra,
    dec: sequence.center_dec,
    size_arcsec: sequence.size_arcsec,
  }))
}

/** Frames already loaded this session are ready at once, the rest loading. */
function initialStates(params: FrameCutoutParams[]): FrameState[] {
  return params.map((p) => {
    const frame = cachedFrame(p)
    return frame ? { status: 'ready', ...frame } : { status: 'loading' }
  })
}

function describeError(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

export interface BlinkFrames {
  params: FrameCutoutParams[]
  frames: FrameState[]
  geometry: (FrameGeometry | null)[]
  retry: () => void
}

/**
 * Load every frame of a sequence in parallel; each resolves on its own.
 * Frames loaded earlier in the session come from memory, not the network.
 * A new sequence (another candidate) starts over without remounting, so the
 * viewer keeps its frame, blink and speed settings. With `loadDelayMs`,
 * uncached frames are only requested once the sequence has stayed selected
 * that long, so stepping quickly through a queue does not download every
 * skipped candidate (cached frames still show at once).
 */
export function useBlinkFrames(sequence: FrameSequence, loadDelayMs = 0): BlinkFrames {
  const params = useMemo(() => frameParams(sequence), [sequence])
  const [state, setState] = useState(() => ({ params, frames: initialStates(params) }))
  const [reloadToken, setReloadToken] = useState(0)

  let frames = state.frames
  if (state.params !== params) {
    frames = initialStates(params)
    setState({ params, frames })
  }

  useEffect(() => {
    let active = true
    const start = () =>
      params.forEach((frameParams, frameIndex) => {
        loadFrame(frameParams)
          .then((frame): FrameState => ({ status: 'ready', ...frame }))
          .catch(
            (error: unknown): FrameState => ({ status: 'error', message: describeError(error) }),
          )
          .then((frameState) => {
            if (!active) return
            setState((current) =>
              current.params === params
                ? {
                    params,
                    frames: current.frames.map((frame, i) => (i === frameIndex ? frameState : frame)),
                  }
                : current,
            )
          })
      })
    const cached = params.every((p) => cachedFrame(p) !== undefined)
    let timer: number | undefined
    if (cached || loadDelayMs === 0) start()
    else timer = window.setTimeout(start, loadDelayMs)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [params, reloadToken, loadDelayMs])

  const retry = () => {
    setState((current) => ({
      ...current,
      frames: current.frames.map((frame) => (frame.status === 'error' ? { status: 'loading' } : frame)),
    }))
    setReloadToken((token) => token + 1)
  }

  const geometry = useMemo(
    () => frames.map((frame) => (frame.status === 'ready' ? frame.data : null)),
    [frames],
  )
  return { params, frames, geometry, retry }
}
