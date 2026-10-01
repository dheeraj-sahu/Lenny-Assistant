/**
 * api/sessionsApi.ts
 * Sessions CRUD — create, list, get, delete.
 * Also exports configApi for provider/model configuration.
 */

import { apiFetch } from './client'

export interface Session {
  id: string
  title: string | null
  active_provider: string
  created_at: string
  updated_at: string
}

export interface SessionListResponse {
  sessions: Session[]
  total: number
}

export const sessionsApi = {
  create: (title?: string) =>
    apiFetch<Session>('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: title ?? null }),
    }),

  list: () => apiFetch<SessionListResponse>('/api/v1/sessions'),

  get: (id: string) => apiFetch<Session>(`/api/v1/sessions/${id}`),

  delete: (id: string) =>
    apiFetch<void>(`/api/v1/sessions/${id}`, { method: 'DELETE' }),
}

export interface ConfigResponse {
  provider: string
  model: string
  provider_label: string
  embedding_model: string
  environment: string
  corpus_version?: string
  chunk_count?: number
  ollama_model?: string
  anthropic_model?: string
}

export const configApi = {
  get: () => apiFetch<ConfigResponse>('/config'),

  /** Switch the active LLM provider at runtime (writes to backend session state). */
  switchProvider: (provider: 'ollama' | 'anthropic', apiKey?: string) =>
    apiFetch<ConfigResponse>('/config/provider', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey ?? null }),
    }),
}
