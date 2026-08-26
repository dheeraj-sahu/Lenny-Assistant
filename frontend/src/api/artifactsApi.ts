/**
 * api/artifactsApi.ts
 * Artifact fetch endpoints.
 */

import { apiFetch } from './client'

export interface Artifact {
  id: string
  session_id: string
  message_id: string | null
  artifact_type: 'markdown' | 'html'
  title: string | null
  sanitized_content: string
  created_at: string
}

export interface ArtifactListResponse {
  artifacts: Artifact[]
}

export const artifactsApi = {
  get: (id: string) => apiFetch<Artifact>(`/api/v1/artifacts/${id}`),

  listBySession: (sessionId: string) =>
    apiFetch<ArtifactListResponse>(`/api/v1/sessions/${sessionId}/artifacts`),
}
