import { useEffect, useState } from 'react'
import { CostCards } from './components/CostCards'
import { SavingsChart } from './components/SavingsChart'
import { RoutingChart } from './components/RoutingChart'
import { LiveRequestFeed } from './components/LiveRequestFeed'
import type { Summary } from './types'

export default function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    fetch(`/api/analytics/summary?days=${days}`)
      .then((r) => r.json())
      .then(setSummary)
      .catch(console.error)
  }, [days])

  return (
    <div style={s.root}>
      <header style={s.header}>
        <div>
          <h1 style={s.title}>NeuralGate</h1>
          <p style={s.subtitle}>LLM cost-optimization proxy</p>
        </div>
        <div style={s.controls}>
          <span style={s.controlLabel}>Period:</span>
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
      </header>

      <main style={s.main}>
        <CostCards summary={summary} />

        <div style={s.grid2}>
          <SavingsChart />
          <RoutingChart />
        </div>

        <LiveRequestFeed />
      </main>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root:         { minHeight: '100vh', background: '#f8fafc', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' },
  header:       { background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, zIndex: 10 },
  title:        { margin: 0, fontSize: 20, fontWeight: 700, color: '#111827' },
  subtitle:     { margin: '2px 0 0', fontSize: 12, color: '#6b7280' },
  controls:     { display: 'flex', alignItems: 'center', gap: 6 },
  controlLabel: { fontSize: 13, color: '#6b7280', marginRight: 4 },
  pill:         { background: '#f3f4f6', border: 'none', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', fontSize: 13, color: '#374151', fontWeight: 500 },
  pillActive:   { background: '#6366f1', color: '#fff' },
  main:         { maxWidth: 1200, margin: '0 auto', padding: '24px 24px', display: 'flex', flexDirection: 'column', gap: 20 },
  grid2:        { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 },
}
