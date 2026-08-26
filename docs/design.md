# Design — The Lenny Growth Assistant

## 1. Design Principles

1. **Clarity over chrome** — The interface should feel like a thinking tool, not a marketing page. Every element earns its place by helping the user get answers.
2. **Progressive disclosure** — Start with the conversation. Only show the artifact panel when there is an artifact. Only show action buttons when they are relevant.
3. **Trust through transparency** — Source citations are always present and always clickable. The provider badge is always visible. "I don't know" is a first-class response.
4. **Performance as UX** — Streaming tokens appear immediately so the user knows the system is working, even on slow local models.

---

## 2. Information Architecture

```
App (full viewport)
├── SessionSidebar (260px fixed left)
│   ├── Logo + product name
│   ├── [+ New chat] button
│   └── Session list (scrollable, newest first)
│
├── ChatPanel (flexible center)
│   ├── Header bar
│   │   ├── Session title (or "New chat")
│   │   └── Provider badge (Local · Ollama · llama3.1:8b)
│   ├── Message thread (scrollable)
│   │   ├── Empty state (suggestions when no messages)
│   │   ├── User message bubbles (right-aligned, accent gradient)
│   │   └── Assistant message bubbles (left-aligned)
│   │       ├── Markdown-rendered content
│   │       ├── Source chips (clickable, link to timestamped YouTube)
│   │       └── Action buttons (Turn into Ship30 / View artifact)
│   └── Input area
│       ├── Auto-resize textarea
│       └── Send button (spinner while streaming)
│
└── ArtifactViewer (420px fixed right, hidden when no artifact)
    ├── Header bar
    │   ├── Type badge (MARKDOWN / HTML)
    │   ├── Artifact title
    │   └── Action buttons (Copy · Download · Close)
    └── Content area
        ├── Markdown: MarkdownRenderer (react-markdown, safe)
        └── HTML: SandboxedHtmlFrame (iframe with sandbox attribute)
```

---

## 3. Key Interaction States

### 3.1 Empty (no session selected)
- Center pane shows welcome message and CTA to create a session

### 3.2 New session (no messages)
- 4 suggestion chips shown for common queries
- Textarea focused

### 3.3 Streaming response
- User message appears immediately (optimistic)
- Assistant bubble appears with blinking cursor
- Tokens append progressively
- Source chips appear as soon as the agent emits them (may be before generation completes)
- Send button disabled + shows spinner

### 3.4 Completed response
- Cursor disappears
- Action buttons appear: "Turn into Ship30 essay" and/or "View artifact"
- Send button re-enabled

### 3.5 Artifact generated
- ArtifactViewer slides open on the right
- Shows the artifact immediately (fetched by ID)
- Chat panel narrows slightly (responsive grid)

### 3.6 Error state
- Friendly inline error banner (not a modal, not a toast that disappears)
- Shows error code and human-readable message
- Input re-enabled so user can retry

---

## 4. Responsive Behavior

| Viewport | Layout |
|---|---|
| > 900px | Three-column: sidebar + chat + artifact |
| 600–900px | Two-column: sidebar + chat (artifact hidden) |
| < 600px | Single-column: chat only (sidebar slides over on demand) |

The artifact viewer collapses to zero-width on narrow screens. On mobile, artifacts can be downloaded for offline viewing.

---

## 5. Accessibility

- All interactive elements have unique `id` attributes (for browser testing)
- ARIA labels on sidebar nav, message thread (`role="log" aria-live="polite"`), and input
- Source chips use `role="list"` / `role="listitem"`
- Color is not the only indicator — provider status uses a dot + text label
- Keyboard navigation: `Enter` sends the message, `Shift+Enter` adds a newline
- Focus management: new session creation focuses the textarea

---

## 6. Design Decisions

**Why a fixed right panel instead of a modal for artifacts?**
Keeping the artifact beside the conversation lets the user refer to both simultaneously — exactly the Claude Artifacts UX that the assignment references. A modal would force the user to close the artifact to read the conversation that spawned it.

**Why streaming over HTTP SSE instead of WebSocket?**
SSE is unidirectional (server → client), which is all we need for token streaming. It works natively with `fetch` and `EventSource`, requires no special server infrastructure, and is simpler to proxy and debug than WebSockets.

**Why suggestion chips in the empty state?**
Cold-start anxiety is real — a blank input box with no hints discourages first-time users. Four concrete example queries show the system's capabilities and lower the barrier to the first interaction.

**Why not a Toast for errors?**
Toasts disappear before the user can read them and are inaccessible for screen readers. An inline, persistent error banner that stays until the user retries is more reliable and more honest.

**Source chip design — why guest name only?**
Full episode titles are too long for chips at small font sizes and would wrap awkwardly. Showing the guest name is sufficient to identify the source; the full title is in the `title` attribute on hover, and clicking opens the exact YouTube timestamp.
