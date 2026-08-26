/**
 * components/artifacts/ArtifactViewer.tsx
 *
 * Right-panel artifact viewer.
 * - Accepts either an artifactId (fetches from backend) OR rawHtml (renders directly)
 * - Markdown artifacts → MarkdownRenderer (safe, no dangerouslySetInnerHTML)
 * - HTML artifacts → SandboxedHtmlFrame (sandboxed iframe, see SandboxedHtmlFrame.tsx)
 * - Download and Copy actions
 */
import { useQuery } from '@tanstack/react-query'
import { artifactsApi } from '../../api/artifactsApi'
import { MarkdownRenderer } from './MarkdownRenderer'
import { SandboxedHtmlFrame } from './SandboxedHtmlFrame'

interface Props {
  artifactId: string | null
  rawHtml: string | null      // NEW: for rendering HTML that wasn't saved as an artifact
  onClose: () => void
}

export function ArtifactViewer({ artifactId, rawHtml, onClose }: Props) {
  const { data: artifact, isLoading } = useQuery({
    queryKey: ['artifact', artifactId],
    queryFn: () => (artifactId ? artifactsApi.get(artifactId) : null),
    enabled: !!artifactId,
  })

  // Determine what to display
  const isRawMode = !!rawHtml && !artifactId
  const displayType = isRawMode ? 'html' : (artifact?.artifact_type ?? 'markdown')
  const displayContent = isRawMode ? rawHtml : (artifact?.sanitized_content ?? '')

  const handleCopy = () => {
    if (displayContent) navigator.clipboard.writeText(displayContent)
  }

  const handleDownload = () => {
    if (!displayContent) return
    const ext = displayType === 'html' ? 'html' : 'md'
    const blob = new Blob([displayContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact?.title?.replace(/\s+/g, '-').toLowerCase() ?? 'artifact'}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Nothing to show
  if (!artifactId && !rawHtml) {
    return (
      <div className="artifact-panel empty" aria-hidden="true" />
    )
  }

  return (
    <aside className="artifact-panel" aria-label="Artifact viewer">
      <div className="artifact-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <span className={`artifact-type-badge ${displayType}`}>
            {isRawMode ? 'HTML Preview' : (displayType === 'html' ? 'HTML' : 'Markdown')}
          </span>
          <span className="artifact-panel-title">
            {isRawMode ? 'HTML Render' : (artifact?.title ?? (isLoading ? 'Loading…' : 'Artifact'))}
          </span>
        </div>

        <div className="artifact-actions">
          <button
            id="artifact-copy-btn"
            className="artifact-action-btn"
            onClick={handleCopy}
            title="Copy to clipboard"
            disabled={!displayContent}
          >
            📋
          </button>
          <button
            id="artifact-download-btn"
            className="artifact-action-btn"
            onClick={handleDownload}
            title="Download file"
            disabled={!displayContent}
          >
            ⬇
          </button>
          <button
            id="artifact-close-btn"
            className="artifact-action-btn"
            onClick={onClose}
            title="Close viewer"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="artifact-content">
        {isLoading && !isRawMode && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
            <span className="spinner" />
          </div>
        )}

        {/* Raw HTML from message (no artifact ID) */}
        {isRawMode && (
          <SandboxedHtmlFrame content={rawHtml!} />
        )}

        {/* Artifact from backend */}
        {!isRawMode && artifact && (
          artifact.artifact_type === 'html'
            ? <SandboxedHtmlFrame content={artifact.sanitized_content} />
            : <MarkdownRenderer content={artifact.sanitized_content} />
        )}
      </div>
    </aside>
  )
}
