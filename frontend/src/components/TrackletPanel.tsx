import type { BlinkPreset, Tracklet } from '../api/types'
import { IdentificationResult, TrackletSummary } from './TrackletDetails'
import type { TrackletOverlayState } from './trackletOverlay'

function shortId(trackletId: string): string {
  return trackletId.split('.').pop() ?? trackletId
}

/** Compact tracklet summary and identification result (AS-030). */
export default function TrackletPanel({
  preset,
  state,
  overlayVisible,
  onToggleOverlay,
  onReview,
}: {
  preset: BlinkPreset
  state: TrackletOverlayState
  overlayVisible: boolean
  onToggleOverlay: () => void
  onReview: (buildId: string) => void
}) {
  const { build, inView, selectedId, identification } = state
  const selected: Tracklet | undefined =
    build.status === 'ready'
      ? build.value.tracklets.find((t) => t.tracklet_id === selectedId)
      : undefined

  return (
    <aside className="panel" data-testid="tracklet-panel">
      <section>
        <h3>
          Tracklet
          <label className="toggle">
            <input type="checkbox" checked={overlayVisible} onChange={onToggleOverlay} /> overlay
          </label>
        </h3>
        {build.status === 'idle' && (
          <>
            <button type="button" onClick={state.runBuild} data-testid="build-tracklets">
              Build tracklets
            </button>
            <p className="muted small">
              Runs the pipeline on these {preset.product_ids.length} frames (live IRSA PSF catalogs,
              experimental default config).
            </p>
          </>
        )}
        {build.status === 'loading' && <p className="muted">Building tracklets…</p>}
        {build.status === 'error' && (
          <p className="error">
            Build failed — {build.message}{' '}
            <button type="button" onClick={state.runBuild}>
              Retry
            </button>
          </p>
        )}
        {build.status === 'ready' && (
          <>
            <p className="muted small" data-testid="build-info">
              build {build.value.build_id} · {build.value.tracklets.length} tracklets ·{' '}
              {inView.length} in view
            </p>
            <button
              type="button"
              className="review-open"
              onClick={() => onReview(build.value.build_id)}
              data-testid="open-review"
            >
              Review all candidates in M1 order →
            </button>
            {inView.length > 1 && (
              <div className="track-list" role="group" aria-label="tracklets in view">
                {inView.map(({ tracklet }) => (
                  <button
                    key={tracklet.tracklet_id}
                    type="button"
                    className={tracklet.tracklet_id === selectedId ? 'epoch active' : 'epoch'}
                    onClick={() => state.select(tracklet.tracklet_id)}
                  >
                    {shortId(tracklet.tracklet_id)}
                  </button>
                ))}
              </div>
            )}
            {!selected && <p className="muted">No tracklet within this field of view.</p>}
            {state.projectionErrors.map(({ epoch, message }) => (
              <p className="error" key={epoch}>
                No overlay on E{epoch + 1} — {message}
              </p>
            ))}
          </>
        )}
        {selected && (
          <TrackletSummary
            tracklet={selected}
            productIds={preset.product_ids}
            identification={identification}
          />
        )}
      </section>

      {selected && (
        <section data-testid="identification">
          <h3>Identification · SkyBoT</h3>
          <IdentificationResult
            identification={identification}
            onRetry={state.retryIdentification}
          />
        </section>
      )}
    </aside>
  )
}
