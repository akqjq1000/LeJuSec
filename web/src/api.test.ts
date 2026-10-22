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

  it('approveRemediation POSTs to the approve path', async () => {
    const fetchMock = vi.fn(
      async () => ({ ok: true, json: async () => ({ id: 1, status: 'approved' }) }) as unknown as Response,
    )
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.approveRemediation(1)
    expect(result.status).toBe('approved')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/remediations/1/approve'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('surfaces 409 detail on unsafe approve', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 409,
            statusText: 'Conflict',
            text: async () => 'unsafe remediation cannot be approved',
          }) as unknown as Response,
      ),
    )
    await expect(api.approveRemediation(1)).rejects.toThrow('409')
  })
})
