// Types mirroring the backend response models (backend/app/models,
// backend/app/api/routes). Keep in sync when the API changes.

export interface HealthResponse {
  status: string
}

/** Domain error body: {"error": {"code", "message"}} */
export interface ApiErrorBody {
  error: { code: string; message: string }
}

export interface Observation {
  product_id: number
  observed_at: string
  field: number
  filter_code: string
  ccd_id: number
  quadrant_id: number
  file_frac_day: string
  exposure_seconds: number | null
}

export interface ObservationSearchParams {
  ra: number
  dec: number
  radius_deg: number
  start_time: string
  end_time: string
}

export interface ObservationSearchResponse extends ObservationSearchParams {
  count: number
  observations: Observation[]
}

/** Experimental, not calibrated defaults are applied when omitted. */
export interface PipelineConfig {
  stationary_tolerance_arcsec: number
  max_rate_arcsec_per_min: number
  search_radius_arcsec: number
  max_residual_arcsec: number
  match_radius_arcsec: number
}

export interface SourceDetection {
  source_id: string
  observation_product_id: number
  ra: number
  dec: number
  x: number
  y: number
  magnitude: number
  magnitude_error: number
  snr: number
  on_image_edge: boolean
  mask_bits: number
}

export interface TrackletDetection {
  time: string
  detection: SourceDetection
}

export type TrackletStatus = 'tracklet_built' | 'rejected'

export interface Tracklet {
  tracklet_id: string
  detections: TrackletDetection[]
  angular_velocity_arcsec_per_min: number
  position_angle_deg: number
  fit_rms_residual_arcsec: number
  fit_max_residual_arcsec: number
  status: TrackletStatus
  status_reason: string | null
}

export interface TrackletBuildDiagnostics {
  frame_count: number
  candidate_counts: number[]
  seed_pairs: number
  linked_before_dedup: number
  duplicates_removed: number
  subsets_removed: number
  ambiguous_extensions: number
  tracklet_count: number
  rejected_tracklet_count: number
  detections_in_multiple_tracklets: number
}

export interface TrackletBuildRequest {
  observation_ids: number[]
  config?: PipelineConfig
}

export interface TrackletBuildResponse {
  build_id: string
  config: PipelineConfig
  observations: Observation[]
  source_counts: number[]
  candidate_counts: number[]
  diagnostics: TrackletBuildDiagnostics
  tracklets: Tracklet[]
}

/** 'unknown' means no known object matched; it is not a discovery. */
export type IdentificationStatus = 'known' | 'unknown' | 'ambiguous'

export interface DetectionResidual {
  observation_product_id: number
  epoch_jd_utc: number
  observed_ra: number
  observed_dec: number
  predicted_ra: number
  predicted_dec: number
  residual_arcsec: number
}

export interface KnownObjectMatch {
  designation: string
  name: string
  object_class: string
  v_magnitude: number | null
  position_error_arcsec: number
  residuals: DetectionResidual[]
  rms_residual_arcsec: number
  max_residual_arcsec: number
}

export interface TrackletIdentification {
  tracklet_id: string
  tracklet_status: TrackletStatus
  status: IdentificationStatus
  status_reason: string
  best_match: KnownObjectMatch | null
  candidate_matches: KnownObjectMatch[]
}

export interface KnownObjectEphemeris {
  designation: string
  number: number | null
  name: string
  object_class: string
  predicted_ra: number
  predicted_dec: number
  v_magnitude: number | null
  position_error_arcsec: number
  distance_from_field_center_arcsec: number
  motion_ra_cos_dec_arcsec_per_hour: number
  motion_dec_arcsec_per_hour: number
  observer_distance_au: number | null
  heliocentric_distance_au: number | null
}

export interface KnownObjectField {
  epoch_jd_utc: number
  field_ra: number
  field_dec: number
  field_radius_degrees: number
  observer: string
  objects: KnownObjectEphemeris[]
  rejected_rows: { row_index: number; reason: string }[]
}

export interface IdentifyResponse {
  tracklet_id: string
  config: { match_radius_arcsec: number }
  identification: TrackletIdentification
  skybot_fields: KnownObjectField[]
}

/** A frozen validation frame sequence (backend: app/validation/presets). */
export interface BlinkPreset {
  preset_id: string
  label: string
  designation: string
  name: string
  role: 'control' | 'primary'
  v_magnitude: number
  predicted_rate_arcsec_per_min: number
  field_id: string
  product_ids: number[]
  center_ra: number
  center_dec: number
  size_arcsec: number
}

export interface FrameCutoutParams {
  product_id: number
  ra: number
  dec: number
  size_arcsec: number
}

/**
 * One ZTF science-frame cutout as an 8-bit display image. `pixels_base64`
 * holds width*height bytes, row-major, row 0 at the top, north up and east
 * left. (center_x, center_y) is the requested sky position in pixels.
 */
export interface FrameCutoutResponse {
  observation: Observation
  ra: number
  dec: number
  size_arcsec: number
  width: number
  height: number
  pixel_scale_arcsec: number
  center_x: number
  center_y: number
  orientation: 'north_up_east_left'
  rotation_deg: number
  transform: string[]
  stretch: { method: 'zscale_linear'; vmin: number; vmax: number }
  pixels_base64: string
}

export interface SkyPosition {
  ra: number
  dec: number
}

/** Display pixel: 0-based (column, row) of the cutout, pixel centres at integers. */
export interface DisplayPoint {
  x: number
  y: number
}

export interface ProjectResponse {
  product_id: number
  width: number
  height: number
  center_x: number
  center_y: number
  points: (DisplayPoint | null)[]
}
