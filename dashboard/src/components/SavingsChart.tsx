import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { SavingsData } from '../types'

interface Props {
  days: number
}

export function SavingsChart({ days }: Props) {
  const [data, setData] = useState<SavingsData | null>(null)

  useEffect(() => {
    fetch(`/api/analytics/savings?days=${days}`)
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
            {data.savings_percent}% saved &nbsp;·&nbsp; ${data.total_savings_usd.toFixed(4)} total
          </div>
        )}
      </div>
      {rows.length === 0 ? (
        <div style={s.empty}>No data yet — send some requests first.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v: number) => `$${v.toFixed(4)}`} tick={{ fontSize: 11 }} width={70} />
            <Tooltip formatter={(v: number, n: string) => [`$${v.toFixed(6)}`, n]} />
            <Legend />
            <Line type="monotone" dataKey="hypothetical" stroke="#ef4444" strokeDasharray="5 5" name="If all-frontier" dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="actual"       stroke="#22c55e" name="Actual cost"    dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card:     { background: 'var(--card)', borderRadius: 10, padding: 24, boxShadow: 'var(--shadow)' },
  header:   { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title:    { margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text)' },
  subtitle: { margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' },
  badge:    { background: '#f0fdf4', color: '#16a34a', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' },
  empty:    { height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 14 },
}
