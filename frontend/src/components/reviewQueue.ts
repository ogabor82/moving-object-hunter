import type { M1FeatureEvidence, RankedCandidate, ReviewRankingResponse } from '../api/types'

/**
 * Review queue state for one build (AS-042). Presentation only: the M1
 * order comes from the backend and is never changed, cut or filtered here.
 */

/** Which list the active item is in, and its 0-based position there. */
export interface ReviewSelection {
  queue: 'ranked' | 'unranked'
  index: number
}

/** All ranked candidates, rank 1 first (the API order; sorting is a guard). */
export function reviewOrder(candidates: RankedCandidate[]): RankedCandidate[] {
  return [...candidates].sort((a, b) => a.review_rank - b.review_rank)
}

/** First item to review: rank 1, or the first unranked tracklet if none is ranked. */
export function initialSelection(ranking: ReviewRankingResponse): ReviewSelection | null {
  if (ranking.candidates.length > 0) return { queue: 'ranked', index: 0 }
  if (ranking.unranked.length > 0) return { queue: 'unranked', index: 0 }
  return null
}

/** Previous / next within the same list; stops at either end (no wrap). */
export function stepSelection(
  selection: ReviewSelection,
  direction: 1 | -1,
  length: number,
): ReviewSelection {
  const index = Math.min(Math.max(selection.index + direction, 0), length - 1)
  return { ...selection, index }
}

/** Short tracklet label: the part after `<build_id>.`. */
export function shortId(trackletId: string): string {
  return trackletId.split('.').pop() ?? trackletId
}

const FEATURE_LABELS: Record<string, string> = {
  min_snr: 'min SNR',
  median_snr: 'median SNR',
  fit_rms_residual_arcsec: 'fit rms ″',
  magnitude_range_mag: 'mag range',
  flagged_detection_count: 'edge/masked det.',
  masked_detection_count: 'masked det.',
  sharp_abs_max: 'max |sharp|',
  shared_detection_tracklets: 'shared det.',
}

export function featureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature
}

export function evidenceOf(candidate: RankedCandidate, feature: string): M1FeatureEvidence | undefined {
  return candidate.evidence.find((e) => e.feature === feature)
}
