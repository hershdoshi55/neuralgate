import { useTheme } from '../ThemeContext'

type Page = 'chat' | 'analytics'

interface Props {
  page: Page
  setPage: (p: Page) => void
}

const NAV = [
  { id: 'chat' as Page,      icon: '💬', label: 'Chat' },
  { id: 'analytics' as Page, icon: '📊', label: 'Analytics' },
]

export function Sidebar({ page, setPage }: Props) {
  const { theme, toggle } = useTheme()

  return (
    <aside style={s.sidebar}>
      {/* Logo */}
      <div style={s.logoArea}>
        <div style={s.logoIcon}>N</div>
        <div>
          <div style={s.logoText}>NeuralGate</div>
          <div style={s.logoSub}>LLM Proxy</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={s.nav}>
        <p style={s.navSection}>MAIN MENU</p>
        {NAV.map((item) => {
          const active = page === item.id
          return (
            <button
              key={item.id}
              style={{ ...s.navItem, ...(active ? s.navItemActive : {}) }}
              onClick={() => setPage(item.id)}
            >
              {active && <span style={s.activeBar} />}
              <span style={s.navIcon}>{item.icon}</span>
              <span style={{ ...s.navLabel, color: active ? '#fff' : 'var(--sidebar-text)' }}>
                {item.label}
              </span>
            </button>
          )
        })}
      </nav>

      {/* Bottom */}
      <div style={s.bottom}>
        <button style={s.themeBtn} onClick={toggle}>
          <span style={s.navIcon}>{theme === 'dark' ? '☀️' : '🌙'}</span>
          <span style={{ ...s.navLabel, color: 'var(--sidebar-text)' }}>
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </span>
        </button>
      </div>
    </aside>
  )
}

const s: Record<string, React.CSSProperties> = {
  sidebar:       { width: 240, minHeight: '100vh', background: 'var(--sidebar-bg)', display: 'flex', flexDirection: 'column', flexShrink: 0 },
  logoArea:      { padding: '24px 20px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid rgba(255,255,255,0.05)' },
  logoIcon:      { width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 18, flexShrink: 0 },
  logoText:      { color: '#fff', fontWeight: 700, fontSize: 15 },
  logoSub:       { color: 'var(--sidebar-text)', fontSize: 11, marginTop: 1 },
  nav:           { flex: 1, padding: '16px 12px' },
  navSection:    { color: 'var(--sidebar-text)', fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', padding: '0 8px', marginBottom: 8, marginTop: 8 },
  navItem:       { width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 8, border: 'none', background: 'transparent', cursor: 'pointer', position: 'relative', marginBottom: 2, textAlign: 'left' },
  navItemActive: { background: 'rgba(99,102,241,0.15)' },
  activeBar:     { position: 'absolute', left: 0, top: '20%', bottom: '20%', width: 3, borderRadius: 2, background: '#6366f1' },
  navIcon:       { fontSize: 16, width: 20, textAlign: 'center', flexShrink: 0 },
  navLabel:      { fontSize: 14, fontWeight: 500 },
  bottom:        { padding: '12px', borderTop: '1px solid rgba(255,255,255,0.05)' },
  themeBtn:      { width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 8, border: 'none', background: 'transparent', cursor: 'pointer' },
}
