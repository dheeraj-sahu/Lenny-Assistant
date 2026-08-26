/**
 * components/sessions/SessionSidebar.tsx
 * Left rail showing session list and new-chat button.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsApi } from '../../api/sessionsApi'

interface Props {
  activeSessionId: string | null
  onSelectSession: (id: string, title: string | null) => void
  onNewSession: (id: string) => void
}

export function SessionSidebar({ activeSessionId, onSelectSession, onNewSession }: Props) {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: sessionsApi.list,
    // Refresh the list every 5s so new session titles appear after first message
    refetchInterval: 5000,
  })

  const createMutation = useMutation({
    mutationFn: () => sessionsApi.create(),
    onSuccess: (session) => {
      // Optimistically add the new session to the top of the list immediately
      queryClient.setQueryData(['sessions'], (old: any) => {
        const existing = old?.sessions ?? []
        // Avoid duplicates if it's already in the list
        if (existing.some((s: any) => s.id === session.id)) return old
        return {
          ...old,
          sessions: [session, ...existing],
          total: (old?.total ?? 0) + 1,
        }
      })
      onNewSession(session.id)
    },
  })

  const sessions = data?.sessions ?? []

  return (
    <aside className="sidebar" aria-label="Session navigation">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🎙</div>
          <span>Lenny Assistant</span>
        </div>

        <button
          id="new-chat-btn"
          className="new-chat-btn"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          aria-label="Start new chat session"
        >
          {createMutation.isPending ? (
            <span className="spinner" />
          ) : (
            <span>+</span>
          )}
          <span>New chat</span>
        </button>
      </div>

      {/* Session list */}
      <nav className="session-list" aria-label="Previous sessions">
        {isLoading && (
          <div style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            Loading…
          </div>
        )}
        {sessions.map((session) => (
          <button
            key={session.id}
            id={`session-${session.id}`}
            className={`session-item ${activeSessionId === session.id ? 'active' : ''}`}
            onClick={() => onSelectSession(session.id, session.title)}
            title={session.title ?? 'New chat'}
          >
            {session.title ?? 'New chat'}
          </button>
        ))}
        {!isLoading && sessions.length === 0 && (
          <div style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No sessions yet
          </div>
        )}
      </nav>
    </aside>
  )
}
