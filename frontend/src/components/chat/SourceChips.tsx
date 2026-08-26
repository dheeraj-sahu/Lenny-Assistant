/**
 * components/chat/SourceChips.tsx
 * Renders clickable episode citation chips below an assistant message.
 */
import type { SourceCitation } from '../../api/messagesApi'

interface Props {
  sources: SourceCitation[]
}

export function SourceChips({ sources }: Props) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="sources-strip" role="list" aria-label="Episode sources">
      {sources.map((src) => {
        // Build timestamped YouTube link if timestamp is available
        const url = src.timestamp
          ? `${src.youtube_url}&t=${timestampToSeconds(src.timestamp)}`
          : src.youtube_url

        return (
          <a
            key={src.episode_slug}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="source-chip"
            title={`${src.guest} — ${src.title}${src.timestamp ? ` at ${src.timestamp}` : ''}`}
            role="listitem"
          >
            <span className="source-chip-icon">▶</span>
            <span>{src.guest}</span>
          </a>
        )
      })}
    </div>
  )
}

function timestampToSeconds(ts: string): number {
  const parts = ts.split(':').map(Number)
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  return 0
}
