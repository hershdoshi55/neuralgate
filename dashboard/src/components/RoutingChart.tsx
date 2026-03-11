import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { RoutingData } from '../types'

const TIER_COLORS: Record<string, string> = {
  cheap:    '#10b981',
  mid:      '#f59e0b',
  frontier: '#6366f1',
}

interface Props {
  days: number
}

export function RoutingChart({ days }: Props) {
  const [data, setData] = useState<RoutingData | null>(null)

  useEffect(() => {
    fetch(`/api/analytics/routing?days=${days}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
  }, [days])

  const pieData = (data?.by_tier ?? []).map((t) => ({
    name: t.tier.charAt(0).toUpperCase() + t.tier.slice(1),
    rawName: t.tier,
    value: t.requests,
    color: TIER_COLORS[t.tier] ?? '#94a3b8',
    percent: t.percent,
  }))

  return (
    <div style={s.card}>
      <div style={s.header}>
        <div>
          <h3 style={s.title}>Routing Distribution</h3>
          <p style={s.subtitle}>Requests by complexity tier</p>
        </div>
        {data && (
          <span style={s.badge}>
            {data.failover_count} failover{data.failover_count !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {pieData.length === 0 ? (
        <div style={s.empty}>No routing data yet.</div>
      ) : (
        <div style={s.body}>
          <ResponsiveContainer width="50%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%" cy="50%"
                innerRadius={60} outerRadius={95}
                dataKey="value"
                paddingAngle={3}
                strokeWidth={0}
              >
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v: number) => [v, 'requests']}
                contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--shadow-md)', fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div style={s.legend}>
            {pieData.map((d) => (
              <div key={d.name} style={s.legendRow}>
                <span style={{ ...s.dot, background: d.color }} />
                <span style={s.tierName}>{d.name}</span>
                <span style={s.tierVal}>{d.value} req</span>
                <span style={{ ...s.tierPct, color: d.color }}>{d.percent}%</span>
              </div>
            ))}
            {data && (
              <div style={s.failoverRow}>
                <span style={{ ...s.dot, background: 'var(--border)' }} />
                <span style={s.tierName}>Failover rate</span>
                <span style={{ ...s.tierVal, color: data.failover_rate > 0.05 ? '#f59e0b' : 'var(--text-muted)' }}>
                  {(data.failover_rate * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:        { background: 'var(--card)', borderRadius: 'var(--radius)', padding: 24, boxShadow: 'var(--shadow)', border: '1px solid var(--border)' },
  header:      { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title:       { fontSize: 16, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  subtitle:    { fontSize: 12, color: 'var(--text-muted)', marginTop: 3 },
  badge:       { background: 'rgba(245,158,11,0.12)', color: '#d97706', padding: '5px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgba(245,158,11,0.2)', whiteSpace: 'nowrap' },
  body:        { display: 'flex', alignItems: 'center' },
  legend:      { flex: 1, display: 'flex', flexDirection: 'column', gap: 12 },
  legendRow:   { display: 'flex', alignItems: 'center', gap: 8 },
  dot:         { width: 10, height: 10, borderRadius: '50%', flexShrink: 0 },
  tierName:    { fontSize: 13, color: 'var(--text)', flex: 1, fontWeight: 500 },
  tierVal:     { fontSize: 13, color: 'var(--text-muted)' },
  tierPct:     { fontSize: 13, fontWeight: 700, minWidth: 38, textAlign: 'right' as const },
  failoverRow: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, paddingTop: 12, borderTop: '1px solid var(--border)' },
  empty:       { height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 14 },
}
