import type { Summary } from '../types'

interface Props {
  summary: Summary | null
}

const CARDS = [
  { key: 'requests',    color: '#6366f1' },
  { key: 'cost',        color: '#22c55e' },
  { key: 'cache',       color: '#f59e0b' },
  { key: 'latency',     color: '#ec4899' },
] as const

export function CostCards({ summary }: Props) {
  if (!summary) {
    return (
      <div style={s.row}>
        {CARDS.map((c) => (
          <div key={c.key} style={s.card}>
            <div style={{ ...s.accent, background: c.color }} />
            <div style={s.skeleton} />
          </div>
        ))}
      </div>
    )
  }

  const cards = [
    {
      color: '#6366f1',
      label: 'Total Requests',
      value: summary.total_requests.toLocaleString(),
      sub: `last ${summary.period_days} days`,
    },
    {
      color: '#22c55e',
      label: 'Actual Cost',
      value: `$${summary.total_cost_usd.toFixed(4)}`,
      sub: `saved $${summary.total_savings_usd.toFixed(4)} (${summary.savings_percent}%)`,
    },
    {
      color: '#f59e0b',
      label: 'Cache Hit Rate',
      value: `${(summary.cache_hit_rate * 100).toFixed(1)}%`,
      sub: `${summary.tokens_saved_by_cache.toLocaleString()} tokens saved`,
    },
    {
      color: '#ec4899',
      label: 'Avg Latency',
      value: `${summary.avg_latency_ms.toLocaleString()}ms`,
      sub: `p95: ${summary.p95_latency_ms.toLocaleString()}ms`,
    },
  ]

  return (
    <div style={s.row}>
      {cards.map((c) => (
        <div key={c.label} style={s.card}>
          <div style={{ ...s.accent, background: c.color }} />
          <p style={s.label}>{c.label}</p>
          <p style={{ ...s.value, color: c.color }}>{c.value}</p>
          <p style={s.sub}>{c.sub}</p>
        </div>
      ))}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  row:      { display: 'flex', gap: 16, flexWrap: 'wrap' },
  card:     { flex: '1 1 180px', background: '#fff', borderRadius: 10, padding: '16px 20px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)', position: 'relative', overflow: 'hidden' },
  accent:   { position: 'absolute', top: 0, left: 0, right: 0, height: 3 },
  label:    { margin: '8px 0 4px', fontSize: 12, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' },
  value:    { margin: '0 0 4px', fontSize: 28, fontWeight: 700 },
  sub:      { margin: 0, fontSize: 12, color: '#9ca3af' },
  skeleton: { height: 80, background: '#f3f4f6', borderRadius: 6, marginTop: 8 },
}
