import { useState, useRef, useEffect } from 'react'

interface ModelOption { id: string; owned_by: string }

interface MetaInfo {
  model: string
  tier: string | null
  cost: number
  latency: number
  cache_hit: boolean
  cache_similarity: number | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  meta?: MetaInfo
}

const VIRTUAL = ['auto', 'cheapest', 'balanced', 'best']

export function ChatPage() {
  const [models, setModels] = useState<ModelOption[]>([])
  const [selectedModel, setSelectedModel] = useState('auto')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/v1/models').then(r => r.json()).then(d => setModels(d.data ?? [])).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    const userMsg: Message = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const history = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))
      const res = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedModel, messages: history }),
      })
      const data = await res.json()
      const ng = data.x_neuralgate ?? {}
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.choices?.[0]?.message?.content ?? '(no response)',
        meta: {
          model: data.model ?? ng.selected_model ?? selectedModel,
          tier: ng.complexity_tier ?? null,
          cost: ng.total_cost_usd ?? 0,
          latency: ng.total_latency_ms ?? 0,
          cache_hit: ng.cache_hit ?? false,
          cache_similarity: ng.cache_similarity ?? null,
        },
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Request failed. Is the proxy running?' }])
    } finally {
      setLoading(false)
    }
  }

  const TIER_COLOR: Record<string, string> = { cheap: '#22c55e', mid: '#f59e0b', frontier: '#6366f1' }

  const virtualModels = models.filter(m => VIRTUAL.includes(m.id))
  const realModels = models.filter(m => !VIRTUAL.includes(m.id))

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <h2 style={s.title}>Chat</h2>
          <p style={s.sub}>Send requests through NeuralGate's intelligent router</p>
        </div>
        <select style={s.select} value={selectedModel} onChange={e => setSelectedModel(e.target.value)}>
          <optgroup label="Routing Aliases">
            {virtualModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
          </optgroup>
          <optgroup label="Specific Models">
            {realModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
          </optgroup>
        </select>
      </div>

      {/* Thread */}
      <div style={s.thread}>
        {messages.length === 0 && (
          <div style={s.empty}>
            <div style={s.emptyIcon}>🧠</div>
            <p style={s.emptyTitle}>Start a conversation</p>
            <p style={s.emptySub}>NeuralGate will route your request to the optimal model</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ ...s.msgRow, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.role === 'assistant' && <div style={s.avatar}>N</div>}
            <div style={{ maxWidth: '70%' }}>
              <div style={{ ...s.bubble, ...(msg.role === 'user' ? s.bubbleUser : s.bubbleAssistant) }}>
                <p style={{ ...s.bubbleText, color: msg.role === 'user' ? '#fff' : 'inherit' }}>{msg.content}</p>
              </div>
              {msg.meta && (
                <div style={s.metaStrip}>
                  <span style={s.metaChip}>⚡ {msg.meta.model}</span>
                  {msg.meta.tier && (
                    <span style={{ ...s.metaChip, color: TIER_COLOR[msg.meta.tier] ?? '#6b7280' }}>
                      {msg.meta.tier}
                    </span>
                  )}
                  <span style={s.metaChip}>{msg.meta.latency}ms</span>
                  {msg.meta.cost > 0
                    ? <span style={s.metaChip}>${msg.meta.cost.toFixed(6)}</span>
                    : <span style={{ ...s.metaChip, color: '#22c55e' }}>⚡ cached</span>
                  }
                  {msg.meta.cache_similarity && (
                    <span style={s.metaChip}>{(msg.meta.cache_similarity * 100).toFixed(0)}% match</span>
                  )}
                </div>
              )}
            </div>
            {msg.role === 'user' && <div style={s.userAvatar}>U</div>}
          </div>
        ))}

        {loading && (
          <div style={{ ...s.msgRow, justifyContent: 'flex-start' }}>
            <div style={s.avatar}>N</div>
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
  page:            { display: 'flex', flexDirection: 'column', height: '100%', gap: 16 },
  header:          { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexShrink: 0 },
  title:           { fontSize: 22, fontWeight: 700, color: 'var(--text)' },
  sub:             { fontSize: 13, color: 'var(--text-muted)', marginTop: 2 },
  select:          { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: 13, color: 'var(--text)', cursor: 'pointer', minWidth: 180 },
  thread:          { flex: 1, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16, minHeight: 0 },
  empty:           { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 40 },
  emptyIcon:       { fontSize: 48, marginBottom: 8 },
  emptyTitle:      { fontSize: 18, fontWeight: 600, color: 'var(--text)' },
  emptySub:        { fontSize: 14, color: 'var(--text-muted)', textAlign: 'center' },
  msgRow:          { display: 'flex', gap: 10, alignItems: 'flex-end' },
  avatar:          { width: 32, height: 32, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 },
  userAvatar:      { width: 32, height: 32, borderRadius: 10, background: 'var(--border)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 },
  bubble:          { padding: '12px 16px', borderRadius: 12, wordBreak: 'break-word' },
  bubbleUser:      { background: '#6366f1', borderBottomRightRadius: 4 },
  bubbleAssistant: { background: 'var(--input-bg)', border: '1px solid var(--border)', borderBottomLeftRadius: 4 },
  bubbleText:      { fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' },
  metaStrip:       { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6, paddingLeft: 4 },
  metaChip:        { fontSize: 11, color: 'var(--text-muted)', background: 'var(--input-bg)', border: '1px solid var(--border)', borderRadius: 20, padding: '2px 8px' },
  dots:            { display: 'flex', gap: 4, padding: '4px 0' },
  dot:             { width: 7, height: 7, borderRadius: '50%', background: '#6366f1', animation: 'bounce 1.2s infinite' },
  inputArea:       { display: 'flex', gap: 10, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: 12, flexShrink: 0 },
  textarea:        { flex: 1, background: 'transparent', border: 'none', outline: 'none', resize: 'none', fontSize: 14, color: 'var(--text)', fontFamily: 'inherit', lineHeight: 1.5 },
  sendBtn:         { width: 44, height: 44, borderRadius: 10, background: '#6366f1', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, alignSelf: 'flex-end' },
}
