import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import * as client from '../api/client'
import type { FrameCutoutParams, SkyPosition } from '../api/types'
import { cutout, ranking } from '../test/fixtures'
import ReviewWorkspace from './ReviewWorkspace'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  getReviewRanking: vi.fn(),
  getFrameCutout: vi.fn(),
  projectPositions: vi.fn(),
  identifyTracklet: vi.fn(),
}))

const getReviewRanking = vi.mocked(client.getReviewRanking)
const getFrameCutout = vi.mocked(client.getFrameCutout)
const projectPositions = vi.mocked(client.projectPositions)
const identifyTracklet = vi.mocked(client.identifyTracklet)

// Session caches are module-level: each test uses its own build id.
let seq = 0
function buildId(): string {
  seq += 1
  return `build${seq}`
}

beforeEach(() => {
  vi.clearAllMocks()
  getFrameCutout.mockImplementation(async (params: FrameCutoutParams) => cutout(params))
  projectPositions.mockImplementation(async (params: FrameCutoutParams, positions: SkyPosition[]) => ({
    product_id: params.product_id,
    width: 2,
    height: 2,
    center_x: 0.5,
    center_y: 0.5,
    points: positions.map(() => ({ x: 0.5, y: 0.5 })),
  }))
})

function position(): string {
  return screen.getByTestId('review-position').textContent ?? ''
}

async function renderReady(count: number, rejected = 0, shuffle = false) {
  const id = buildId()
  const data = ranking(id, count, rejected, shuffle)
  getReviewRanking.mockResolvedValueOnce(data)
  render(<ReviewWorkspace buildId={id} />)
  await screen.findByTestId('review-workspace')
  // The ranking resolved outside act(): flush effects (key listeners).
  await act(async () => undefined)
  return { id, data }
}

function cutoutRequests(): FrameCutoutParams[] {
  return getFrameCutout.mock.calls.map(([params]) => params)
}

describe('ReviewWorkspace states', () => {
  it('shows loading, then the queue', async () => {
    const id = buildId()
    let resolve!: (value: ReturnType<typeof ranking>) => void
    getReviewRanking.mockReturnValueOnce(new Promise((r) => (resolve = r)))
    render(<ReviewWorkspace buildId={id} />)
    expect(screen.getByTestId('review-loading')).toHaveTextContent(`build ${id}`)
    await act(async () => resolve(ranking(id, 2)))
    expect(screen.getByTestId('review-workspace')).toBeInTheDocument()
    expect(getReviewRanking).toHaveBeenCalledWith(id)
  })

  it('shows an API error with a retry', async () => {
    const id = buildId()
    getReviewRanking.mockRejectedValueOnce(new ApiError(404, 'BUILD_NOT_FOUND', 'Build gone'))
    render(<ReviewWorkspace buildId={id} />)
    const error = await screen.findByTestId('review-error')
    expect(error).toHaveTextContent('BUILD_NOT_FOUND: Build gone')
    getReviewRanking.mockResolvedValueOnce(ranking(id, 1))
    fireEvent.click(within(error).getByRole('button', { name: 'Retry' }))
    await screen.findByTestId('review-workspace')
    expect(position()).toBe('Candidate 1 / 1')
  })

  it('handles an empty build', async () => {
    await renderReady(0, 0)
    expect(screen.getByTestId('review-empty')).toHaveTextContent('no tracklets')
    expect(screen.queryByTestId('review-position')).toBeNull()
  })

  it('opens the unranked list when no tracklet is ranked', async () => {
    await renderReady(0, 2)
    expect(screen.getByTestId('review-empty')).toHaveTextContent('No built tracklet to rank')
    expect(position()).toBe('Unranked 1 / 2')
  })
})

