/**
 * components/artifacts/SandboxedHtmlFrame.tsx
 *
 * Renders untrusted HTML inside a sandboxed iframe using the srcdoc attribute.
 *
 * Security model (defense layer 2 — see architecture.md for full explanation):
 *
 * ALLOWED (inside the iframe):
 *   - Styling, layout, CSS
 *   - Client-side JavaScript scoped to the iframe's own DOM
 *   - Reading/writing to the iframe's own localStorage (if allow-storage-access-by-user-activation)
 *
 * BLOCKED (by sandbox attribute — no allow-same-origin, allow-top-navigation, allow-popups):
 *   - Reading parent page DOM or cookies
 *   - Making authenticated requests to the backend with the user's session
 *   - Navigating the parent page
 *   - Opening new windows/popups
 *   - Submitting forms to external origins
 *
 * The server-side sanitizer (nh3) is defense layer 1.
 * This iframe sandbox is defense layer 2.
 * Two independent layers means a failure in either one alone is not exploitable.
 */

interface Props {
  /** Server-sanitized HTML content (nh3 already stripped scripts/handlers) */
  content: string
}

export function SandboxedHtmlFrame({ content }: Props) {
  // Wrap in a complete HTML document if not already
  const doc = content.trim().startsWith('<!DOCTYPE')
    ? content
    : `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body { font-family: system-ui, sans-serif; padding: 20px; line-height: 1.6;
         color: #111; background: #fff; }
  img { max-width: 100%; }
  a { color: #4f6ef7; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
  th { background: #f8fafc; font-weight: 600; }
</style>
</head>
<body>${content}</body>
</html>`

  return (
    <iframe
      className="artifact-html-frame"
      title="Generated HTML artifact"
      srcDoc={doc}
      sandbox="allow-scripts"
      // Explicitly NOT including:
      //   allow-same-origin   → would let iframe script access parent cookies/session
      //   allow-top-navigation → would let iframe redirect the parent page
      //   allow-popups         → would let iframe open new windows
      referrerPolicy="no-referrer"
      loading="lazy"
    />
  )
}
