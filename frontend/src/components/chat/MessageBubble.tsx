/**
 * components/chat/MessageBubble.tsx
 *
 * Renders one message (user or assistant).
 * Assistant messages support:
 *  - Streaming markdown with a blinking cursor while in-progress
 *  - Source citation chips
 *  - "Turn into Ship 30 essay" and "Generate artifact" action buttons
 *  - "Render as HTML" button: auto-detects HTML code blocks and renders them
 *    in the artifact panel even if the model didn't call generate_artifact
 */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message, SourceCitation } from '../../api/messagesApi'
import { SourceChips } from './SourceChips'

interface Props {
  message: Message
  isStreaming?: boolean
  streamContent?: string
  streamSources?: SourceCitation[]
  onTurnIntoEssay?: () => void
  onViewArtifact?: (artifactId: string) => void
  onRenderHtml?: (htmlContent: string) => void  // NEW: render raw HTML directly
  artifactId?: string | null
}

/**
 * Extracts the first HTML code block from a message.
 * Returns null if none found.
 */
function extractHtmlBlock(content: string): string | null {
  // Match ```html ... ``` or raw <!DOCTYPE / <html blocks
  const fenced = content.match(/```html\s*([\s\S]*?)```/)
  if (fenced) return fenced[1].trim()

  // If the message itself is mostly HTML (starts with doctype or html tag)
  const trimmed = content.trim()
  if (trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html')) {
    return trimmed
  }

  return null
}

export function MessageBubble({
  message,
  isStreaming = false,
  streamContent,
  streamSources,
  onTurnIntoEssay,
  onViewArtifact,
  onRenderHtml,
  artifactId,
}: Props) {
  const isUser = message.role === 'user'
  const content = isStreaming && streamContent !== undefined ? streamContent : message.content
  const sources = isStreaming ? streamSources : message.sources

  // Detect HTML code block in assistant messages (only when not streaming)
  const htmlBlock = !isUser && !isStreaming ? extractHtmlBlock(content) : null

  return (
    <div className={`message-bubble ${message.role}`} id={`msg-${message.id}`}>
      {/* Message body */}
      <div className="bubble-body">
        {isUser ? (
          <span>{content}</span>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Open links in new tab
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && <span className="typing-cursor" aria-hidden="true" />}
          </>
        )}
      </div>

      {/* Sources strip */}
      {!isUser && sources && sources.length > 0 && (
        <SourceChips sources={sources} />
      )}

      {/* Action buttons (only on completed assistant messages) */}
      {!isUser && !isStreaming && content && (
        <div className="message-actions">
          {onTurnIntoEssay && (
            <button
              id={`essay-btn-${message.id}`}
              className="action-btn"
              onClick={onTurnIntoEssay}
              title="Convert this answer into a Ship 30 for 30 essay"
            >
              ✍️ Turn into Ship30 essay
            </button>
          )}

          {/* ✅ Show "Render as HTML" when model output contains an HTML block */}
          {htmlBlock && onRenderHtml && (
            <button
              id={`render-html-btn-${message.id}`}
              className="action-btn action-btn-html"
              onClick={() => onRenderHtml(htmlBlock)}
              title="Render this HTML in the artifact viewer"
            >
              🖥️ Render as HTML
            </button>
          )}

          {artifactId && onViewArtifact && (
            <button
              id={`view-artifact-btn-${message.id}`}
              className="action-btn"
              onClick={() => onViewArtifact(artifactId)}
            >
              📄 View artifact
            </button>
          )}
        </div>
      )}
    </div>
  )
}
