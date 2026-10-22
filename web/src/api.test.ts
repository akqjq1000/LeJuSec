import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from './api'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('fetches /summary and returns json', async () => {
    const payload = { assets_total: 2, checks_fail: 1 }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => payload }) as unknown as Response),
    )
    const result = await api.summary()
    expect(result.assets_total).toBe(2)
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/summary'))
  })

  it('throws on non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 500, statusText: 'err' }) as unknown as Response),
    )
    await expect(api.assets()).rejects.toThrow('500')
  })
})
