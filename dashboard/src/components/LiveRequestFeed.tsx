import { useEffect, useState, useCallback } from 'react'
import type { RecentRequest } from '../types'

const TIER_COLOR: Record<string, string> = {
  cheap:    '#22c55e',
  mid:      '#f59e0b',
  frontier: '#6366f1',
}

const PROVIDER_EMOJI: Record<string, string> = {
  anthropic: '🟠',
  openai:    '🟢',
  google:    '🔵',
  deepseek:  '🟣',
  cache:     '⚡',
}

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
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
        <button style={s.btn} onClick={refresh}>↻ Refresh</button>
      </div>

      <div style={s.table}>
        <div style={s.thead}>
          <span style={{ ...s.col, flex: 2 }}>Model</span>
          <span style={{ ...s.col, flex: 1 }}>Tier</span>
          <span style={{ ...s.col, flex: 1 }}>Tokens</span>
          <span style={{ ...s.col, flex: 1 }}>Cost</span>
          <span style={{ ...s.col, flex: 1 }}>Latency</span>
          <span style={{ ...s.col, flex: 1 }}>Cache</span>
          <span style={{ ...s.col, flex: 2 }}>Time</span>
        </div>

        {requests.length === 0 && (
          <div style={s.empty}>No requests yet.</div>
        )}

        {requests.map((r) => (
          <div key={r.request_id} style={s.row}>
            <span style={{ ...s.col, flex: 2 }}>
              {PROVIDER_EMOJI[r.selected_provider] ?? '⚪'} {r.selected_model}
            </span>
            <span style={{ ...s.col, flex: 1 }}>
              {r.complexity_tier ? (
                <span style={{ ...s.pill, background: TIER_COLOR[r.complexity_tier] + '22', color: TIER_COLOR[r.complexity_tier] }}>
                  {r.complexity_tier}
                </span>
              ) : (
                <span style={{ ...s.pill, background: '#f0f9ff', color: '#0284c7' }}>cached</span>
              )}
            </span>
            <span style={{ ...s.col, flex: 1, color: '#374151' }}>{r.total_tokens.toLocaleString()}</span>
            <span style={{ ...s.col, flex: 1, color: '#374151' }}>
              {r.total_cost_usd > 0 ? `$${r.total_cost_usd.toFixed(6)}` : '—'}
            </span>
            <span style={{ ...s.col, flex: 1, color: r.total_latency_ms < 100 ? '#22c55e' : '#374151' }}>
              {formatMs(r.total_latency_ms)}
            </span>
            <span style={{ ...s.col, flex: 1 }}>
              {r.cache_hit ? (
                <span style={{ color: '#22c55e', fontWeight: 600 }}>
                  ✓ {r.cache_similarity ? (r.cache_similarity * 100).toFixed(0) + '%' : 'exact'}
                </span>
              ) : '—'}
            </span>
            <span style={{ ...s.col, flex: 2, color: '#9ca3af', fontSize: 11 }}>
              {new Date(r.created_at).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:    { background: '#fff', borderRadius: 10, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  header:  { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title:   { margin: 0, fontSize: 16, fontWeight: 600 },
  subtitle:{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' },
  btn:     { background: '#f3f4f6', border: 'none', borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13, color: '#374151' },
  table:   { overflow: 'auto' },
  thead:   { display: 'flex', padding: '6px 0', borderBottom: '1px solid #f3f4f6', marginBottom: 4 },
  row:     { display: 'flex', padding: '8px 0', borderBottom: '1px solid #f9fafb', alignItems: 'center' },
  col:     { fontSize: 13, paddingRight: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#6b7280', fontWeight: 500 },
  pill:    { fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 600 },
  empty:   { padding: '40px 0', textAlign: 'center', color: '#9ca3af', fontSize: 14 },
}
