import type { Summary } from '../types'
import { CostCards } from '../components/CostCards'
import { SavingsChart } from '../components/SavingsChart'
import { RoutingChart } from '../components/RoutingChart'
import { LiveRequestFeed } from '../components/LiveRequestFeed'

interface Props {
  summary: Summary | null
  days: number
  setDays: (d: number) => void
}

export function AnalyticsPage({ summary, days, setDays }: Props) {
  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <h2 style={s.title}>Analytics</h2>
          <p style={s.sub}>Cost optimization and routing insights</p>
        </div>
        <div style={s.pills}>
          {([1, 7, 30] as const).map((d) => (
            <button
              key={d}
              style={{ ...s.pill, ...(days === d ? s.pillActive : {}) }}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      <CostCards summary={summary} />

      <div style={s.grid2}>
        <SavingsChart days={days} />
        <RoutingChart days={days} />
      </div>

      <LiveRequestFeed />
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page:       { display: 'flex', flexDirection: 'column', gap: 22, flex: 1 },
  header:     { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' },
  title:      { fontSize: 24, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' },
  sub:        { fontSize: 13, color: 'var(--text-muted)', marginTop: 3, fontWeight: 400 },
  pills:      { display: 'flex', gap: 4, background: 'var(--card)', padding: 4, borderRadius: 10, border: '1px solid var(--border)' },
  pill:       { background: 'transparent', border: 'none', borderRadius: 7, padding: '5px 16px', cursor: 'pointer', fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, transition: 'all 0.15s' },
  pillActive: { background: '#6366f1', color: '#fff', boxShadow: '0 2px 8px rgba(99,102,241,0.35)' },
  grid2:      { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 },
}
