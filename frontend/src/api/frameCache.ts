import { getFrameCutout } from './client'
import { SessionCache } from './sessionCache'
import type { FrameCutoutParams, FrameCutoutResponse } from './types'

/** A cutout plus its decoded bitmap, ready to draw. */
export interface LoadedFrame {
  data: FrameCutoutResponse
  bitmap: HTMLCanvasElement
}

// Every cutout is requested at most once per page load.
const frames = new SessionCache<LoadedFrame>()

export function frameKey(params: FrameCutoutParams): string {
  return [params.product_id, params.ra, params.dec, params.size_arcsec].join('|')
}

/** Grey 8-bit pixels (row 0 = north) → an offscreen canvas at native size. */
function toBitmap(frame: FrameCutoutResponse): HTMLCanvasElement {
  const bytes = Uint8Array.from(atob(frame.pixels_base64), (c) => c.charCodeAt(0))
  const rgba = new Uint8ClampedArray(frame.width * frame.height * 4)
  for (let i = 0; i < bytes.length; i++) {
    rgba[i * 4] = bytes[i]
    rgba[i * 4 + 1] = bytes[i]
    rgba[i * 4 + 2] = bytes[i]
    rgba[i * 4 + 3] = 255
  }
  const canvas = document.createElement('canvas')
  canvas.width = frame.width
  canvas.height = frame.height
  canvas.getContext('2d')?.putImageData(new ImageData(rgba, frame.width, frame.height), 0, 0)
  return canvas
}

/** An already loaded frame, without any request. */
export function cachedFrame(params: FrameCutoutParams): LoadedFrame | undefined {
  return frames.get(frameKey(params))
}

/**
 * Load one frame, sharing in-flight requests and remembering results.
 * Requests are not aborted when the viewer changes sequence: they finish in
 * the background and warm the cache.
 */
export function loadFrame(params: FrameCutoutParams): Promise<LoadedFrame> {
  return frames.load(frameKey(params), () =>
    getFrameCutout(params).then((data) => ({ data, bitmap: toBitmap(data) })),
  )
}
