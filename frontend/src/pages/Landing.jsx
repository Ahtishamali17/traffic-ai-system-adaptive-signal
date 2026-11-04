import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LuArrowRight, LuRadar, LuGauge, LuTriangleAlert, LuNetwork } from 'react-icons/lu'

const FEATURES = [
  {
    icon: LuRadar,
    title: 'Multi-Class Detection',
    body: 'YOLOv8 identifies cars, trucks, buses, motorcycles, bicycles, and more — across CCTV, dashcam, drone, and webcam feeds.',
  },
  {
    icon: LuNetwork,
    title: 'Persistent Tracking',
    body: 'DeepSORT assigns every vehicle a permanent ID, following it through occlusion until it leaves the frame.',
  },
  {
    icon: LuGauge,
    title: 'Speed & Violations',
    body: 'Calibrated speed estimation flags overspeeding, wrong-direction travel, lane violations, and illegal U-turns in real time.',
  },
  {
    icon: LuTriangleAlert,
    title: 'Instant Alerts',
    body: 'Telegram and email notifications fire the moment a violation or crowd threshold is crossed — no polling required.',
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-void overflow-x-hidden">
      {/* ---------------- HERO ---------------- */}
      <section className="relative h-screen flex flex-col overflow-hidden bg-grid-lines bg-grid">
        <nav className="relative z-10 flex items-center justify-between px-8 py-6">
          <div className="flex items-center gap-2">
            <LuRadar className="text-signal-amber" size={22} />
            <span className="font-display font-semibold text-lg">Sentry</span>
          </div>
          <Link to="/dashboard" className="btn-ghost text-sm">
            Open Dashboard
          </Link>
        </nav>

        <div className="relative flex-1 flex items-center px-8">
          {/* Radar sweep signature element */}
          <div className="absolute right-[8%] top-1/2 -translate-y-1/2 w-[420px] h-[420px] hidden lg:block pointer-events-none">
            <div className="absolute inset-0 rounded-full border border-hairline" />
            <div className="absolute inset-[15%] rounded-full border border-hairline" />
            <div className="absolute inset-[30%] rounded-full border border-hairline" />
            <div className="absolute inset-[45%] rounded-full border border-signal-amber/30" />
            <motion.div
              className="absolute inset-0 rounded-full overflow-hidden"
              style={{
                background:
                  'conic-gradient(from 0deg, rgba(245,166,35,0) 0deg, rgba(245,166,35,0) 300deg, rgba(245,166,35,0.35) 360deg)',
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            />
            {[
              { top: '30%', left: '55%', delay: 0 },
              { top: '62%', left: '35%', delay: 0.8 },
              { top: '45%', left: '70%', delay: 1.6 },
              { top: '70%', left: '60%', delay: 2.4 },
            ].map((blip, i) => (
              <span
                key={i}
                className="absolute w-2 h-2 rounded-full bg-signal-amber animate-blip"
                style={{ top: blip.top, left: blip.left, animationDelay: `${blip.delay}s` }}
              />
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="relative z-10 max-w-2xl"
          >
            <span className="eyebrow">Real-Time Vehicle Intelligence</span>
            <h1 className="font-display font-semibold text-5xl md:text-6xl leading-[1.05] mt-4 tracking-tight">
              Every vehicle,
              <br />
              tracked and
              <br />
              <span className="text-signal-amber">understood.</span>
            </h1>
            <p className="mt-6 text-ink-muted text-lg max-w-md leading-relaxed">
              Sentry watches your cameras so you don't have to — detecting, tracking, and
              flagging traffic behavior across every feed, in real time.
            </p>
            <div className="mt-8 flex items-center gap-4">
              <Link to="/dashboard" className="btn-primary flex items-center gap-2">
                Open Dashboard <LuArrowRight size={16} />
              </Link>
              <Link to="/about" className="text-sm text-ink-muted hover:text-ink-primary transition-colors">
                How it works
              </Link>
            </div>
          </motion.div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-hairline to-transparent" />
      </section>

      {/* ---------------- FEATURES ---------------- */}
      <section className="px-8 py-24 max-w-6xl mx-auto">
        <span className="eyebrow">Capabilities</span>
        <h2 className="font-display font-semibold text-3xl mt-3 mb-12 max-w-lg">
          Built for the demands of live traffic monitoring.
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {FEATURES.map(({ icon: Icon, title, body }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="glass-panel p-6"
            >
              <Icon className="text-signal-amber mb-4" size={22} />
              <h3 className="font-display font-semibold text-lg mb-2">{title}</h3>
              <p className="text-ink-muted text-sm leading-relaxed">{body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <footer className="px-8 py-8 border-t border-hairline text-center">
        <p className="font-mono text-xs text-ink-faint">
          Sentry Traffic Monitoring System — built on YOLOv8 + DeepSORT
        </p>
      </footer>
    </div>
  )
}
