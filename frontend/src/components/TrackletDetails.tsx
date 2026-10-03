import type { IdentifyResponse, Tracklet } from '../api/types'
import type { Async } from './trackletOverlay'

function utc(iso: string): string {
  return new Date(iso).toISOString().slice(11, 19)
}

/** Motion, fit and per-detection table of one tracklet (AS-030). */
export function TrackletSummary({
  tracklet,
  productIds,
  identification,
}: {
  tracklet: Tracklet
  productIds: number[]
  identification: Async<IdentifyResponse>
}) {
  const match = identification.status === 'ready' ? identification.value.identification : null
  const residualFor = (productId: number) =>
    match?.best_match?.residuals.find((r) => r.observation_product_id === productId)
      ?.residual_arcsec

  return (
    <>
      <dl className="facts" data-testid="tracklet-summary">
        <dt>id</dt>
        <dd data-testid="tracklet-id">{tracklet.tracklet_id}</dd>
        <dt>status</dt>
        <dd>
          {tracklet.status === 'tracklet_built' ? 'built' : 'rejected'}
          {tracklet.status_reason && ` (${tracklet.status_reason})`}
        </dd>
        <dt>detections</dt>
        <dd data-testid="tracklet-count">{tracklet.detections.length}</dd>
        <dt>speed</dt>
        <dd data-testid="tracklet-speed">
          {tracklet.angular_velocity_arcsec_per_min.toFixed(3)}″/min
        </dd>
        <dt>PA</dt>
        <dd data-testid="tracklet-pa">{tracklet.position_angle_deg.toFixed(1)}° E of N</dd>
        <dt>fit resid.</dt>
        <dd data-testid="tracklet-fit">
          rms {tracklet.fit_rms_residual_arcsec.toFixed(2)}″ · max{' '}
          {tracklet.fit_max_residual_arcsec.toFixed(2)}″
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
          {tracklet.detections.map(({ time, detection }) => {
            const residual = residualFor(detection.observation_product_id)
            return (
              <tr key={detection.source_id}>
                <td>E{productIds.indexOf(detection.observation_product_id) + 1}</td>
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
  )
}

/** SkyBoT identification result; a failure is an error, never 'unknown'. */
export function IdentificationResult({
  identification,
  onRetry,
}: {
  identification: Async<IdentifyResponse>
  onRetry: () => void
}) {
  const match = identification.status === 'ready' ? identification.value.identification : null
  return (
    <>
      {identification.status === 'loading' && <p className="muted">Querying SkyBoT…</p>}
      {identification.status === 'error' && (
        <p className="error" data-testid="identification-error">
          Identification failed — {identification.message}{' '}
          <button type="button" onClick={onRetry}>
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
              {match.best_match.object_class} · V {match.best_match.v_magnitude?.toFixed(1) ?? '—'}{' '}
              · residual rms {match.best_match.rms_residual_arcsec.toFixed(2)}″ · max{' '}
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
    </>
  )
}
