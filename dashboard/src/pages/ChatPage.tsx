import { useState, useRef, useEffect } from 'react'
import { apiFetch } from '../api'

interface ModelOption { id: string; owned_by: string }

interface MetaInfo {
  model: string
  tier: string | null
  cost: number
  latency: number
  cache_hit: boolean
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  meta?: MetaInfo
}

const VIRTUAL = ['auto', 'cheapest', 'balanced', 'best']

function shortName(id: string): string {
  return id
    .replace(/^claude-/, '')
    .replace(/^gpt-/, 'GPT ')
    .replace(/^gemini-/, '')
    .replace(/^deepseek-/, '')
    .replace(/-\d{8}$/, '')        // strip date suffixes like -20251001
    .replace(/-/g, ' ')
    .replace(/\b(\d)/g, ' $1')     // space before version numbers
    .replace(/\s+/g, ' ')
    .trim()
    // capitalise first letter of each word
    .replace(/\b\w/g, c => c.toUpperCase())
}

const PROVIDER_GROUPS = [
  { key: 'routing', label: 'Auto Route', ids: VIRTUAL },
  { key: 'claude',   label: 'Claude',    match: (id: string) => id.includes('claude') },
  { key: 'openai',   label: 'ChatGPT',   match: (id: string) => id.startsWith('gpt') || id.startsWith('o1') || id.startsWith('o3') },
  { key: 'google',   label: 'Gemini',    match: (id: string) => id.includes('gemini') },
  { key: 'deepseek', label: 'DeepSeek',  match: (id: string) => id.includes('deepseek') },
]

const PROVIDER_COLORS: Record<string, string> = {
  claude:   '#f97316',
  gpt:      '#10b981',
  o1:       '#10b981',
  o3:       '#10b981',
  gemini:   '#3b82f6',
  deepseek: '#8b5cf6',
}

function modelColor(model: string): string {
  const m = model.toLowerCase()
  for (const [key, color] of Object.entries(PROVIDER_COLORS)) {
    if (m.includes(key)) return color
  }
  return '#6b7280'
}

function providerLogo(model: string): string | null {
  const m = model.toLowerCase()
  if (m.includes('claude'))   return '/images/claude.jpeg'
  if (m.includes('gpt') || m.includes('o1') || m.includes('o3')) return '/images/openai.png'
  if (m.includes('gemini'))   return '/images/gemini.png'
  if (m.includes('deepseek')) return '/images/DeepSeek.png'
  return null
}

function ModelAvatar({ model, size = 32 }: { model: string; size?: number }) {
  const logo = providerLogo(model)
  const style = { width: size, height: size, borderRadius: size * 0.3, objectFit: 'cover' as const, flexShrink: 0 }
  if (logo) return <img src={logo} alt={model} style={style} />
  return (
    <div style={{ ...style, background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: size * 0.4 }}>
      N
    </div>
  )
}

const TIER_COLOR: Record<string, string> = { cheap: '#22c55e', mid: '#f59e0b', frontier: '#6366f1' }

function MetaStrip({ meta }: { meta: MetaInfo }) {
  return (
    <div style={s.metaStrip}>
      <span style={s.metaChip}>{meta.model}</span>
      {meta.tier && <span style={{ ...s.metaChip, color: TIER_COLOR[meta.tier] }}>{meta.tier}</span>}
      <span style={s.metaChip}>{meta.latency}ms</span>
      {meta.cost > 0
        ? <span style={s.metaChip}>${meta.cost.toFixed(6)}</span>
        : <span style={{ ...s.metaChip, color: '#22c55e' }}>cached</span>}
    </div>
  )
}

