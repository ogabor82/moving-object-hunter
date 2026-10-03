import { describe, expect, it } from 'vitest'
import { ranking } from '../test/fixtures'
import { initialSelection, reviewOrder, shortId, stepSelection } from './reviewQueue'

describe('reviewOrder', () => {
  it('keeps every candidate, rank 1 first, without changing the M1 order', () => {
    const shuffled = ranking('b', 6, 0, true).candidates
    const ordered = reviewOrder(shuffled)
    expect(ordered.map((c) => c.review_rank)).toEqual([1, 2, 3, 4, 5, 6])
    expect(ordered).toHaveLength(shuffled.length)
    // Scores fall along the order; nothing is cut at any score.
    const scores = ordered.map((c) => c.review_priority_score)
    expect([...scores].sort((a, b) => b - a)).toEqual(scores)
  })

  it('does not mutate the API list', () => {
    const shuffled = ranking('b', 3, 0, true).candidates
    reviewOrder(shuffled)
    expect(shuffled.map((c) => c.review_rank)).toEqual([3, 2, 1])
  })
})

describe('stepSelection', () => {
  it('moves one item and stops at either end (no wrap)', () => {
    expect(stepSelection({ queue: 'ranked', index: 0 }, -1, 5)).toEqual({ queue: 'ranked', index: 0 })
    expect(stepSelection({ queue: 'ranked', index: 0 }, 1, 5)).toEqual({ queue: 'ranked', index: 1 })
    expect(stepSelection({ queue: 'ranked', index: 4 }, 1, 5)).toEqual({ queue: 'ranked', index: 4 })
    expect(stepSelection({ queue: 'unranked', index: 1 }, -1, 2)).toEqual({
      queue: 'unranked',
      index: 0,
    })
  })
})

describe('initialSelection', () => {
  it('starts at rank 1, else at the first unranked tracklet, else nothing', () => {
    expect(initialSelection(ranking('b', 3, 1))).toEqual({ queue: 'ranked', index: 0 })
    expect(initialSelection(ranking('b', 0, 2))).toEqual({ queue: 'unranked', index: 0 })
    expect(initialSelection(ranking('b', 0, 0))).toBeNull()
  })
})

it('shortId drops the build prefix', () => {
  expect(shortId('abc123.t0042')).toBe('t0042')
})
