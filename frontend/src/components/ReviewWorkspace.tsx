import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { loadFrame } from '../api/frameCache'
import { cachedReviewRanking, loadReviewRanking } from '../api/trackletCache'
import type {
  RankedCandidate,
  ReviewRankingResponse,
  ReviewView,
  Tracklet,
  UnrankedTracklet,
} from '../api/types'
import { BlinkViewer } from './BlinkComparator'
import { frameParams, useBlinkFrames } from './blinkFrames'
import CandidatePanel from './CandidatePanel'
import {
  evidenceOf,
  initialSelection,
  reviewOrder,
  shortId,
  stepSelection,
  type ReviewSelection,
} from './reviewQueue'
import { useCandidateTrack, type Async } from './trackletOverlay'

function describeError(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

/** The item under review: a ranked candidate or an unranked (rejected) tracklet. */
export type ReviewItem =
  | { kind: 'ranked'; candidate: RankedCandidate; tracklet: Tracklet; view: ReviewView }
  | { kind: 'unranked'; entry: UnrankedTracklet; tracklet: Tracklet; view: ReviewView }

const PREFETCH_DELAY_MS = 400
// Uncached frames load once a candidate stays selected this long.
const LOAD_DELAY_MS = 150

/**
 * Ranked candidate review workstation (AS-042): every candidate of one
 * build in M1 review order → blink / overlay of the selected one →
 * previous / next. Read-only; the order is review priority only.
 */
export default function ReviewWorkspace({ buildId }: { buildId: string }) {
  const [ranking, setRanking] = useState<Async<ReviewRankingResponse>>(() => {
    const cached = cachedReviewRanking(buildId)
    return cached ? { status: 'ready', value: cached } : { status: 'loading' }
  })
  const [loadToken, setLoadToken] = useState(0)

  useEffect(() => {
    let active = true
    loadReviewRanking(buildId)
      .then((value) => active && setRanking({ status: 'ready', value }))
      .catch(
        (error: unknown) => active && setRanking({ status: 'error', message: describeError(error) }),
      )
    return () => {
      active = false
    }
  }, [buildId, loadToken])

  if (ranking.status === 'loading' || ranking.status === 'idle') {
    return (
      <div className="review-state" data-testid="review-loading">
        <p className="muted">Loading the M1 review order of build {buildId}…</p>
      </div>
    )
  }
  if (ranking.status === 'error') {
    return (
      <div className="review-state" data-testid="review-error">
        <p className="error">Could not load the review order of build {buildId} — {ranking.message}</p>
        <p className="muted small">
          Builds live in the backend's memory (latest 20) and are lost on restart; rebuild the
          sequence if it is gone.
        </p>
        <button
          type="button"
          onClick={() => {
            setRanking({ status: 'loading' })
            setLoadToken((token) => token + 1)
          }}
        >
          Retry
        </button>
      </div>
    )
  }
  return <ReviewQueue ranking={ranking.value} />
}

function ReviewQueue({ ranking }: { ranking: ReviewRankingResponse }) {
  const candidates = useMemo(() => reviewOrder(ranking.candidates), [ranking.candidates])
  const unranked = ranking.unranked
  const [selection, setSelection] = useState<ReviewSelection | null>(() =>
    initialSelection(ranking),
  )
  const [unrankedOpen, setUnrankedOpen] = useState(() => ranking.candidates.length === 0)
  const activeRow = useRef<HTMLButtonElement>(null)

  const length = selection?.queue === 'unranked' ? unranked.length : candidates.length
  const step = useCallback(
    (direction: 1 | -1) =>
      setSelection((current) => (current ? stepSelection(current, direction, length) : current)),
    [length],
  )

  // Keyboard: n / ↓ next candidate, p / ↑ previous (← / → stay frame steps).
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey)
        return
      if (event.key === 'n' || event.key === 'ArrowDown') step(1)
      else if (event.key === 'p' || event.key === 'ArrowUp') step(-1)
      else return
      event.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step])

  // Keep the active row visible in the list.
  useEffect(() => {
    activeRow.current?.scrollIntoView?.({ block: 'nearest' })
  }, [selection])

  const item: ReviewItem | null = !selection
    ? null
    : selection.queue === 'ranked'
      ? {
          kind: 'ranked',
          candidate: candidates[selection.index],
          tracklet: candidates[selection.index].tracklet,
          view: candidates[selection.index].view,
        }
      : {
          kind: 'unranked',
          entry: unranked[selection.index],
          tracklet: unranked[selection.index].tracklet,
          view: unranked[selection.index].view,
        }

  // Warm the next item's frames so that Next is quick (fire and forget).
  const nextView =
    selection && selection.index + 1 < length
      ? (selection.queue === 'ranked' ? candidates : unranked)[selection.index + 1].view
      : null
  useEffect(() => {
    if (!nextView) return
    const timer = window.setTimeout(() => {
      frameParams(nextView).forEach((params) => loadFrame(params).catch(() => undefined))
    }, PREFETCH_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [nextView])

  const select = (next: ReviewSelection) => setSelection(next)
  const isActive = (queue: ReviewSelection['queue'], index: number) =>
    selection?.queue === queue && selection.index === index

  return (
    <div className="review" data-testid="review-workspace">
      <nav className="sidebar queue" aria-label="review queue">
        <div className="queue-head">
          <h3>
            Ranked candidates <span data-testid="candidate-count">{candidates.length}</span>
          </h3>
          <p className="muted small" data-testid="review-semantics">
            Build {ranking.build_id} · M1 review order. Rank is the order to look at them, not a
            verdict; the priority score is not a probability or confidence. All {candidates.length}{' '}
            are listed.
          </p>
          <details className="small">
            <summary className="muted">
              About this order
              {ranking.domain_notes.length > 0 && ` · ${ranking.domain_notes.length} domain note(s)`}
            </summary>
            <p>{ranking.semantics.statement}</p>
            {ranking.domain_notes.length > 0 && (
              <>
                <p className="muted">This build vs the validated unit:</p>
                <ul data-testid="domain-notes">
                  {ranking.domain_notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="muted">Known limitations (AS-040):</p>
            <ul>
              {ranking.semantics.known_limitations.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </details>
        </div>

        {candidates.length === 0 ? (
          <p className="muted queue-empty" data-testid="review-empty">
            {unranked.length === 0
              ? 'This build has no tracklets — nothing to review.'
              : 'No built tracklet to rank in this build; its rejected tracklets are listed below.'}
          </p>
        ) : (
          <ol className="queue-list" aria-label="ranked candidates" data-testid="ranked-list">
            {candidates.map((candidate, index) => {
              const active = isActive('ranked', index)
              const flagged = evidenceOf(candidate, 'flagged_detection_count')?.value ?? 0
              const shared = evidenceOf(candidate, 'shared_detection_tracklets')?.value ?? 0
              return (
                <li key={candidate.tracklet_id}>
                  <button
                    type="button"
                    ref={active ? activeRow : undefined}
                    className={active ? 'queue-row active' : 'queue-row'}
                    aria-current={active ? 'true' : undefined}
                    onClick={() => select({ queue: 'ranked', index })}
                    data-testid="ranked-row"
                  >
                    <span className="queue-rank">#{candidate.review_rank}</span>
                    <span className="queue-id">{shortId(candidate.tracklet_id)}</span>
                    <span
                      className="queue-prio muted"
                      title="M1 review priority — orders review only; not a probability or confidence"
                    >
                      prio {candidate.review_priority_score.toFixed(3)}
                    </span>
                    <span className="queue-meta muted">
                      {candidate.tracklet.angular_velocity_arcsec_per_min.toFixed(2)}″/min · rms{' '}
                      {candidate.tracklet.fit_rms_residual_arcsec.toFixed(2)}″
                      {flagged > 0 && ` · ${flagged} edge/mask`}
                      {shared > 0 && ` · shares det.`}
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        )}

        <details
          className="unranked"
          open={unrankedOpen}
          onToggle={(event) => setUnrankedOpen(event.currentTarget.open)}
          data-testid="unranked-section"
        >
          <summary>
            Unranked <span data-testid="unranked-count">{unranked.length}</span> · rejected
            tracklets
          </summary>
          <p className="muted small">
            Not given an M1 rank: these tracklets failed the earlier fit/build criterion (fit
            residual above the build limit), so they are outside the ranked population. Kept here
            for completeness; they can still be blinked.
          </p>
          {unranked.length === 0 ? (
            <p className="muted small">None in this build.</p>
          ) : (
            <ul className="queue-list" aria-label="unranked tracklets">
              {unranked.map((entry, index) => {
                const active = isActive('unranked', index)
                return (
                  <li key={entry.tracklet_id}>
                    <button
                      type="button"
                      ref={active ? activeRow : undefined}
                      className={active ? 'queue-row unranked-row active' : 'queue-row unranked-row'}
                      aria-current={active ? 'true' : undefined}
                      onClick={() => select({ queue: 'unranked', index })}
                      data-testid="unranked-row"
                    >
                      <span className="queue-rank">—</span>
                      <span className="queue-id">{shortId(entry.tracklet_id)}</span>
                      <span className="queue-meta muted">
                        {entry.tracklet.status_reason ?? entry.reason}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </details>
      </nav>

      <main className="main">
        {item && selection ? (
          <>
            <div className="review-nav" role="group" aria-label="candidate navigation">
              <button
                type="button"
                onClick={() => step(-1)}
                disabled={selection.index === 0}
                aria-label="previous candidate"
              >
                ◀ Previous
              </button>
              <strong className="review-position" data-testid="review-position">
                {selection.queue === 'ranked'
                  ? `Candidate ${selection.index + 1} / ${candidates.length}`
                  : `Unranked ${selection.index + 1} / ${unranked.length}`}
              </strong>
              <button
                type="button"
                onClick={() => step(1)}
                disabled={selection.index >= length - 1}
                aria-label="next candidate"
              >
                Next ▶
              </button>
              <span className="muted small">n / ↓ next · p / ↑ previous</span>
            </div>
            <CandidateReview item={item} total={candidates.length} />
          </>
        ) : (
          <p className="muted">Nothing to review in this build.</p>
        )}
      </main>
    </div>
  )
}

/** Blink / overlay and details of the item under review (one viewer, reused). */
function CandidateReview({ item, total }: { item: ReviewItem; total: number }) {
  const { tracklet, view } = item
  const blink = useBlinkFrames(view, LOAD_DELAY_MS)
  const overlay = useCandidateTrack(tracklet, view.product_ids, blink.params, blink.geometry)
  const [overlayVisible, setOverlayVisible] = useState(true)
  const toggleOverlay = useCallback(() => setOverlayVisible((value) => !value), [])

  return (
    <div className="workspace">
      <BlinkViewer
        heading={
          <>
            <h2 data-testid="review-heading">
              {item.kind === 'ranked'
                ? `#${item.candidate.review_rank} · ${shortId(tracklet.tracklet_id)}`
                : `Unranked · ${shortId(tracklet.tracklet_id)}`}
            </h2>
            <p className="muted">
              {item.kind === 'ranked'
                ? `review rank ${item.candidate.review_rank} of ${total}`
                : 'rejected tracklet, no M1 rank'}{' '}
              · {view.product_ids.length} frames · {view.size_arcsec.toFixed(0)}″ cutout around the
              track
            </p>
          </>
        }
        productIds={view.product_ids}
        blink={blink}
        tracks={overlay.tracks}
        overlayVisible={overlayVisible}
        onToggleOverlay={toggleOverlay}
      />
      <CandidatePanel
        item={item}
        overlayVisible={overlayVisible}
        onToggleOverlay={toggleOverlay}
        overlayErrors={overlay.errors}
      />
    </div>
  )
}
