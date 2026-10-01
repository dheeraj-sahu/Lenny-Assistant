/**
 * api/client.ts
 * Shared Axios-like fetch wrapper that prepends the API base URL.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body?.error?.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export { API_BASE }
