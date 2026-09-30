import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import {
  cachedBuild,
  cachedIdentification,
  loadBuild,
  loadIdentification,
  loadProjection,
} from '../api/trackletCache'
import type {
  BlinkPreset,
  DisplayPoint,
  FrameCutoutParams,
  FrameCutoutResponse,
  IdentifyResponse,
  Tracklet,
  TrackletBuildResponse,
} from '../api/types'

export type Async<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; value: T }
  | { status: 'error'; message: string }

function describeError(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

function initial<T>(value: T | undefined, otherwise: Async<T>): Async<T> {
  return value === undefined ? otherwise : { status: 'ready', value }
}

/** One tracklet with the display pixel of each detection on one frame. */
export interface OverlayTrack {
  tracklet: Tracklet
  /** Detection points on the frame; `epoch` is the frame index (E1 = 0). */
  points: { epoch: number; point: DisplayPoint }[]
}

/** Loaded frame geometry needed to decide what is in view. */
type FrameGeometry = Pick<FrameCutoutResponse, 'width' | 'height' | 'center_x' | 'center_y'>

/**
 * Tracklets of a build on one frame, from the backend projection
 * (`points` is flattened in tracklet then detection order).
 */
export function tracksOnFrame(
  build: TrackletBuildResponse,
  points: (DisplayPoint | null)[],
  productIds: number[],
): OverlayTrack[] {
  let offset = 0
  return build.tracklets.map((tracklet) => {
    const track = tracklet.detections.flatMap(({ detection }, i) => {
      const point = points[offset + i]
      const epoch = productIds.indexOf(detection.observation_product_id)
      return point && epoch >= 0 ? [{ epoch, point }] : []
    })
    offset += tracklet.detections.length
    return { tracklet, points: track }
  })
}

/**
 * Tracklets with every detection inside the frame, built ones first, then
 * by distance of their mean point from the sequence centre. Only a display
 * choice: the ordering carries no scientific meaning.
 */
export function tracksInView(tracks: OverlayTrack[], frame: FrameGeometry): OverlayTrack[] {
  const inside = ({ x, y }: DisplayPoint) =>
    x >= -0.5 && y >= -0.5 && x <= frame.width - 0.5 && y <= frame.height - 0.5
  const distance = (track: OverlayTrack) => {
    const n = track.points.length
    const x = track.points.reduce((sum, p) => sum + p.point.x, 0) / n
    const y = track.points.reduce((sum, p) => sum + p.point.y, 0) / n
    return Math.hypot(x - frame.center_x, y - frame.center_y)
  }
  return tracks
    .filter(
      (track) =>
        track.points.length === track.tracklet.detections.length &&
        track.points.every(({ point }) => inside(point)),
    )
    .map((track) => ({
      track,
      built: track.tracklet.status === 'tracklet_built',
      d: distance(track),
    }))
    .sort((a, b) => Number(b.built) - Number(a.built) || a.d - b.d)
    .map(({ track }) => track)
}

export interface TrackletOverlayState {
  build: Async<TrackletBuildResponse>
  runBuild: () => void
  /** Tracks per frame index, once that frame's projection has loaded. */
  tracks: (OverlayTrack[] | undefined)[]
  /** Frames whose projection failed (no overlay there), with the reason. */
  projectionErrors: { epoch: number; message: string }[]
  inView: OverlayTrack[]
  selectedId: string | null
  select: (trackletId: string) => void
  identification: Async<IdentifyResponse>
  retryIdentification: () => void
}

/**
 * Build → project onto every loaded frame → pick a tracklet → identify.
 * All results are memoised for the session (api/trackletCache).
 */
export function useTrackletOverlay(
  preset: BlinkPreset,
  params: FrameCutoutParams[],
  frames: (FrameGeometry | null)[],
): TrackletOverlayState {
  const [build, setBuild] = useState<Async<TrackletBuildResponse>>(() =>
    initial(cachedBuild(preset), { status: 'idle' }),
  )
  const [projections, setProjections] = useState<Async<(DisplayPoint | null)[]>[]>(() =>
    params.map(() => ({ status: 'idle' })),
  )
  const [selectedId, setSelectedId] = useState<string | null>(null)
  // Settled identifications by tracklet id (in flight = absent).
  const [identified, setIdentified] = useState<Record<string, Async<IdentifyResponse>>>({})
  const [buildToken, setBuildToken] = useState(0)
  const [identifyToken, setIdentifyToken] = useState(0)

  useEffect(() => {
    if (buildToken === 0) return
    let active = true
    loadBuild(preset)
      .then((value) => active && setBuild({ status: 'ready', value }))
      .catch(
        (error: unknown) => active && setBuild({ status: 'error', message: describeError(error) }),
      )
    return () => {
      active = false
    }
  }, [preset, buildToken])

  const runBuild = () => {
    setBuild({ status: 'loading' })
    setBuildToken((token) => token + 1)
  }

  // Project the build's detections onto each frame once the frame is loaded
  // (the backend reuses that frame's cached cutout: no IRSA request).
  const builtValue = build.status === 'ready' ? build.value : null
  const loadedMask = frames.map((frame) => (frame === null ? '0' : '1')).join('')
  useEffect(() => {
    if (!builtValue) return
    let active = true
    params.forEach((frameParams, i) => {
      if (loadedMask[i] !== '1') return
      const settle = (state: Async<(DisplayPoint | null)[]>) =>
        active && setProjections((current) => current.map((p, j) => (j === i ? state : p)))
      loadProjection(frameParams, builtValue)
        .then((value) => settle({ status: 'ready', value }))
        .catch((error: unknown) => settle({ status: 'error', message: describeError(error) }))
    })
    return () => {
      active = false
    }
  }, [builtValue, params, loadedMask])

  const tracks = useMemo(
    () =>
      projections.map((projection) =>
        builtValue && projection.status === 'ready'
          ? tracksOnFrame(builtValue, projection.value, preset.product_ids)
          : undefined,
      ),
    [projections, builtValue, preset.product_ids],
  )

  const referenceIndex = tracks.findIndex((t, i) => t !== undefined && frames[i] !== null)
  const referenceFrame = referenceIndex >= 0 ? frames[referenceIndex] : null
  const referenceTracks = referenceIndex >= 0 ? tracks[referenceIndex] : undefined
  const inView = useMemo(
    () => (referenceTracks && referenceFrame ? tracksInView(referenceTracks, referenceFrame) : []),
    [referenceTracks, referenceFrame],
  )

  // Default selection: the first tracklet in view.
  const effectiveId = selectedId ?? inView[0]?.tracklet.tracklet_id ?? null

  useEffect(() => {
    if (!effectiveId) return
    let active = true
    const settle = (state: Async<IdentifyResponse>) =>
      active && setIdentified((current) => ({ ...current, [effectiveId]: state }))
    loadIdentification(effectiveId)
      .then((value) => settle({ status: 'ready', value }))
      .catch((error: unknown) => settle({ status: 'error', message: describeError(error) }))
    return () => {
      active = false
    }
  }, [effectiveId, identifyToken])

  const identification: Async<IdentifyResponse> = !effectiveId
    ? { status: 'idle' }
    : (identified[effectiveId] ?? initial(cachedIdentification(effectiveId), { status: 'loading' }))

  const retryIdentification = () => {
    if (!effectiveId) return
    setIdentified(({ [effectiveId]: _dropped, ...rest }) => rest)
    setIdentifyToken((token) => token + 1)
  }

  return {
    build,
    runBuild,
    tracks,
    projectionErrors: projections.flatMap((projection, epoch) =>
      projection.status === 'error' ? [{ epoch, message: projection.message }] : [],
    ),
    inView,
    selectedId: effectiveId,
    select: setSelectedId,
    identification,
    retryIdentification,
  }
}

const TRACK_COLOR = '#ffb547'
const GAP = 7 // CSS px kept clear around each detection

/**
 * Draw one tracklet on the canvas: a crosshair (open centre) on this
 * epoch's detection, small rings on the other epochs' detections, and the
 * motion path between them (trimmed around the detections) with an arrow
 * in the direction of motion. `toCanvas` maps display pixels to canvas.
 */
export function drawTrack(
  context: CanvasRenderingContext2D,
  track: OverlayTrack,
  epoch: number,
  toCanvas: (point: DisplayPoint) => { x: number; y: number },
): void {
  const points = track.points.map(({ epoch: e, point }) => ({ epoch: e, ...toCanvas(point) }))
  context.save()
  context.strokeStyle = TRACK_COLOR
  context.fillStyle = TRACK_COLOR
  context.lineWidth = 1.25
  context.font = '11px ui-monospace, Menlo, monospace'

  context.setLineDash([4, 3])
  context.globalAlpha = 0.7
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]
    const b = points[i]
    const length = Math.hypot(b.x - a.x, b.y - a.y)
    if (length <= 2 * GAP) continue
    const ux = (b.x - a.x) / length
    const uy = (b.y - a.y) / length
    context.beginPath()
    context.moveTo(a.x + ux * GAP, a.y + uy * GAP)
    context.lineTo(b.x - ux * GAP, b.y - uy * GAP)
    context.stroke()
    if (i === points.length - 1) {
      const tipX = b.x - ux * GAP
      const tipY = b.y - uy * GAP
      context.setLineDash([])
      context.beginPath()
      context.moveTo(tipX, tipY)
      context.lineTo(tipX - ux * 7 - uy * 4, tipY - uy * 7 + ux * 4)
      context.lineTo(tipX - ux * 7 + uy * 4, tipY - uy * 7 - ux * 4)
      context.closePath()
      context.fill()
    }
  }
  context.setLineDash([])

  for (const p of points) {
    if (p.epoch === epoch) {
      context.globalAlpha = 1
      context.lineWidth = 1.5
      context.beginPath()
      for (const [dx, dy] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ]) {
        context.moveTo(p.x + dx * GAP, p.y + dy * GAP)
        context.lineTo(p.x + dx * (GAP + 9), p.y + dy * (GAP + 9))
      }
      context.stroke()
    } else {
      context.globalAlpha = 0.55
      context.lineWidth = 1
      context.beginPath()
      context.arc(p.x, p.y, GAP - 2, 0, 2 * Math.PI)
      context.stroke()
    }
    context.globalAlpha = p.epoch === epoch ? 1 : 0.55
    context.fillText(`E${p.epoch + 1}`, p.x + GAP + 3, p.y - GAP - 1)
  }
  context.restore()
}
