import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { RoutingData } from '../types'

const TIER_COLORS: Record<string, string> = {
  cheap:    '#22c55e',
  mid:      '#f59e0b',
  frontier: '#6366f1',
}

export function RoutingChart() {
  const [data, setData] = useState<RoutingData | null>(null)

  useEffect(() => {
    fetch('/api/analytics/routing?days=7')
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
  }, [])

  const pieData = (data?.by_tier ?? []).map((t) => ({
    name: t.tier.charAt(0).toUpperCase() + t.tier.slice(1),
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
          <ResponsiveContainer width="55%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} dataKey="value" paddingAngle={3}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => [v, 'requests']} />
            </PieChart>
          </ResponsiveContainer>

          <div style={s.legend}>
            {pieData.map((d) => (
              <div key={d.name} style={s.legendRow}>
                <span style={{ ...s.dot, background: d.color }} />
                <span style={s.tierName}>{d.name}</span>
                <span style={s.tierVal}>{d.value} req · {d.percent}%</span>
              </div>
            ))}
            {data && (
              <div style={s.failoverRow}>
                <span style={s.tierName}>Failover rate</span>
                <span style={s.tierVal}>{(data.failover_rate * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:       { background: '#fff', borderRadius: 10, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  header:     { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title:      { margin: 0, fontSize: 16, fontWeight: 600 },
  subtitle:   { margin: '4px 0 0', fontSize: 12, color: '#6b7280' },
  badge:      { background: '#fef3c7', color: '#d97706', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 },
  body:       { display: 'flex', alignItems: 'center' },
  legend:     { flex: 1, display: 'flex', flexDirection: 'column', gap: 10 },
  legendRow:  { display: 'flex', alignItems: 'center', gap: 8 },
  dot:        { width: 10, height: 10, borderRadius: '50%', flexShrink: 0 },
  tierName:   { fontSize: 13, color: '#374151', flex: 1 },
  tierVal:    { fontSize: 13, color: '#6b7280' },
  failoverRow:{ display: 'flex', gap: 8, marginTop: 8, paddingTop: 8, borderTop: '1px solid #f3f4f6' },
  empty:      { height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 14 },
}
