import type {
  ApiErrorBody,
  BlinkPreset,
  FrameCutoutParams,
  FrameCutoutResponse,
  HealthResponse,
  IdentifyResponse,
  ObservationSearchParams,
  ObservationSearchResponse,
  TrackletBuildRequest,
  TrackletBuildResponse,
} from './types'

const API_BASE = '/api'

/** A failed API call: HTTP status plus the backend error code if any. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init?.headers },
    })
  } catch (error) {
    throw new ApiError(0, 'NETWORK_ERROR', `Backend not reachable: ${String(error)}`)
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw toApiError(response.status, body)
  }
  return body as T
}

function toApiError(status: number, body: unknown): ApiError {
  if (isErrorBody(body)) {
    return new ApiError(status, body.error.code, body.error.message)
  }
  if (body && typeof body === 'object' && 'detail' in body) {
    // FastAPI request validation error (422).
    return new ApiError(status, 'VALIDATION_ERROR', JSON.stringify(body.detail))
  }
  return new ApiError(status, 'HTTP_ERROR', `HTTP ${status}`)
}

function isErrorBody(body: unknown): body is ApiErrorBody {
  return (
    typeof body === 'object' &&
    body !== null &&
    'error' in body &&
    typeof (body as ApiErrorBody).error?.code === 'string'
  )
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export function searchObservations(
  params: ObservationSearchParams,
): Promise<ObservationSearchResponse> {
  const query = new URLSearchParams({
    ra: String(params.ra),
    dec: String(params.dec),
    radius_deg: String(params.radius_deg),
    start_time: params.start_time,
    end_time: params.end_time,
  })
  return request<ObservationSearchResponse>(`/observations/search?${query}`)
}

export function buildTracklets(
  body: TrackletBuildRequest,
): Promise<TrackletBuildResponse> {
  return request<TrackletBuildResponse>('/tracklets/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function identifyTracklet(
  trackletId: string,
  matchRadiusArcsec?: number,
): Promise<IdentifyResponse> {
  return request<IdentifyResponse>(
    `/tracklets/${encodeURIComponent(trackletId)}/identify`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(
        matchRadiusArcsec === undefined
          ? {}
          : { match_radius_arcsec: matchRadiusArcsec },
      ),
    },
  )
}

export function getFramePresets(): Promise<BlinkPreset[]> {
  return request<BlinkPreset[]>('/frames/presets')
}

export function getFrameCutout(
  params: FrameCutoutParams,
  signal?: AbortSignal,
): Promise<FrameCutoutResponse> {
  const query = new URLSearchParams({
    product_id: String(params.product_id),
    ra: String(params.ra),
    dec: String(params.dec),
    size_arcsec: String(params.size_arcsec),
  })
  return request<FrameCutoutResponse>(`/frames/cutout?${query}`, { signal })
}
