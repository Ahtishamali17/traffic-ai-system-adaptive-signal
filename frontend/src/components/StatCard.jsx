import { motion } from 'framer-motion'

/**
 * A single metric card: label, big mono value, optional trend/unit,
 * optional icon. Used across Dashboard, Analytics, Live Detection.
 */
export default function StatCard({ label, value, unit, icon: Icon, accent = 'amber', delay = 0 }) {
  const accentColor = {
    amber: 'text-signal-amber',
    danger: 'text-signal-danger',
    safe: 'text-signal-safe',
    default: 'text-ink-primary',
  }[accent]

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="glass-panel p-5 relative overflow-hidden"
    >
      <div className="flex items-start justify-between">
        <span className="eyebrow">{label}</span>
        {Icon && <Icon className={`${accentColor} opacity-70`} size={18} />}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className={`stat-value ${accentColor}`}>{value}</span>
        {unit && <span className="text-ink-muted text-sm font-mono">{unit}</span>}
      </div>
    </motion.div>
  )
}
