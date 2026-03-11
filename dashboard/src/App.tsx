import { useEffect, useState } from 'react'
import { ThemeProvider } from './ThemeContext'
import { Sidebar } from './components/Sidebar'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { ChatPage } from './pages/ChatPage'
import type { Summary } from './types'

type Page = 'chat' | 'analytics'

function Shell() {
  const [page, setPage] = useState<Page>('chat')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    fetch(`/api/analytics/summary?days=${days}`)
      .then(r => r.json())
      .then(setSummary)
      .catch(console.error)
  }, [days])

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar page={page} setPage={setPage} />
      <main style={{ flex: 1, padding: 28, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {page === 'analytics'
          ? <AnalyticsPage summary={summary} days={days} setDays={setDays} />
          : <ChatPage />
        }
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <Shell />
    </ThemeProvider>
  )
}
