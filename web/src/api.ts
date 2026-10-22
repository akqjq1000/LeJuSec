export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

const TOKEN_KEY = 'lejusec_token'

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setToken(token: string): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    /* localStorage 불가 시 무시 */
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: authHeaders() })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ''}`)
  }
  return (await res.json()) as T
}

export interface Summary {
  assets_total: number
  assets_managed: number
  checks_pass: number
  checks_fail: number
  checks_na: number
  remediations_open: number
  integrity_high_critical: number
}

export interface Asset {
  id: number
  hostname: string
  os: string
  os_version: string
  role: string
  managed: boolean
  agent_status: string
  public_key: string
  last_scan_at: string | null
  created_at: string
}

export interface InventorySummary {
  package_count: number
  process_count: number
  captured_at: string | null
}

export interface CheckResult {
  check_id: string
  standard: string
  title: string
  severity: string
  status: string
  reason: string
  evidence: string[]
}

export interface IntegrityEvent {
  path: string
  change_type: string
  severity: string
  detail: string
  created_at: string
}

export interface Remediation {
  id: number
  check_id: string
  title: string
  script: string
  rollback: string
  status: string
  static_ok: boolean
  static_notes: string
  verified: boolean
  verify_notes: string
}

export interface CheckItem {
  id: string
  standard: string
  title: string
  severity: string
  rationale: string
}

export interface CheckHit {
  item: CheckItem
  score: number
}

export interface GenerateAck {
  generated: number
  proposed: Remediation[]
}

export interface VerifyResult {
  ok: boolean
  notes: string
  sandbox: string
}

export interface Me {
  role: string
  auth: string
}

export const api = {
  me: () => get<Me>('/me'),
  summary: () => get<Summary>('/summary'),
  assets: () => get<Asset[]>('/assets'),
  asset: (id: number) => get<Asset>(`/assets/${id}`),
  inventory: (id: number) => get<InventorySummary>(`/assets/${id}/inventory`),
  results: (id: number) => get<CheckResult[]>(`/assets/${id}/results`),
  integrity: (id: number) => get<IntegrityEvent[]>(`/assets/${id}/integrity/events`),
  remediations: (id: number) => get<Remediation[]>(`/assets/${id}/remediations`),
  // 점검 기준 · RAG 근거 (G3)
  checks: () => get<CheckItem[]>('/checks'),
  checksSearch: (q: string) => get<CheckHit[]>(`/checks/search?q=${encodeURIComponent(q)}`),
  // HITL 조치 변이 (G2)
  generateRemediations: (id: number) => post<GenerateAck>(`/assets/${id}/remediations`),
  verifyRemediation: (rid: number) => post<VerifyResult>(`/remediations/${rid}/verify`),
  approveRemediation: (rid: number) => post<Remediation>(`/remediations/${rid}/approve`),
  rejectRemediation: (rid: number) => post<Remediation>(`/remediations/${rid}/reject`),
}