describe('ranked queue', () => {
  it('lists every candidate in M1 order with a position', async () => {
    await renderReady(5, 0, true)
    const rows = screen.getAllByTestId('ranked-row')
    expect(rows.map((row) => row.querySelector('.queue-rank')?.textContent)).toEqual([
      '#1',
      '#2',
      '#3',
      '#4',
      '#5',
    ])
    expect(screen.getByTestId('candidate-count')).toHaveTextContent('5')
    expect(position()).toBe('Candidate 1 / 5')
    expect(rows[0]).toHaveAttribute('aria-current', 'true')
  })

  it('keeps the whole list reachable: no top-N or score cut', async () => {
    await renderReady(250)
    expect(screen.getAllByTestId('ranked-row')).toHaveLength(250)
    const next = screen.getByRole('button', { name: 'next candidate' })
    for (let i = 0; i < 249; i++) fireEvent.click(next)
    expect(position()).toBe('Candidate 250 / 250')
    expect(screen.getByTestId('review-heading')).toHaveTextContent('#250')
    expect(next).toBeDisabled()
  })

  it('selects a candidate from the list and steps with Previous / Next', async () => {
    const { id } = await renderReady(4)
    const previous = screen.getByRole('button', { name: 'previous candidate' })
    expect(previous).toBeDisabled()
    fireEvent.click(screen.getAllByTestId('ranked-row')[2])
    expect(position()).toBe('Candidate 3 / 4')
    expect(screen.getByTestId('tracklet-id')).toHaveTextContent(`${id}.t3`)
    expect(screen.getByTestId('candidate-rank')).toHaveTextContent('3')
    fireEvent.click(previous)
    expect(position()).toBe('Candidate 2 / 4')
    fireEvent.click(screen.getByRole('button', { name: 'next candidate' }))
    fireEvent.click(screen.getByRole('button', { name: 'next candidate' }))
    expect(position()).toBe('Candidate 4 / 4')
    expect(screen.getAllByTestId('ranked-row')[3]).toHaveAttribute('aria-current', 'true')
  })

  it('supports n / p and ↓ / ↑ keys, leaving ← / → to the frames', async () => {
    await renderReady(3)
    fireEvent.keyDown(window, { key: 'n' })
    expect(position()).toBe('Candidate 2 / 3')
    fireEvent.keyDown(window, { key: 'ArrowDown' })
    expect(position()).toBe('Candidate 3 / 3')
    fireEvent.keyDown(window, { key: 'p' })
    expect(position()).toBe('Candidate 2 / 3')
    fireEvent.keyDown(window, { key: 'ArrowUp' })
    expect(position()).toBe('Candidate 1 / 3')
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(position()).toBe('Candidate 1 / 3')
    expect(screen.getByTestId('frame-info')).toHaveTextContent('FRAME 2/3')
  })
})

