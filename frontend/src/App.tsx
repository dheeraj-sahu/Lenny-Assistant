/**
 * App.tsx
 * Root component — assembles the three-column layout:
 *   SessionSidebar | ChatPanel | ArtifactViewer
 */
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SessionSidebar } from './components/sessions/SessionSidebar'
import { ChatPanel } from './components/chat/ChatPanel'
import { ArtifactViewer } from './components/artifacts/ArtifactViewer'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [activeSessionTitle, setActiveSessionTitle] = useState<string | null>(null)
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null)
  const [rawHtml, setRawHtml] = useState<string | null>(null)  // for direct HTML rendering

  const handleSelectSession = (id: string, title: string | null) => {
    setActiveSessionId(id)
    setActiveSessionTitle(title)
    setActiveArtifactId(null)
    setRawHtml(null)
  }

  const handleNewSession = (id: string) => {
    setActiveSessionId(id)
    setActiveSessionTitle(null)
    setActiveArtifactId(null)
    setRawHtml(null)
  }

  const handleArtifactReady = (id: string) => {
    setActiveArtifactId(id)
    setRawHtml(null) // artifact from backend takes priority
  }

  const handleRenderHtml = (html: string) => {
    setActiveArtifactId(null) // clear any artifact-id based view
    setRawHtml(html)
  }

  const handleClose = () => {
    setActiveArtifactId(null)
    setRawHtml(null)
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-layout">
        <SessionSidebar
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
        />
        <ChatPanel
          sessionId={activeSessionId}
          sessionTitle={activeSessionTitle}
          onArtifactReady={handleArtifactReady}
          onRenderHtml={handleRenderHtml}
        />
        <ArtifactViewer
          artifactId={activeArtifactId}
          rawHtml={rawHtml}
          onClose={handleClose}
        />
      </div>
    </QueryClientProvider>
  )
}
