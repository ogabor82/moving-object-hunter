import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as client from './api/client'
import type { BlinkPreset, FrameCutoutParams, SkyPosition } from './api/types'
import App from './App'
import { cutout, PRODUCT_IDS, ranking, tracklet } from './test/fixtures'

vi.mock('./api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api/client')>()),
  getHealth: vi.fn(),
  getFramePresets: vi.fn(),
  getFrameCutout: vi.fn(),
  projectPositions: vi.fn(),
  buildTracklets: vi.fn(),
  getReviewRanking: vi.fn(),
  identifyTracklet: vi.fn(),
}))

const preset: BlinkPreset = {
  preset_id: 'p1',
  label: '48606 1995 DH',
  designation: '48606',
  name: '1995 DH',
  role: 'control',
  v_magnitude: 17.5,
  predicted_rate_arcsec_per_min: 0.4,
  field_id: 'ztf-0001-c01-q1-20190401',
  product_ids: PRODUCT_IDS,
  center_ra: 150,
  center_dec: 20,
  size_arcsec: 60,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(client.getHealth).mockResolvedValue({ status: 'ok' })
  vi.mocked(client.getFramePresets).mockResolvedValue([preset])
  vi.mocked(client.getFrameCutout).mockImplementation(async (params: FrameCutoutParams) =>
    cutout(params),
  )
  vi.mocked(client.projectPositions).mockImplementation(
    async (params: FrameCutoutParams, positions: SkyPosition[]) => ({
      product_id: params.product_id,
      width: 2,
      height: 2,
      center_x: 0.5,
      center_y: 0.5,
      points: positions.map(() => ({ x: 0.5, y: 0.5 })),
    }),
  )
  // The preset panel identifies its tracklet at once; keep SkyBoT pending.
  vi.mocked(client.identifyTracklet).mockReturnValue(new Promise(() => undefined))
})

it('opens the ranked review from a finished build and returns to the sequences', async () => {
  vi.mocked(client.buildTracklets).mockResolvedValue({
    build_id: 'abc123',
    config: ranking('abc123', 0).config,
    observations: [],
    source_counts: [],
    candidate_counts: [],
    diagnostics: {
      frame_count: 3,
      candidate_counts: [],
      seed_pairs: 0,
      linked_before_dedup: 1,
      duplicates_removed: 0,
      subsets_removed: 0,
      ambiguous_extensions: 0,
      tracklet_count: 1,
      rejected_tracklet_count: 0,
      detections_in_multiple_tracklets: 0,
    },
    tracklets: [tracklet('abc123.t0')],
  })
  vi.mocked(client.getReviewRanking).mockResolvedValue(ranking('abc123', 4, 1))

  render(<App />)
  // The preset blink comparator still works as before.
  await waitFor(() => expect(screen.getByTestId('frames-loaded')).toHaveTextContent('3/3'))
  fireEvent.click(screen.getByTestId('build-tracklets'))
  fireEvent.click(await screen.findByTestId('open-review'))

  await screen.findByTestId('review-workspace')
  expect(window.location.hash).toBe('#review=abc123')
  expect(client.getReviewRanking).toHaveBeenCalledWith('abc123')
  expect(screen.getByTestId('review-position')).toHaveTextContent('Candidate 1 / 4')

  fireEvent.click(screen.getByTestId('leave-review'))
  await screen.findByTestId('tracklet-panel')
})

it('opens a build id typed in the sidebar', async () => {
  vi.mocked(client.getReviewRanking).mockResolvedValue(ranking('typed1', 2))
  render(<App />)
  fireEvent.change(await screen.findByLabelText('build id'), { target: { value: ' typed1 ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Open' }))
  await screen.findByTestId('review-workspace')
  expect(client.getReviewRanking).toHaveBeenCalledWith('typed1')
})