describe('blink / overlay integration', () => {
  it("loads the selected candidate's view frames and projects its detections", async () => {
    const { id, data } = await renderReady(3)
    const [first, second] = data.candidates
    await waitFor(() => expect(screen.getByTestId('frames-loaded')).toHaveTextContent('3/3'))
    for (const productId of first.view.product_ids) {
      expect(cutoutRequests()).toContainEqual({
        product_id: productId,
        ra: first.view.center_ra,
        dec: first.view.center_dec,
        size_arcsec: first.view.size_arcsec,
      })
    }
    await waitFor(() => expect(projectPositions).toHaveBeenCalledTimes(3))
    expect(projectPositions.mock.calls[0][1]).toEqual(
      first.tracklet.detections.map(({ detection }) => ({ ra: detection.ra, dec: detection.dec })),
    )

    fireEvent.click(screen.getByRole('button', { name: 'next candidate' }))
    expect(screen.getByTestId('tracklet-id')).toHaveTextContent(`${id}.t2`)
    await waitFor(() =>
      expect(cutoutRequests()).toContainEqual({
        product_id: second.view.product_ids[2],
        ra: second.view.center_ra,
        dec: second.view.center_dec,
        size_arcsec: second.view.size_arcsec,
      }),
    )
    await waitFor(() => expect(screen.getByTestId('frames-loaded')).toHaveTextContent('3/3'))
  })

  it('does not download the frames of candidates skipped quickly', async () => {
    const { data } = await renderReady(6)
    for (let i = 0; i < 3; i++) fireEvent.keyDown(window, { key: 'n' })
    expect(position()).toBe('Candidate 4 / 6')
    const [, second, third, fourth] = data.candidates
    await waitFor(() => expect(screen.getByTestId('frames-loaded')).toHaveTextContent('3/3'))
    const centres = cutoutRequests().map((p) => p.ra)
    expect(centres).toContain(fourth.view.center_ra)
    expect(centres).not.toContain(second.view.center_ra)
    expect(centres).not.toContain(third.view.center_ra)
  })

  it('shows a failed frame as a frame error, not as an invalid candidate', async () => {
    getFrameCutout.mockRejectedValue(new ApiError(502, 'CUTOUT_FAILED', 'IRSA down'))
    await renderReady(2)
    const error = await screen.findByTestId('frame-error')
    expect(error).toHaveTextContent('Frame 1 failed — CUTOUT_FAILED: IRSA down')
    expect(within(error).getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(position()).toBe('Candidate 1 / 2')
    expect(screen.getByTestId('candidate-rank')).toHaveTextContent('1')
  })

  it('queries SkyBoT only on request', async () => {
    const { id } = await renderReady(3)
    fireEvent.click(screen.getByRole('button', { name: 'next candidate' }))
    expect(identifyTracklet).not.toHaveBeenCalled()
    identifyTracklet.mockRejectedValueOnce(new ApiError(502, 'SKYBOT_FAILED', 'timeout'))
    fireEvent.click(screen.getByTestId('identify'))
    expect(identifyTracklet).toHaveBeenCalledWith(`${id}.t2`)
    expect(await screen.findByTestId('identification-error')).toHaveTextContent('SKYBOT_FAILED')
  })
})

describe('semantics', () => {
  it('labels the score as review priority, never as probability or a verdict', async () => {
    await renderReady(3)
    for (const row of screen.getAllByTestId('ranked-row')) {
      expect(row).toHaveTextContent(/prio \d\.\d{3}/)
      expect(row.textContent).not.toMatch(/probab|confiden|likel|good|real|asteroid|%/i)
    }
    expect(screen.getByTestId('review-semantics')).toHaveTextContent(
      'the priority score is not a probability or confidence',
    )
    expect(screen.getByTestId('candidate-priority')).toHaveTextContent('(M1 review priority)')
    expect(screen.getByTestId('candidate-panel')).toHaveTextContent(
      'Not a probability or confidence',
    )
  })

  it('keeps detailed M1 evidence collapsed but inspectable', async () => {
    await renderReady(2)
    const evidence = screen.getByTestId('ranking-evidence')
    expect(evidence).not.toHaveAttribute('open')
    expect(within(evidence).getAllByRole('row')).toHaveLength(1 + 8 + 1)
    expect(evidence).toHaveTextContent('max |sharp|')
    expect(evidence).toHaveTextContent('missing')
  })
})

describe('unranked tracklets', () => {
  it('are listed separately with the reason and can be opened', async () => {
    const { id } = await renderReady(3, 2)
    const section = screen.getByTestId('unranked-section')
    expect(screen.getByTestId('unranked-count')).toHaveTextContent('2')
    expect(section).toHaveTextContent('failed the earlier fit/build criterion')
    expect(screen.getAllByTestId('ranked-row')).toHaveLength(3)

    fireEvent.click(within(section).getAllByTestId('unranked-row')[1])
    expect(position()).toBe('Unranked 2 / 2')
    expect(screen.getByTestId('unranked-reason')).toHaveTextContent('No M1 rank')
    expect(screen.getByTestId('tracklet-id')).toHaveTextContent(`${id}.r2`)
    expect(screen.queryByTestId('candidate-rank')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'previous candidate' }))
    expect(position()).toBe('Unranked 1 / 2')

    fireEvent.click(screen.getAllByTestId('ranked-row')[0])
    expect(position()).toBe('Candidate 1 / 3')
  })
})
