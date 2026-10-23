import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, setToken } from './api'

afterEach(() => {
  vi.restoreAllMocks()
  setToken('')
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
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/summary'), expect.anything())
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

  it('checksSearch encodes the query', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => [] }) as unknown as Response)
    vi.stubGlobal('fetch', fetchMock)
    await api.checksSearch('root SSH 접속')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/checks/search?q=root%20SSH'),
      expect.anything(),
    )
  })

  it('sends Authorization header when a token is set', async () => {
    setToken('tok123')
    const fetchMock = vi.fn(
      async () => ({ ok: true, json: async () => ({ role: 'admin', auth: 'enabled' }) }) as unknown as Response,
    )
    vi.stubGlobal('fetch', fetchMock)
    await api.me()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/me'),
      expect.objectContaining({ headers: { Authorization: 'Bearer tok123' } }),
    )
  })

  it('registerAsset POSTs a JSON body to /assets', async () => {
    const fetchMock = vi.fn(
      async () => ({ ok: true, json: async () => ({ id: 5, hostname: 'h1' }) }) as unknown as Response,
    )
    vi.stubGlobal('fetch', fetchMock)
    await api.registerAsset({ hostname: 'h1', os: 'ubuntu', os_version: '26.04', role: 'test' })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/assets'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ hostname: 'h1', os: 'ubuntu', os_version: '26.04', role: 'test' }),
      }),
    )
  })

  it('requestScan POSTs to the scan-requests path', async () => {
    const fetchMock = vi.fn(
      async () => ({ ok: true, json: async () => ({ id: 1, kind: 'scan', status: 'pending' }) }) as unknown as Response,
    )
    vi.stubGlobal('fetch', fetchMock)
    const cmd = await api.requestScan(3)
    expect(cmd.kind).toBe('scan')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/assets/3/scan-requests'),
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
