import { useEffect, useState, useCallback } from 'react'
import type { RecentRequest } from '../types'

const TIER_COLOR: Record<string, string> = {
  cheap:    '#10b981',
  mid:      '#f59e0b',
  frontier: '#6366f1',
}

const PROVIDER_COLOR: Record<string, string> = {
  anthropic: '#f97316',
  openai:    '#10b981',
  google:    '#3b82f6',
  deepseek:  '#8b5cf6',
  cache:     '#06b6d4',
}

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function providerColor(model: string, provider: string): string {
  if (PROVIDER_COLOR[provider]) return PROVIDER_COLOR[provider]
  const m = model.toLowerCase()
  if (m.includes('claude'))   return PROVIDER_COLOR.anthropic
  if (m.includes('gpt') || m.includes('o1') || m.includes('o3')) return PROVIDER_COLOR.openai
  if (m.includes('gemini'))   return PROVIDER_COLOR.google
  if (m.includes('deepseek')) return PROVIDER_COLOR.deepseek
  return '#94a3b8'
}

export function LiveRequestFeed() {
  const [requests, setRequests] = useState<RecentRequest[]>([])
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const refresh = useCallback(() => {
    fetch('/api/analytics/recent?limit=15')
      .then((r) => r.json())
      .then((d) => {
        setRequests(d.requests ?? [])
        setLastUpdated(new Date())
      })
      .catch(console.error)
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 5000)
    return () => clearInterval(id)
  }, [refresh])

  return (
    <div style={s.card}>
      <div style={s.header}>
        <div>
          <h3 style={s.title}>Live Request Feed</h3>
          <p style={s.subtitle}>
            {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Loading…'} · refreshes every 5s
          </p>
        </div>
        <button style={s.btn} onClick={refresh}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ marginRight: 5, display: 'inline' }}>
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          Refresh
        </button>
      </div>

      <div style={s.tableWrap}>
        <div style={s.thead}>
          <span style={{ ...s.th, flex: 2.5 }}>Model</span>
          <span style={{ ...s.th, flex: 1 }}>Tier</span>
          <span style={{ ...s.th, flex: 1 }}>Tokens</span>
          <span style={{ ...s.th, flex: 1.2 }}>Cost</span>
          <span style={{ ...s.th, flex: 1 }}>Latency</span>
          <span style={{ ...s.th, flex: 1.2 }}>Cache</span>
          <span style={{ ...s.th, flex: 1.5 }}>Time</span>
        </div>

        {requests.length === 0 && (
          <div style={s.empty}>No requests yet — send some through the proxy.</div>
        )}

        {requests.map((r, idx) => {
          const dot = providerColor(r.selected_model, r.selected_provider)
          return (
            <div key={r.request_id} style={{ ...s.row, background: idx % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)' }}>
              <span style={{ ...s.td, flex: 2.5, color: 'var(--text)', fontWeight: 500 }}>
                <span style={{ ...s.provDot, background: dot }} />
                {r.selected_model}
              </span>
              <span style={{ ...s.td, flex: 1 }}>
                {r.complexity_tier ? (
                  <span style={{ ...s.pill, background: TIER_COLOR[r.complexity_tier] + '20', color: TIER_COLOR[r.complexity_tier] }}>
                    {r.complexity_tier}
                  </span>
                ) : (
                  <span style={{ ...s.pill, background: '#06b6d420', color: '#06b6d4' }}>cached</span>
                )}
              </span>
              <span style={{ ...s.td, flex: 1 }}>{r.total_tokens.toLocaleString()}</span>
              <span style={{ ...s.td, flex: 1.2 }}>
                {r.total_cost_usd > 0 ? `$${r.total_cost_usd.toFixed(6)}` : <span style={{ color: '#10b981', fontWeight: 600 }}>free</span>}
              </span>
              <span style={{ ...s.td, flex: 1, color: r.total_latency_ms < 100 ? '#10b981' : 'var(--text-muted)', fontWeight: r.total_latency_ms < 100 ? 600 : 400 }}>
                {formatMs(r.total_latency_ms)}
              </span>
              <span style={{ ...s.td, flex: 1.2 }}>
                {r.cache_hit ? (
                  <span style={{ color: '#10b981', fontWeight: 600, fontSize: 12 }}>
                    ✓ {r.cache_similarity ? (r.cache_similarity * 100).toFixed(0) + '%' : 'exact'}
                  </span>
                ) : <span style={{ color: 'var(--border)' }}>—</span>}
              </span>
              <span style={{ ...s.td, flex: 1.5, fontSize: 12 }}>
                {new Date(r.created_at).toLocaleTimeString()}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:      { background: 'var(--card)', borderRadius: 'var(--radius)', padding: 24, boxShadow: 'var(--shadow)', border: '1px solid var(--border)' },
  header:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  title:     { fontSize: 16, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  subtitle:  { fontSize: 12, color: 'var(--text-muted)', marginTop: 3 },
  btn:       { display: 'flex', alignItems: 'center', background: 'var(--input-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontSize: 13, color: 'var(--text)', fontWeight: 500, transition: 'all 0.15s' },
  tableWrap: { overflow: 'auto' },
  thead:     { display: 'flex', padding: '0 0 10px', borderBottom: '2px solid var(--border)', marginBottom: 4 },
  th:        { fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', paddingRight: 12, overflow: 'hidden' },
  row:       { display: 'flex', padding: '9px 0', borderBottom: '1px solid var(--border)', alignItems: 'center', transition: 'background 0.1s', borderRadius: 6 },
  td:        { fontSize: 13, paddingRight: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8 },
  pill:      { fontSize: 11, padding: '3px 9px', borderRadius: 20, fontWeight: 700, letterSpacing: '0.02em' },
  provDot:   { width: 8, height: 8, borderRadius: '50%', flexShrink: 0, display: 'inline-block' },
  empty:     { padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 },
}
