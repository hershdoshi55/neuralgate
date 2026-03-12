import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { SavingsData } from '../types'
import { apiFetch } from '../api'

interface Props {
  days: number
}

export function SavingsChart({ days }: Props) {
  const [data, setData] = useState<SavingsData | null>(null)

  useEffect(() => {
    apiFetch(`/api/analytics/savings?days=${days}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
  }, [days])

  const rows = data?.daily_savings ?? []

  return (
    <div style={s.card}>
      <div style={s.header}>
        <div>
          <h3 style={s.title}>Cost: Actual vs All-Frontier</h3>
          <p style={s.subtitle}>Green area = money saved by intelligent routing</p>
        </div>
        {data && (
          <div style={s.badge}>
            <span style={{ color: '#3b82f6', fontWeight: 700 }}>{data.savings_percent}% saved</span>
            <span style={s.badgeDivider}>·</span>
            <span>${data.total_savings_usd.toFixed(4)} total</span>
          </div>
        )}
      </div>
      {rows.length === 0 ? (
        <div style={s.empty}>No data yet — send some requests first.</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={rows} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="colorSavings" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.35}/>
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05}/>
              </linearGradient>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={(v: number) => `$${v.toFixed(3)}`} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} width={65} />
            <Tooltip
              formatter={(v: number, n: string) => [`$${v.toFixed(6)}`, n]}
              contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--shadow-md)', fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            <Area type="monotone" dataKey="hypothetical" stroke="#93c5fd" strokeDasharray="5 5" strokeWidth={2} fill="url(#colorSavings)" name="If all-frontier" dot={false} />
            <Area type="monotone" dataKey="actual"       stroke="#3b82f6" strokeWidth={2.5}   fill="url(#colorActual)"   name="Actual cost"    dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:         { background: 'var(--card)', borderRadius: 'var(--radius)', padding: 24, boxShadow: 'var(--shadow)', border: '1px solid var(--border)' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  title:        { fontSize: 16, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  subtitle:     { fontSize: 12, color: 'var(--text-muted)', marginTop: 3 },
  badge:        { display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(59,130,246,0.1)', color: 'var(--text-muted)', padding: '6px 12px', borderRadius: 20, fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', border: '1px solid rgba(59,130,246,0.2)' },
  badgeDivider: { color: 'var(--border)' },
  empty:        { height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 14 },
}
