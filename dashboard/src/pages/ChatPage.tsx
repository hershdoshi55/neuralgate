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

function providerLogo(model: string): string | null {
  const m = model.toLowerCase()
  if (m.includes('claude'))   return '/images/claude.jpeg'
  if (m.includes('gpt') || m.includes('o1') || m.includes('o3')) return '/images/openai.png'
  if (m.includes('gemini'))   return '/images/gemini.png'
  if (m.includes('deepseek')) return '/images/DeepSeek.png'
  return null
}

function ModelAvatar({ model }: { model: string }) {
  const logo = providerLogo(model)
  if (logo) {
    return <img src={logo} alt={model} style={{ width: 32, height: 32, borderRadius: 10, objectFit: 'cover', flexShrink: 0 }} />
  }
  return <div style={{ width: 32, height: 32, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 }}>N</div>
}

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

  function handleModelChange(newModel: string) {
    if (messages.length > 0) {
      // Clear conversation when switching models so new model doesn't
      // inherit prior model's identity from conversation history
      setMessages([{
        role: 'assistant',
        content: `🔄 Switched to **${newModel}**. Starting a fresh conversation.`,
      }])
    }
    setSelectedModel(newModel)
  }

  function newChat() {
    setMessages([])
    setInput('')
  }

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
      const actualModel = data.model ?? ng.selected_model ?? selectedModel
      const failover = ng.failover === true
      const content = data.choices?.[0]?.message?.content ?? data.detail?.message ?? '(no response)'
      const assistantMsg: Message = {
        role: 'assistant',
        content: failover
          ? `⚠️ **${selectedModel}** failed — fell back to **${actualModel}**.\n\n${content}`
          : content,
        meta: {
          model: actualModel,
          tier: ng.complexity_tier ?? null,
          cost: ng.total_cost_usd ?? 0,
          latency: ng.total_latency_ms ?? 0,
          cache_hit: ng.cache_hit ?? false,
          cache_similarity: ng.cache_similarity ?? null,
        },
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Request failed: ${e instanceof Error ? e.message : 'Is the proxy running?'}` }])
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
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button style={s.newChatBtn} onClick={newChat}>+ New Chat</button>
          <select style={s.select} value={selectedModel} onChange={e => handleModelChange(e.target.value)}>
            <optgroup label="Routing Aliases">
              {virtualModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
            </optgroup>
            <optgroup label="Specific Models">
              {realModels.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
            </optgroup>
          </select>
        </div>
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
            {msg.role === 'assistant' && <ModelAvatar model={msg.meta?.model ?? ''} />}
            <div style={{ maxWidth: '70%' }}>
              <div style={{ ...s.bubble, ...(msg.role === 'user' ? s.bubbleUser : s.bubbleAssistant) }}>
                <p style={{ ...s.bubbleText, color: msg.role === 'user' ? '#fff' : 'inherit' }}>{msg.content}</p>
              </div>
              {msg.meta && (
                <div style={s.metaStrip}>
                  <span style={s.metaChip}>{msg.meta.model}</span>
                  {msg.meta.tier && (
                    <span style={{ ...s.metaChip, color: TIER_COLOR[msg.meta.tier] ?? '#6b7280' }}>
                      {msg.meta.tier}
                    </span>
                  )}
                  <span style={s.metaChip}>{msg.meta.latency}ms</span>
                  {msg.meta.cost > 0
                    ? <span style={s.metaChip}>${msg.meta.cost.toFixed(6)}</span>
                    : <span style={{ ...s.metaChip, color: '#22c55e' }}>cached</span>
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
  page:            { display: 'flex', flexDirection: 'column', height: '100%', gap: 18 },
  header:          { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexShrink: 0 },
  title:           { fontSize: 24, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' },
  sub:             { fontSize: 13, color: 'var(--text-muted)', marginTop: 3 },
  select:          { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 9, padding: '8px 14px', fontSize: 13, color: 'var(--text)', cursor: 'pointer', minWidth: 200, fontFamily: 'inherit', fontWeight: 500, boxShadow: 'var(--shadow-sm)' },
  thread:          { flex: 1, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: '20px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18, minHeight: 0, boxShadow: 'var(--shadow)' },
  empty:           { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 40 },
  emptyIcon:       { fontSize: 52, marginBottom: 8 },
  emptyTitle:      { fontSize: 20, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  emptySub:        { fontSize: 14, color: 'var(--text-muted)', textAlign: 'center' as const, maxWidth: 340, lineHeight: 1.6 },
  msgRow:          { display: 'flex', gap: 12, alignItems: 'flex-end' },
  avatar:          { width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 },
  userAvatar:      { width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg, #374151, #1f2937)', color: '#9ca3af', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14, flexShrink: 0 },
  bubble:          { padding: '12px 16px', borderRadius: 14, wordBreak: 'break-word' as const },
  bubbleUser:      { background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', borderBottomRightRadius: 4, boxShadow: '0 4px 12px rgba(99,102,241,0.25)' },
  bubbleAssistant: { background: 'var(--input-bg)', border: '1px solid var(--border)', borderBottomLeftRadius: 4 },
  bubbleText:      { fontSize: 14, lineHeight: 1.65, whiteSpace: 'pre-wrap' as const },
  metaStrip:       { display: 'flex', flexWrap: 'wrap' as const, gap: 5, marginTop: 7, paddingLeft: 4 },
  metaChip:        { fontSize: 11, color: 'var(--text-muted)', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 20, padding: '2px 9px', fontWeight: 500 },
  dots:            { display: 'flex', gap: 5, padding: '5px 0' },
  dot:             { width: 7, height: 7, borderRadius: '50%', background: '#6366f1', animation: 'bounce 1.2s infinite' },
  inputArea:       { display: 'flex', gap: 10, background: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', padding: '14px 16px', flexShrink: 0, boxShadow: 'var(--shadow)' },
  textarea:        { flex: 1, background: 'transparent', border: 'none', outline: 'none', resize: 'none' as const, fontSize: 14, color: 'var(--text)', fontFamily: 'inherit', lineHeight: 1.55 },
  sendBtn:         { width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, alignSelf: 'flex-end', boxShadow: '0 4px 12px rgba(99,102,241,0.3)', transition: 'opacity 0.15s' },
  newChatBtn:      { background: 'var(--input-bg)', border: '1px solid var(--border)', borderRadius: 9, padding: '8px 16px', cursor: 'pointer', fontSize: 13, color: 'var(--text)', fontWeight: 600, whiteSpace: 'nowrap' as const, boxShadow: 'var(--shadow-sm)', transition: 'all 0.15s' },
}
