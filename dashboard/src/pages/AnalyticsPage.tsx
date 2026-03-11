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
  page:       { display: 'flex', flexDirection: 'column', gap: 20 },
  header:     { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' },
  title:      { fontSize: 22, fontWeight: 700, color: 'var(--text)' },
  sub:        { fontSize: 13, color: 'var(--text-muted)', marginTop: 2 },
  pills:      { display: 'flex', gap: 6 },
  pill:       { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 14px', cursor: 'pointer', fontSize: 13, color: 'var(--text-muted)', fontWeight: 500, transition: 'all 0.15s' },
  pillActive: { background: '#6366f1', borderColor: '#6366f1', color: '#fff' },
  grid2:      { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 },
}
