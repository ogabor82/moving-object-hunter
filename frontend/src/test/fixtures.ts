import type {
  FrameCutoutParams,
  FrameCutoutResponse,
  M1FeatureEvidence,
  RankedCandidate,
  ReviewRankingResponse,
  Tracklet,
  UnrankedTracklet,
} from '../api/types'

export const PRODUCT_IDS = [101, 102, 103]

const FEATURES: [string, M1FeatureEvidence['direction']][] = [
  ['min_snr', 'higher_reviewed_first'],
  ['median_snr', 'higher_reviewed_first'],
  ['fit_rms_residual_arcsec', 'lower_reviewed_first'],
  ['magnitude_range_mag', 'lower_reviewed_first'],
  ['flagged_detection_count', 'lower_reviewed_first'],
  ['masked_detection_count', 'lower_reviewed_first'],
  ['sharp_abs_max', 'lower_reviewed_first'],
  ['shared_detection_tracklets', 'lower_reviewed_first'],
]

export function tracklet(id: string, status: Tracklet['status'] = 'tracklet_built'): Tracklet {
  return {
    tracklet_id: id,
    detections: PRODUCT_IDS.map((pid, i) => ({
      time: `2019-04-0${i + 1}T06:00:00Z`,
      detection: {
        source_id: `${id}-s${i}`,
        observation_product_id: pid,
        ra: 150 + i * 0.001,
        dec: 20,
        x: 100 + i,
        y: 200,
        magnitude: 19 + i * 0.1,
        magnitude_error: 0.05,
        snr: 12 - i,
        on_image_edge: false,
        mask_bits: 0,
      },
    })),
    angular_velocity_arcsec_per_min: 0.5,
    position_angle_deg: 90,
    fit_rms_residual_arcsec: 0.2,
    fit_max_residual_arcsec: 0.3,
    status,
    status_reason: status === 'rejected' ? 'max fit residual 2.10" > 1.00"' : null,
  }
}

// Frame caches are per page session: every view gets its own sky centre so
// that tests never share a cached cutout.
let viewCount = 0
export function view() {
  viewCount += 1
  return { product_ids: PRODUCT_IDS, center_ra: 100 + viewCount / 1000, center_dec: 20, size_arcsec: 60 }
}

export function candidate(buildId: string, rank: number, score: number): RankedCandidate {
  const id = `${buildId}.t${rank}`
  return {
    review_rank: rank,
    tracklet_id: id,
    review_priority_score: score,
    evidence: FEATURES.map(([feature, direction]) => ({
      feature,
      direction,
      value: feature === 'sharp_abs_max' ? null : 1,
      percentile: feature === 'sharp_abs_max' ? null : score,
      weight: 0.125,
      contribution: feature === 'sharp_abs_max' ? 0 : 0.125 * score,
    })),
    sharp_availability: 'partial',
    tracklet: tracklet(id),
    view: view(),
  }
}

export function unranked(buildId: string, n: number): UnrankedTracklet {
  const id = `${buildId}.r${n}`
  return {
    tracklet_id: id,
    reason: 'max fit residual 2.10" > 1.00"',
    tracklet: tracklet(id, 'rejected'),
    view: view(),
  }
}

/** A ranking with `count` candidates (rank 1 = highest score) and `rejected` unranked. */
export function ranking(
  buildId: string,
  count: number,
  rejected = 0,
  shuffle = false,
): ReviewRankingResponse {
  const candidates = Array.from({ length: count }, (_, i) =>
    candidate(buildId, i + 1, 1 - (i + 1) / (count + 1)),
  )
  if (shuffle) candidates.reverse()
  return {
    build_id: buildId,
    config: {
      stationary_tolerance_arcsec: 1,
      max_rate_arcsec_per_min: 1,
      search_radius_arcsec: 30,
      max_residual_arcsec: 1,
      match_radius_arcsec: 5,
    },
    observations: [],
    tracklet_count: count + rejected,
    candidate_count: count,
    unranked_count: rejected,
    ranker: {
      ranker: 'M1',
      source: 'AS-039 frozen ranker',
      inputs: FEATURES.map(([feature, direction]) => ({
        feature,
        direction: direction === 'higher_reviewed_first' ? 1 : -1,
        weight: 0.125,
      })),
      intercept: 0,
      missing_percentile: 0,
      percentile_population: 'every built tracklet of the build',
      tie_order: 'build order',
    },
    semantics: {
      purpose: 'review_priority_only',
      is_classifier: false,
      score_is_probability: false,
      candidates_filtered: false,
      complete: true,
      statement: 'Rank orders human review only.',
      known_limitations: ['Faint objects rank lower.'],
    },
    domain_notes: [],
    candidates,
    unranked: Array.from({ length: rejected }, (_, i) => unranked(buildId, i + 1)),
  }
}

export function cutout(params: FrameCutoutParams): FrameCutoutResponse {
  return {
    observation: {
      product_id: params.product_id,
      observed_at: '2019-04-01T06:00:00Z',
      field: 1,
      filter_code: 'zr',
      ccd_id: 1,
      quadrant_id: 1,
      file_frac_day: '20190401250000',
      exposure_seconds: 30,
    },
    ra: params.ra,
    dec: params.dec,
    size_arcsec: params.size_arcsec,
    width: 2,
    height: 2,
    pixel_scale_arcsec: 1.01,
    center_x: 0.5,
    center_y: 0.5,
    orientation: 'north_up_east_left',
    rotation_deg: 0,
    transform: [],
    stretch: { method: 'zscale_linear', vmin: 0, vmax: 255 },
    pixels_base64: 'AAAAAA==',
  }
}
