import { useTheme } from '../ThemeContext'

type Page = 'chat' | 'analytics'

interface Props {
  page: Page
  setPage: (p: Page) => void
}

function ChatIcon({ active }: { active: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke={active ? '#fff' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}

function AnalyticsIcon({ active }: { active: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke={active ? '#fff' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
      <line x1="3" y1="20" x2="21" y2="20"/>
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}

const NAV = [
  { id: 'chat' as Page,      Icon: ChatIcon,      label: 'Chat' },
  { id: 'analytics' as Page, Icon: AnalyticsIcon, label: 'Analytics' },
]

export function Sidebar({ page, setPage }: Props) {
  const { theme, toggle } = useTheme()

  return (
    <aside style={s.sidebar}>
      {/* Logo */}
      <div style={s.logoArea}>
        <div style={s.logoIcon}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        </div>
        <div>
          <div style={s.logoText}>NeuralGate</div>
          <div style={s.logoSub}>LLM Proxy</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={s.nav}>
        <p style={s.navSection}>MAIN MENU</p>
        {NAV.map(({ id, Icon, label }) => {
          const active = page === id
          return (
            <button
              key={id}
              style={{ ...s.navItem, ...(active ? s.navItemActive : {}) }}
              onClick={() => setPage(id)}
            >
              {active && <span style={s.activeBar} />}
              <span style={{ ...s.navIcon, color: active ? '#fff' : 'var(--sidebar-text)' }}>
                <Icon active={active} />
              </span>
              <span style={{ ...s.navLabel, color: active ? '#fff' : 'var(--sidebar-text)' }}>
                {label}
              </span>
            </button>
          )
        })}
      </nav>

      {/* Bottom */}
      <div style={s.bottom}>
        <div style={s.liveDot}>
          <span style={s.dot} />
          <span style={s.liveText}>Live</span>
        </div>
        <button style={s.themeBtn} onClick={toggle}>
          <span style={{ color: 'var(--sidebar-text)', display: 'flex' }}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </span>
          <span style={{ ...s.navLabel, color: 'var(--sidebar-text)' }}>
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </span>
        </button>
      </div>
    </aside>
  )
}

const s: Record<string, React.CSSProperties> = {
  sidebar:       { width: 248, minHeight: '100vh', background: 'var(--sidebar-bg)', display: 'flex', flexDirection: 'column', flexShrink: 0, borderRight: '1px solid rgba(255,255,255,0.04)' },
  logoArea:      { padding: '22px 20px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 4 },
  logoIcon:      { width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 4px 12px rgba(99,102,241,0.4)' },
  logoText:      { color: '#fff', fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em' },
  logoSub:       { color: 'var(--sidebar-text)', fontSize: 11, marginTop: 2, letterSpacing: '0.01em' },
  nav:           { flex: 1, padding: '8px 12px' },
  navSection:    { color: 'rgba(139,149,176,0.6)', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', padding: '12px 10px 8px', textTransform: 'uppercase' },
  navItem:       { width: '100%', display: 'flex', alignItems: 'center', gap: 11, padding: '10px 12px', borderRadius: 9, border: 'none', background: 'transparent', cursor: 'pointer', position: 'relative', marginBottom: 2, textAlign: 'left', transition: 'background 0.15s' },
  navItemActive: { background: 'rgba(99,102,241,0.2)' },
  activeBar:     { position: 'absolute', left: 0, top: '18%', bottom: '18%', width: 3, borderRadius: 10, background: '#6366f1' },
  navIcon:       { display: 'flex', alignItems: 'center', width: 20, flexShrink: 0 },
  navLabel:      { fontSize: 14, fontWeight: 500 },
  bottom:        { padding: '12px', borderTop: '1px solid rgba(255,255,255,0.06)' },
  liveDot:       { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px 4px', marginBottom: 4 },
  dot:           { width: 7, height: 7, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 6px #22c55e', flexShrink: 0 },
  liveText:      { fontSize: 11, color: '#22c55e', fontWeight: 600, letterSpacing: '0.05em' },
  themeBtn:      { width: '100%', display: 'flex', alignItems: 'center', gap: 11, padding: '10px 12px', borderRadius: 9, border: 'none', background: 'transparent', cursor: 'pointer', transition: 'background 0.15s' },
}
