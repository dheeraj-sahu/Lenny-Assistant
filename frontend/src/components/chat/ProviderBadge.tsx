/**
 * components/chat/ProviderBadge.tsx
 *
 * Displays the active LLM provider/model fetched from /config.
 * Clicking opens a model switcher modal where the user can:
 *  - Toggle between Local (Ollama) and Cloud (Anthropic)
 *  - Enter their own Anthropic API key (not pre-configured in .env)
 *  - See corpus version and indexed chunk count
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { configApi } from '../../api/sessionsApi'

export function ProviderBadge() {
  const [open, setOpen] = useState(false)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
    staleTime: Infinity,
  })

  const switchMutation = useMutation({
    mutationFn: ({ provider, apiKey }: { provider: string; apiKey?: string }) =>
      configApi.switchProvider(provider, apiKey),
    onSuccess: (newConfig) => {
      queryClient.setQueryData(['config'], newConfig)
      setOpen(false)
      setApiKeyInput('')
    },
  })

  if (!data) return null

  const isCloud = data.provider === 'anthropic'
  const isOllama = data.provider === 'ollama'

  const handleSwitchToAnthropic = () => {
    if (!apiKeyInput.trim()) return
    switchMutation.mutate({ provider: 'anthropic', apiKey: apiKeyInput.trim() })
  }

  const handleSwitchToOllama = () => {
    switchMutation.mutate({ provider: 'ollama' })
  }

  return (
    <>
      <button
        id="provider-badge-btn"
        className="provider-badge"
        onClick={() => setOpen(true)}
        title="Click to change LLM provider/model"
        style={{ cursor: 'pointer' }}
      >
        <span className={`provider-badge-dot ${isCloud ? 'cloud' : ''}`} />
        <span>{isOllama ? '⚡ ' : '☁️ '}{data.provider_label}</span>
        <span style={{ opacity: 0.5, fontSize: '0.7rem' }}>▾</span>
      </button>

      {/* Modal overlay */}
      {open && (
        <div
          className="modal-overlay"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Model configuration"
        >
          <div
            className="model-switcher-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3>LLM Configuration</h3>
              <button className="modal-close-btn" onClick={() => setOpen(false)} aria-label="Close">✕</button>
            </div>

            <div className="modal-body">
              <p className="modal-hint">
                Choose the AI model powering your answers. Ollama runs <strong>locally at zero cost</strong>.
                Anthropic Claude is cloud-based and requires your API key.
              </p>

              {/* ── Option 1: Local Ollama ─────────────────────── */}
              <div className="provider-option-section">
                <button
                  id="use-ollama-btn"
                  className={`provider-option ${isOllama ? 'active' : ''}`}
                  onClick={handleSwitchToOllama}
                  disabled={switchMutation.isPending || isOllama}
                >
                  <span className="provider-option-icon">⚡</span>
                  <div className="provider-option-info">
                    <div className="provider-option-name">Local · Ollama</div>
                    <div className="provider-option-model">{data.ollama_model ?? 'qwen2.5:1.5b'}</div>
                    <div className="provider-option-desc">Free · runs on your machine · no API key needed</div>
                  </div>
                  {isOllama && <span className="provider-option-check">✓</span>}
                </button>
              </div>

              {/* ── Option 2: Anthropic Cloud ─────────────────── */}
              <div className="provider-option-section">
                <div className={`provider-option ${isCloud ? 'active' : ''}`} style={{ flexDirection: 'column', alignItems: 'stretch', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className="provider-option-icon">☁️</span>
                    <div className="provider-option-info">
                      <div className="provider-option-name">Cloud · Anthropic</div>
                      <div className="provider-option-model">{data.anthropic_model ?? 'claude-3-5-sonnet-20241022'}</div>
                      <div className="provider-option-desc">Better quality · requires your Anthropic API key</div>
                    </div>
                    {isCloud && <span className="provider-option-check">✓</span>}
                  </div>

                  {/* API key input — always visible for Anthropic */}
                  <div className="api-key-row">
                    <div className="api-key-input-wrap">
                      <input
                        id="anthropic-api-key-input"
                        type={showKey ? 'text' : 'password'}
                        className="api-key-input"
                        placeholder="sk-ant-api03-…  (your Anthropic API key)"
                        value={apiKeyInput}
                        onChange={(e) => setApiKeyInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSwitchToAnthropic()}
                      />
                      <button
                        className="api-key-toggle"
                        onClick={() => setShowKey(v => !v)}
                        tabIndex={-1}
                        title={showKey ? 'Hide key' : 'Show key'}
                      >
                        {showKey ? '🙈' : '👁'}
                      </button>
                    </div>
                    <button
                      id="switch-to-anthropic-btn"
                      className="api-key-submit-btn"
                      onClick={handleSwitchToAnthropic}
                      disabled={!apiKeyInput.trim() || switchMutation.isPending}
                    >
                      {switchMutation.isPending ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Use Claude →'}
                    </button>
                  </div>
                  <p className="api-key-hint">
                    🔒 Your key is only used for this session and never stored permanently.
                    Get one at <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer">console.anthropic.com</a>
                  </p>
                </div>
              </div>

              {/* Corpus info */}
              <div className="corpus-info">
                <div className="corpus-info-row">
                  <span>Embedding model</span>
                  <code>{data.embedding_model}</code>
                </div>
                {data.corpus_version && (
                  <div className="corpus-info-row">
                    <span>Corpus commit</span>
                    <code>{data.corpus_version}</code>
                  </div>
                )}
                {data.chunk_count != null && (
                  <div className="corpus-info-row">
                    <span>Indexed chunks</span>
                    <code>{data.chunk_count.toLocaleString()}</code>
                  </div>
                )}
              </div>

              {switchMutation.isError && (
                <p className="modal-error">
                  ⚠️ {(switchMutation.error as Error)?.message ?? 'Failed to switch provider. Check your API key.'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
