/**
 * api/messagesApi.ts
 * Message list and SSE streaming.
 */

import { apiFetch, API_BASE } from './client'

export interface SourceCitation {
  episode_slug: string
  guest: string
  title: string
  youtube_url: string
  timestamp: string | null
  score: number | null
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceCitation[] | null
  prompt_tokens: number | null
  completion_tokens: number | null
  latency_ms: number | null
  created_at: string
}

export interface MessageListResponse {
  messages: Message[]
}

// SSE event types emitted by the backend
export type SSEEvent =
  | { type: 'token'; delta: string }
  | { type: 'sources'; sources: SourceCitation[] }
  | { type: 'artifact_id'; artifact_id: string }
  | { type: 'done'; message_id: string; sources: SourceCitation[] | null; artifact_id: string | null }
  | { type: 'error'; code: string; message: string }

export const messagesApi = {
  list: (sessionId: string) =>
    apiFetch<MessageListResponse>(`/api/v1/sessions/${sessionId}/messages`),

  /**
   * Open an SSE stream for a user message.
   * Returns an EventSource-like object via ReadableStream parsing.
   * Calls onEvent for each parsed SSE event, onDone when the stream closes.
   */
  stream: (
    sessionId: string,
    content: string,
    callbacks: {
      onToken: (delta: string) => void
      onSources: (sources: SourceCitation[]) => void
      onArtifactId: (id: string) => void
      onDone: (event: Extract<SSEEvent, { type: 'done' }>) => void
      onError: (msg: string) => void
    }
  ): (() => void) => {
    const controller = new AbortController()

    fetch(`${API_BASE}/api/v1/sessions/${sessionId}/messages/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          callbacks.onError(body?.error?.message || `HTTP ${res.status}`)
          return
        }

        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event: SSEEvent = JSON.parse(line.slice(6))
              if (event.type === 'token') callbacks.onToken(event.delta)
              else if (event.type === 'sources') callbacks.onSources(event.sources)
              else if (event.type === 'artifact_id') callbacks.onArtifactId(event.artifact_id)
              else if (event.type === 'done') callbacks.onDone(event)
              else if (event.type === 'error') callbacks.onError(event.message)
            } catch (_) {
              // Ignore malformed lines
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') callbacks.onError(err.message)
      })

    // Return cancel function
    return () => controller.abort()
  },
}