export function ChatPage() {
  const [models, setModels] = useState<ModelOption[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('auto')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    apiFetch('/api/v1/models').then(r => r.json()).then(d => setModels(d.data ?? [])).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function newChat() { setMessages([]); setInput('') }

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { role: 'user', content: text }
    const history = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, userMsg])
    try {
      const res = await apiFetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedModel, messages: history }),
      })
      const data = await res.json()
      const ng = data.x_neuralgate ?? {}
      const actualModel = data.model ?? ng.selected_model ?? selectedModel
      const content = data.choices?.[0]?.message?.content ?? data.detail?.message ?? '(no response)'
      setMessages(prev => [...prev, {
        role: 'assistant', content,
        meta: { model: actualModel, tier: ng.complexity_tier ?? null, cost: ng.total_cost_usd ?? 0, latency: ng.total_latency_ms ?? 0, cache_hit: ng.cache_hit ?? false },
      }])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Request failed: ${e instanceof Error ? e.message : 'Error'}` }])
    }

    setLoading(false)
  }

  // Build grouped columns: routing aliases + one per provider
  const groupedColumns = PROVIDER_GROUPS.map(g => {
    const ids = g.ids
      ? g.ids.filter(id => models.some(m => m.id === id))
      : models.filter(m => g.match!(m.id)).map(m => m.id)
    return { ...g, ids }
  }).filter(g => g.ids.length > 0)

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <h2 style={s.title}>Chat</h2>
          <p style={s.sub}>Send requests through NeuralGate's intelligent router</p>
        </div>
        <button style={s.newChatBtn} onClick={newChat}>+ New Chat</button>
      </div>

      {/* Model selector */}
      <div style={s.modelBar}>
        <div style={s.modelBarTop}>
          <span style={s.modelBarLabel}>Model</span>
        </div>
        <div style={s.modelColumns}>
          {groupedColumns.map((group, gi) => (
            <div key={group.key} style={{ ...s.modelCol, borderLeft: gi > 0 ? '1px solid var(--border)' : 'none' }}>
              <p style={s.colHeader}>{group.label}</p>
              {group.ids.map(id => {
                const active = selectedModel === id
                const color = group.key === 'routing' ? '#3b82f6' : modelColor(id)
                return (
                  <button
                    key={id}
                    style={{ ...s.modelBtn, background: active ? color + '18' : 'transparent', color: active ? color : 'var(--text-muted)', fontWeight: active ? 700 : 400 }}
                    onClick={() => setSelectedModel(id)}
                  >
                    {active && <span style={{ ...s.activeDot, background: color }} />}
                    {shortName(id)}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Thread */}
      <div style={s.thread}>
        {messages.length === 0 && (
          <div style={s.empty}>
            <div style={s.emptyIcon}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <p style={s.emptyTitle}>Start a conversation</p>
            <p style={s.emptySub}>NeuralGate will route your request to the optimal model</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === 'user' ? (
              <div style={{ ...s.msgRow, justifyContent: 'flex-end' }}>
                <div style={{ maxWidth: '70%' }}>
                  <div style={{ ...s.bubble, ...s.bubbleUser }}>
                    <p style={{ ...s.bubbleText, color: '#fff' }}>{msg.content}</p>
                  </div>
                </div>
                <div style={s.userAvatar}>U</div>
              </div>
            ) : (
              <div style={{ ...s.msgRow, justifyContent: 'flex-start' }}>
                <ModelAvatar model={msg.meta?.model ?? ''} />
                <div style={{ maxWidth: '70%' }}>
                  <div style={{ ...s.bubble, ...s.bubbleAssistant }}>
                    <p style={s.bubbleText}>{msg.content}</p>
                  </div>
                  {msg.meta && <MetaStrip meta={msg.meta} />}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ ...s.msgRow, justifyContent: 'flex-start' }}>
            <ModelAvatar model="" />
            <div style={{ ...s.bubble, ...s.bubbleAssistant }}>
              <div style={s.dots}>
                <span style={{ ...s.dot, animationDelay: '0ms' }} />
                <span style={{ ...s.dot, animationDelay: '150ms' }} />
                <span style={{ ...s.dot, animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={s.inputArea}>
        <textarea
          style={s.textarea}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
          rows={3}
        />
        <button
          style={{ ...s.sendBtn, opacity: loading || !input.trim() ? 0.5 : 1 }}
          onClick={send}
          disabled={loading || !input.trim()}
        >
          {loading ? '…' : '↑'}
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page:            { display: 'flex', flexDirection: 'column', height: '100%', gap: 14 },
  header:          { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexShrink: 0 },
  title:           { fontSize: 24, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' },
  sub:             { fontSize: 13, color: 'var(--text-muted)', marginTop: 3 },
  newChatBtn:      { background: 'var(--input-bg)', border: '1px solid var(--border)', borderRadius: 9, padding: '8px 16px', cursor: 'pointer', fontSize: 13, color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' as const, boxShadow: 'var(--shadow-sm)' },
  modelBar:        { background: 'var(--card)', borderRadius: 12, padding: '14px 18px', border: '1px solid var(--border)', flexShrink: 0 },
  modelBarTop:     { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  modelBarLabel:   { fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 8 },
  modelColumns:    { display: 'flex', gap: 0 },
  modelCol:        { display: 'flex', flexDirection: 'column' as const, gap: 2, padding: '0 16px', minWidth: 110 },
  colHeader:       { fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.08em', marginBottom: 6, paddingBottom: 6, borderBottom: '1px solid var(--border)' },
  modelBtn:        { display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, textAlign: 'left' as const, transition: 'all 0.12s', whiteSpace: 'nowrap' as const },
  activeDot:       { width: 5, height: 5, borderRadius: '50%', flexShrink: 0 },
  thread:          { flex: 1, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: '20px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18, minHeight: 0, boxShadow: 'var(--shadow)' },
  empty:           { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 40 },
  emptyIcon:       { marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 72, height: 72, borderRadius: 20, background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' },
  emptyTitle:      { fontSize: 20, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  emptySub:        { fontSize: 14, color: 'var(--text-muted)', textAlign: 'center' as const, maxWidth: 400, lineHeight: 1.6 },
  msgRow:          { display: 'flex', gap: 12, alignItems: 'flex-end' },
  userAvatar:      { width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg, #374151, #1f2937)', color: '#9ca3af', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 },
  bubble:          { padding: '12px 16px', borderRadius: 14, wordBreak: 'break-word' as const },
  bubbleUser:      { background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)', borderBottomRightRadius: 4, boxShadow: '0 4px 12px rgba(59,130,246,0.25)' },
  bubbleAssistant: { background: 'var(--input-bg)', border: '1px solid var(--border)', borderBottomLeftRadius: 4 },
  bubbleText:      { fontSize: 14, lineHeight: 1.65, whiteSpace: 'pre-wrap' as const },
  metaStrip:       { display: 'flex', flexWrap: 'wrap' as const, gap: 5, marginTop: 7, paddingLeft: 4 },
  metaChip:        { fontSize: 11, color: 'var(--text-muted)', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 20, padding: '2px 9px', fontWeight: 500 },
  dots:            { display: 'flex', gap: 5, padding: '5px 0' },
  dot:             { width: 7, height: 7, borderRadius: '50%', background: '#3b82f6', animation: 'bounce 1.2s infinite' },
  inputArea:       { display: 'flex', gap: 10, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: '14px 16px', flexShrink: 0, boxShadow: 'var(--shadow)' },
  textarea:        { flex: 1, background: 'transparent', border: 'none', outline: 'none', resize: 'none' as const, fontSize: 14, color: 'var(--text)', fontFamily: 'inherit', lineHeight: 1.55 },
  sendBtn:         { width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, alignSelf: 'flex-end', boxShadow: '0 4px 12px rgba(59,130,246,0.3)', transition: 'opacity 0.15s' },
}
