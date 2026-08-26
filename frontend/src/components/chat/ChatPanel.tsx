/**
 * components/chat/ChatPanel.tsx
 *
 * Main chat panel: message thread + input area.
 * Handles the full streaming lifecycle and delegates rendering to MessageBubble.
 */
import { useRef, useEffect, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { messagesApi, type Message, type SourceCitation } from '../../api/messagesApi'
import { MessageBubble } from './MessageBubble'
import { ProviderBadge } from './ProviderBadge'

const SUGGESTIONS = [
  'How do the best PLG companies think about pricing?',
  'What does Lenny say about finding product-market fit?',
  'How should early-stage startups approach growth?',
  'What are the best practices for user retention?',
]

interface StreamState {
  messageId: string   // temporary ID while streaming
  content: string
  sources: SourceCitation[]
  artifactId: string | null
}

interface Props {
  sessionId: string | null
  sessionTitle: string | null
  onArtifactReady: (id: string) => void
  onRenderHtml: (html: string) => void   // NEW: render HTML from a code block directly
}

export function ChatPanel({ sessionId, sessionTitle, onArtifactReady, onRenderHtml }: Props) {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState<StreamState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [artifactMap, setArtifactMap] = useState<Record<string, string>>({})
  // Optimistic user message — shows the user's text immediately without waiting for refetch
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<string | null>(null)
  const threadRef = useRef<HTMLDivElement>(null)
  const cancelStream = useRef<(() => void) | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch message history
  const { data, refetch } = useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () => (sessionId ? messagesApi.list(sessionId) : null),
    enabled: !!sessionId,
  })

  const messages = data?.messages ?? []

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight
    }
  }, [messages, streaming?.content, optimisticUserMsg])

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${e.target.scrollHeight}px`
  }

  const send = useCallback(
    (text: string) => {
      if (!sessionId || !text.trim() || streaming) return
      setError(null)
      setInput('')

      // Reset textarea height
      if (textareaRef.current) textareaRef.current.style.height = 'auto'

      // ✅ Show user message instantly (optimistic UI)
      setOptimisticUserMsg(text.trim())

      const tempId = `streaming-${Date.now()}`
      setStreaming({ messageId: tempId, content: '', sources: [], artifactId: null })

      const cancel = messagesApi.stream(sessionId, text.trim(), {
        onToken: (delta) =>
          setStreaming((prev) => prev ? { ...prev, content: prev.content + delta } : prev),
        onSources: (sources) =>
          setStreaming((prev) => prev ? { ...prev, sources } : prev),
        onArtifactId: (id) => {
          setStreaming((prev) => prev ? { ...prev, artifactId: id } : prev)
          onArtifactReady(id)
        },
        onDone: (event) => {
          setStreaming(null)
          setOptimisticUserMsg(null) // real messages coming from refetch
          if (event.artifact_id) {
            setArtifactMap((prev) => ({ ...prev, [event.message_id]: event.artifact_id! }))
            onArtifactReady(event.artifact_id)
          }
          refetch()
        },
        onError: (msg) => {
          setStreaming(null)
          setOptimisticUserMsg(null)
          setError(msg)
          refetch()
        },
      })
      cancelStream.current = cancel
    },
    [sessionId, streaming, refetch, onArtifactReady]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const handleEssayRequest = (msg: Message) => {
    const text = `Turn into Ship30 essay: ${msg.content.slice(0, 200)}`
    send(text)
  }

  const isLoading = !!streaming

  if (!sessionId) {
    return (
      <div className="chat-area">
        <div className="chat-empty">
          <div className="chat-empty-icon">🎙️</div>
          <h2>Lenny Growth Assistant</h2>
          <p>Start a new chat to ask questions grounded in Lenny's Podcast transcripts.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-area">
      {/* Header */}
      <div className="chat-header">
        <span className="chat-title">{sessionTitle || 'New chat'}</span>
        <ProviderBadge />
      </div>

      {/* Thread */}
      <div className="message-thread" ref={threadRef} role="log" aria-live="polite">
        {messages.length === 0 && !streaming && !optimisticUserMsg && (
          <div className="chat-empty">
            <div className="chat-empty-icon">💬</div>
            <h2>Ask anything about growth</h2>
            <p>Answers are grounded in 300+ Lenny's Podcast transcripts with source citations.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onTurnIntoEssay={msg.role === 'assistant' ? () => handleEssayRequest(msg) : undefined}
            onViewArtifact={(id) => onArtifactReady(id)}
            onRenderHtml={onRenderHtml}
            artifactId={artifactMap[msg.id] ?? null}
          />
        ))}

        {/* ✅ Optimistic user message — visible immediately */}
        {optimisticUserMsg && (
          <MessageBubble
            key="optimistic-user"
            message={{
              id: 'optimistic-user',
              session_id: sessionId,
              role: 'user',
              content: optimisticUserMsg,
              sources: null,
              prompt_tokens: null,
              completion_tokens: null,
              latency_ms: null,
              created_at: new Date().toISOString(),
            }}
          />
        )}

        {/* Streaming assistant message */}
        {streaming && (
          <MessageBubble
            key={streaming.messageId}
            message={{
              id: streaming.messageId,
              session_id: sessionId,
              role: 'assistant',
              content: streaming.content,
              sources: streaming.sources,
              prompt_tokens: null,
              completion_tokens: null,
              latency_ms: null,
              created_at: new Date().toISOString(),
            }}
            isStreaming
            streamContent={streaming.content}
            streamSources={streaming.sources}
          />
        )}
      </div>

      {/* Error banner */}
      {error && <div className="error-banner" style={{ margin: '0 20px 12px' }}>⚠️ {error}</div>}

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            id="chat-input"
            ref={textareaRef}
            className="chat-textarea"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask a product or growth question…"
            rows={1}
            disabled={isLoading}
            aria-label="Chat message input"
          />
          <button
            id="send-btn"
            className="send-btn"
            onClick={() => send(input)}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
          >
            {isLoading ? <span className="spinner" /> : '↑'}
          </button>
        </div>
      </div>
    </div>
  )
}
