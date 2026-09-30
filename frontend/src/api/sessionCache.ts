/**
 * Per-page-load memo of async results: one request per key, shared while in
 * flight, remembered once resolved. Failures are dropped so a retry asks
 * the backend again.
 */
export class SessionCache<T> {
  private readonly pending = new Map<string, Promise<T>>()
  private readonly loaded = new Map<string, T>()

  get(key: string): T | undefined {
    return this.loaded.get(key)
  }

  load(key: string, fetcher: () => Promise<T>): Promise<T> {
    const done = this.loaded.get(key)
    if (done !== undefined) return Promise.resolve(done)
    let request = this.pending.get(key)
    if (!request) {
      request = fetcher()
        .then((value) => {
          this.loaded.set(key, value)
          return value
        })
        .finally(() => this.pending.delete(key))
      this.pending.set(key, request)
    }
    return request
  }
}
