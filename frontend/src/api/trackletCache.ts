import { buildTracklets, getReviewRanking, identifyTracklet, projectPositions } from './client'
import { frameKey } from './frameCache'
import { SessionCache } from './sessionCache'
import type {
  BlinkPreset,
  DisplayPoint,
  FrameCutoutParams,
  IdentifyResponse,
  ReviewRankingResponse,
  Tracklet,
  TrackletBuildResponse,
} from './types'

// Session memo of pipeline results, so switching sequences or frames never
// repeats a build, a SkyBoT identification or a projection.
const builds = new SessionCache<TrackletBuildResponse>()
const projections = new SessionCache<(DisplayPoint | null)[]>()
const identifications = new SessionCache<IdentifyResponse>()
const rankings = new SessionCache<ReviewRankingResponse>()

function buildKey(preset: BlinkPreset): string {
  return preset.product_ids.join(',')
}

export function cachedBuild(preset: BlinkPreset): TrackletBuildResponse | undefined {
  return builds.get(buildKey(preset))
}

/** POST /api/tracklets/build for the preset's frames (experimental defaults). */
export function loadBuild(preset: BlinkPreset): Promise<TrackletBuildResponse> {
  return builds.load(buildKey(preset), () =>
    buildTracklets({ observation_ids: preset.product_ids }),
  )
}

/**
 * Display pixels of every detection of every tracklet of a build on one
 * frame, flattened in tracklet then detection order. The backend projects
 * them with the WCS and orientation of exactly this cutout.
 */
export function loadProjection(
  params: FrameCutoutParams,
  build: TrackletBuildResponse,
): Promise<(DisplayPoint | null)[]> {
  const positions = build.tracklets.flatMap((tracklet) =>
    tracklet.detections.map(({ detection }) => ({ ra: detection.ra, dec: detection.dec })),
  )
  return projections.load(`${frameKey(params)}#${build.build_id}`, () =>
    projectPositions(params, positions).then((response) => response.points),
  )
}

/** Display pixels of one tracklet's detections on one frame (review view). */
export function loadTrackletProjection(
  params: FrameCutoutParams,
  tracklet: Tracklet,
): Promise<(DisplayPoint | null)[]> {
  const positions = tracklet.detections.map(({ detection }) => ({
    ra: detection.ra,
    dec: detection.dec,
  }))
  return projections.load(`${frameKey(params)}#${tracklet.tracklet_id}`, () =>
    projectPositions(params, positions).then((response) => response.points),
  )
}

export function cachedIdentification(trackletId: string): IdentifyResponse | undefined {
  return identifications.get(trackletId)
}

/** POST /api/tracklets/{id}/identify (live SkyBoT; errors are never 'unknown'). */
export function loadIdentification(trackletId: string): Promise<IdentifyResponse> {
  return identifications.load(trackletId, () => identifyTracklet(trackletId))
}

export function cachedReviewRanking(buildId: string): ReviewRankingResponse | undefined {
  return rankings.get(buildId)
}

/** GET /api/tracklets/builds/{build_id}/review-ranking (deterministic, offline). */
export function loadReviewRanking(buildId: string): Promise<ReviewRankingResponse> {
  return rankings.load(buildId, () => getReviewRanking(buildId))
}
