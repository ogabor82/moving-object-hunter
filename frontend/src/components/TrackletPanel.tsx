import type { BlinkPreset, Tracklet } from '../api/types'
import type { TrackletOverlayState } from './trackletOverlay'

function utc(iso: string): string {
  return new Date(iso).toISOString().slice(11, 19)
}

function shortId(trackletId: string): string {
  return trackletId.split('.').pop() ?? trackletId
}

/** Compact tracklet summary and identification result (AS-030). */
export default function TrackletPanel({
  preset,
  state,
  overlayVisible,
  onToggleOverlay,
}: {
  preset: BlinkPreset
  state: TrackletOverlayState
  overlayVisible: boolean
  onToggleOverlay: () => void
}) {
  const { build, inView, selectedId, identification } = state
  const selected: Tracklet | undefined =
    build.status === 'ready'
      ? build.value.tracklets.find((t) => t.tracklet_id === selectedId)
      : undefined
  const match = identification.status === 'ready' ? identification.value.identification : null
  const residualFor = (productId: number) =>
    match?.best_match?.residuals.find((r) => r.observation_product_id === productId)
      ?.residual_arcsec

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
          <>
            <dl className="facts" data-testid="tracklet-summary">
              <dt>id</dt>
              <dd data-testid="tracklet-id">{selected.tracklet_id}</dd>
              <dt>status</dt>
              <dd>
                {selected.status === 'tracklet_built' ? 'built' : 'rejected'}
                {selected.status_reason && ` (${selected.status_reason})`}
              </dd>
              <dt>detections</dt>
              <dd data-testid="tracklet-count">{selected.detections.length}</dd>
              <dt>speed</dt>
              <dd data-testid="tracklet-speed">
                {selected.angular_velocity_arcsec_per_min.toFixed(3)}″/min
              </dd>
              <dt>PA</dt>
              <dd data-testid="tracklet-pa">{selected.position_angle_deg.toFixed(1)}° E of N</dd>
              <dt>fit resid.</dt>
              <dd data-testid="tracklet-fit">
                rms {selected.fit_rms_residual_arcsec.toFixed(2)}″ · max{' '}
                {selected.fit_max_residual_arcsec.toFixed(2)}″
              </dd>
            </dl>
            <table className="detections" data-testid="detection-table">
              <thead>
                <tr>
                  <th>ep</th>
                  <th>UT</th>
                  <th>mag</th>
                  <th>SNR</th>
                  <th title="observed − SkyBoT predicted">Δ id</th>
                </tr>
              </thead>
              <tbody>
                {selected.detections.map(({ time, detection }) => {
                  const residual = residualFor(detection.observation_product_id)
                  return (
                    <tr key={detection.source_id}>
                      <td>E{preset.product_ids.indexOf(detection.observation_product_id) + 1}</td>
                      <td>{utc(time)}</td>
                      <td>
                        {detection.magnitude.toFixed(2)}±{detection.magnitude_error.toFixed(2)}
                      </td>
                      <td>{detection.snr.toFixed(1)}</td>
                      <td>{residual === undefined ? '—' : `${residual.toFixed(2)}″`}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </>
        )}
      </section>

      {selected && (
        <section data-testid="identification">
          <h3>Identification · SkyBoT</h3>
          {identification.status === 'loading' && <p className="muted">Querying SkyBoT…</p>}
          {identification.status === 'error' && (
            <p className="error" data-testid="identification-error">
              Identification failed — {identification.message}{' '}
              <button type="button" onClick={state.retryIdentification}>
                Retry
              </button>
            </p>
          )}
          {match && (
            <>
              <p>
                <span className={`badge ${match.status}`} data-testid="identification-status">
                  {match.status}
                </span>{' '}
                {match.best_match && (
                  <strong data-testid="identification-object">
                    {match.best_match.designation}
                    {match.best_match.name !== match.best_match.designation &&
                      ` (${match.best_match.name})`}
                  </strong>
                )}
              </p>
              {match.best_match && (
                <p className="muted small" data-testid="identification-residual">
                  {match.best_match.object_class} · V{' '}
                  {match.best_match.v_magnitude?.toFixed(1) ?? '—'} · residual rms{' '}
                  {match.best_match.rms_residual_arcsec.toFixed(2)}″ · max{' '}
                  {match.best_match.max_residual_arcsec.toFixed(2)}″ · ephemeris ±
                  {match.best_match.position_error_arcsec.toFixed(2)}″
                </p>
              )}
              {match.status === 'ambiguous' && (
                <p className="small">
                  candidates:{' '}
                  {match.candidate_matches.map((m) => `${m.designation} ${m.name}`).join(', ')}
                </p>
              )}
              <p className="muted small">
                {match.status_reason}
                {match.status === 'unknown' && ' — unknown is not a discovery.'}
              </p>
            </>
          )}
        </section>
      )}
    </aside>
  )
}
