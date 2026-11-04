import { LuCircle } from 'react-icons/lu'

export default function TopBar({ title, subtitle }) {
  return (
    <header className="h-16 flex items-center justify-between px-6 border-b border-hairline bg-panel/30 backdrop-blur-sm shrink-0">
      <div>
        <h1 className="font-display font-semibold text-lg leading-tight">{title}</h1>
        {subtitle && <p className="text-xs text-ink-muted mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2 font-mono text-xs text-ink-muted">
        <LuCircle className="text-signal-safe fill-signal-safe animate-pulse" size={8} />
        SYSTEM ONLINE
      </div>
    </header>
  )
}
