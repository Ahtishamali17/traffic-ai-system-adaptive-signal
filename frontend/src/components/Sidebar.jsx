import { NavLink } from 'react-router-dom'
import {
  LuLayoutDashboard,
  LuVideo,
  LuChartLine,
  LuFileText,
  LuSettings,
  LuInfo,
  LuRadar,
} from 'react-icons/lu'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LuLayoutDashboard },
  { to: '/live', label: 'Live Detection', icon: LuVideo },
  { to: '/analytics', label: 'Analytics', icon: LuChartLine },
  { to: '/reports', label: 'Reports', icon: LuFileText },
  { to: '/settings', label: 'Settings', icon: LuSettings },
  { to: '/about', label: 'About', icon: LuInfo },
]

export default function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-64 flex-col border-r border-hairline bg-panel/50 backdrop-blur-md shrink-0">
      <div className="h-16 flex items-center gap-2 px-6 border-b border-hairline">
        <LuRadar className="text-signal-amber shrink-0" size={22} />
        <span className="font-display font-semibold text-lg tracking-tight">Sentry</span>
      </div>

      <nav className="flex-1 px-3 py-6 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-signal-amber/10 text-signal-amber border border-signal-amber/20'
                  : 'text-ink-muted hover:text-ink-primary hover:bg-panel-raised'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-6 py-4 border-t border-hairline">
        <p className="font-mono text-[10px] text-ink-faint tracking-wide">
          v1.0.0 · BUILD PRODUCTION
        </p>
      </div>
    </aside>
  )
}
