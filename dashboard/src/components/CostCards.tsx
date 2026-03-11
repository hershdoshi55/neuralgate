import type { Summary } from '../types'

interface Props {
  summary: Summary | null
}

function RequestsIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}

function CostIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23"/>
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>
  )
}

function CacheIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  )
}

function LatencyIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  )
}

const CARD_CONFIG = [
  { color: '#6366f1', bg: 'linear-gradient(135deg, #6366f1, #8b5cf6)', Icon: RequestsIcon },
  { color: '#10b981', bg: 'linear-gradient(135deg, #10b981, #059669)', Icon: CostIcon },
  { color: '#f59e0b', bg: 'linear-gradient(135deg, #f59e0b, #d97706)', Icon: CacheIcon },
  { color: '#ec4899', bg: 'linear-gradient(135deg, #ec4899, #db2777)', Icon: LatencyIcon },
]

export function CostCards({ summary }: Props) {
  const cards = summary ? [
    {
      label: 'Total Requests',
      value: summary.total_requests.toLocaleString(),
      sub: `Last ${summary.period_days} days`,
      trend: null,
    },
    {
      label: 'Actual Cost',
      value: `$${summary.total_cost_usd.toFixed(4)}`,
      sub: `Saved $${summary.total_savings_usd.toFixed(4)} (${summary.savings_percent}%)`,
      trend: 'down',
    },
    {
      label: 'Cache Hit Rate',
      value: `${(summary.cache_hit_rate * 100).toFixed(1)}%`,
      sub: `${summary.tokens_saved_by_cache.toLocaleString()} tokens saved`,
      trend: 'up',
    },
    {
      label: 'Avg Latency',
      value: `${summary.avg_latency_ms.toLocaleString()}ms`,
      sub: `p95: ${summary.p95_latency_ms.toLocaleString()}ms`,
      trend: null,
    },
  ] : null

  return (
    <div style={s.row}>
      {CARD_CONFIG.map((cfg, i) => {
        const card = cards?.[i]
        const { Icon } = cfg
        return (
          <div key={i} style={s.card}>
            <div style={s.cardLeft}>
              <p style={s.label}>{card?.label ?? '—'}</p>
              <p style={{ ...s.value, color: cfg.color }}>
                {card?.value ?? <span style={s.skel} />}
              </p>
              <p style={s.sub}>
                {card?.trend === 'down' && <span style={{ color: '#10b981', marginRight: 4 }}>↓</span>}
                {card?.trend === 'up'   && <span style={{ color: '#10b981', marginRight: 4 }}>↑</span>}
                {card?.sub ?? ''}
              </p>
            </div>
            <div style={{ ...s.iconWrap, background: cfg.bg }}>
              <Icon />
            </div>
          </div>
        )
      })}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  row:      { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18 },
  card:     { background: 'var(--card)', borderRadius: 'var(--radius)', padding: '22px 24px', boxShadow: 'var(--shadow)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, border: '1px solid var(--border)' },
  cardLeft: { flex: 1, minWidth: 0 },
  label:    { fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 },
  value:    { fontSize: 30, fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1, marginBottom: 8 },
  sub:      { fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  iconWrap: { width: 52, height: 52, borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' },
  skel:     { display: 'inline-block', width: 80, height: 28, background: 'var(--border)', borderRadius: 6 },
}
