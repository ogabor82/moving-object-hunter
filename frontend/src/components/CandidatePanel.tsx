import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { cachedIdentification, loadIdentification } from '../api/trackletCache'
import type { IdentifyResponse, RankedCandidate } from '../api/types'
import type { ReviewItem } from './ReviewWorkspace'
import { featureLabel } from './reviewQueue'
import { IdentificationResult, TrackletSummary } from './TrackletDetails'
import type { Async } from './trackletOverlay'

function describeError(error: unknown): string {
  return error instanceof ApiError ? `${error.code}: ${error.message}` : String(error)
}

function formatValue(value: number | null): string {
  if (value === null) return 'missing'
  return Number.isInteger(value) ? String(value) : value.toFixed(3)
}

/**
 * SkyBoT identification on request only, so that stepping through the
 * queue never queries SkyBoT (context for the reviewer, not an M1 input).
 */
function useOnDemandIdentification(trackletId: string) {
  // Request count per tracklet: absent = not requested in this view.
  const [requests, setRequests] = useState<Record<string, number>>({})
  const [settled, setSettled] = useState<Record<string, Async<IdentifyResponse>>>({})
  const token = requests[trackletId]

  useEffect(() => {
    if (token === undefined) return
    let active = true
    const settle = (state: Async<IdentifyResponse>) =>
      active && setSettled((current) => ({ ...current, [trackletId]: state }))
    loadIdentification(trackletId)
      .then((value) => settle({ status: 'ready', value }))
      .catch((error: unknown) => settle({ status: 'error', message: describeError(error) }))
    return () => {
      active = false
    }
  }, [trackletId, token])

  const cached = cachedIdentification(trackletId)
  const state: Async<IdentifyResponse> =
    settled[trackletId] ??
    (cached
      ? { status: 'ready', value: cached }
      : token === undefined
        ? { status: 'idle' }
        : { status: 'loading' })

  const request = () => {
    setSettled(({ [trackletId]: _dropped, ...rest }) => rest)
    setRequests((current) => ({ ...current, [trackletId]: (current[trackletId] ?? 0) + 1 }))
  }
  return { state, request }
}

/** The 8 M1 inputs of one candidate: value, oriented percentile, contribution. */
function RankingEvidence({ candidate }: { candidate: RankedCandidate }) {
  return (
    <details className="evidence" data-testid="ranking-evidence">
      <summary className="muted">M1 ranking evidence · 8 inputs</summary>
      <table className="detections">
        <thead>
          <tr>
            <th>input</th>
            <th title="earlier in review when the value is higher (↑) or lower (↓)">order</th>
            <th>value</th>
            <th title="oriented percentile in this build (higher = reviewed earlier)">pct</th>
            <th title="weight × percentile">contr.</th>
          </tr>
        </thead>
        <tbody>
          {candidate.evidence.map((e) => (
            <tr key={e.feature}>
              <td className="label" title={e.feature}>
                {featureLabel(e.feature)}
              </td>
              <td>{e.direction === 'higher_reviewed_first' ? '↑' : '↓'}</td>
              <td>{formatValue(e.value)}</td>
              <td>{e.percentile === null ? '—' : e.percentile.toFixed(2)}</td>
              <td>{e.contribution.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="label" colSpan={4}>
              priority score (Σ)
            </td>
            <td>{candidate.review_priority_score.toFixed(3)}</td>
          </tr>
        </tfoot>
      </table>
      <p className="muted small">
        Percentiles are within this build only. A missing value counts as 0.
        {candidate.sharp_availability !== 'complete' &&
          ` sharp: ${candidate.sharp_availability}.`}
      </p>
    </details>
  )
}

/** Details of the item under review, beside the blink viewer. */
export default function CandidatePanel({
  item,
  overlayVisible,
  onToggleOverlay,
  overlayErrors,
}: {
  item: ReviewItem
  overlayVisible: boolean
  onToggleOverlay: () => void
  overlayErrors: { epoch: number; message: string }[]
}) {
  const { tracklet, view } = item
  const identification = useOnDemandIdentification(tracklet.tracklet_id)

  return (
    <aside className="panel" data-testid="candidate-panel">
      <section>
        <h3>Review order</h3>
        {item.kind === 'ranked' ? (
          <>
            <dl className="facts">
              <dt>review rank</dt>
              <dd data-testid="candidate-rank">{item.candidate.review_rank}</dd>
              <dt>priority</dt>
              <dd data-testid="candidate-priority">
                {item.candidate.review_priority_score.toFixed(3)}{' '}
                <span className="muted">(M1 review priority)</span>
              </dd>
            </dl>
            <p className="muted small">
              Orders review only. Not a probability or confidence; an earlier rank does not make it
              more likely to be a real or new object.
            </p>
            <RankingEvidence candidate={item.candidate} />
          </>
        ) : (
          <p className="small" data-testid="unranked-reason">
            No M1 rank — {item.entry.reason}. Shown for completeness.
          </p>
        )}
      </section>

      <section>
        <h3>
          Tracklet
          <label className="toggle">
            <input type="checkbox" checked={overlayVisible} onChange={onToggleOverlay} /> overlay
          </label>
        </h3>
        <TrackletSummary
          tracklet={tracklet}
          productIds={view.product_ids}
          identification={identification.state}
        />
        {overlayErrors.map(({ epoch, message }) => (
          <p className="error" key={epoch}>
            No overlay on E{epoch + 1} — {message}
          </p>
        ))}
      </section>

      <section data-testid="identification">
        <h3>Identification · SkyBoT</h3>
        {identification.state.status === 'idle' ? (
          <>
            <button type="button" onClick={identification.request} data-testid="identify">
              Identify with SkyBoT
            </button>
            <p className="muted small">On request (live query). Context only, not an M1 input.</p>
          </>
        ) : (
          <IdentificationResult
            identification={identification.state}
            onRetry={identification.request}
          />
        )}
      </section>
    </aside>
  )
}
