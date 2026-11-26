import { useEffect, useState } from 'react'
import { LuSend, LuListChecks, LuTriangleAlert } from 'react-icons/lu'
import TopBar from '../components/TopBar.jsx'
import StatCard from '../components/StatCard.jsx'
import { complaintsApi } from '../api/client.js'

const prettyName = (name) => name.replace(/_/g, ' ')

function PriorityBadge({ priority }) {
  const urgent = priority === 'urgent'
  return (
    <span
      className={`font-mono text-[11px] uppercase px-2 py-0.5 rounded border ${
        urgent
          ? 'text-signal-danger border-signal-danger/40 bg-signal-danger/10'
          : 'text-ink-muted border-hairline bg-panel-raised'
      }`}
    >
      {priority}
    </span>
  )
}

function ResultCard({ result }) {
  return (
    <div className="glass-panel p-5 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="eyebrow">Result</span>
        <PriorityBadge priority={result.priority} />
        <span className="font-mono text-xs text-ink-faint">{result.priority_reason}</span>
      </div>

      <div>
        <p className="text-xs text-ink-muted">Predicted category</p>
        <p className="font-display font-semibold text-2xl capitalize text-signal-amber">
          {prettyName(result.category)}
        </p>
        <p className="font-mono text-xs text-ink-muted mt-1">
          confidence {(result.category_confidence * 100).toFixed(0)}%
        </p>
      </div>

      {result.needs_review && (
        <div className="flex items-start gap-2 text-signal-amber text-xs border border-signal-amber/30 bg-signal-amber/5 rounded-lg p-3">
          <LuTriangleAlert size={14} className="mt-0.5 shrink-0" />
          Low confidence. This text may be outside the topics the model knows, so a person should check it.
        </div>
      )}

      <div className="space-y-2">
        <p className="text-xs text-ink-muted">Top 3 categories</p>
        {result.top_categories.map((c) => (
          <div key={c.category} className="flex items-center gap-3">
            <span className="text-xs w-36 capitalize text-ink-muted">{prettyName(c.category)}</span>
            <div className="flex-1 h-2 bg-panel-raised rounded-full overflow-hidden">
              <div className="h-full bg-signal-amber rounded-full" style={{ width: `${c.probability * 100}%` }} />
            </div>
            <span className="font-mono text-xs text-ink-muted w-10 text-right">
              {(c.probability * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Complaints() {
  const [text, setText] = useState('')
  const [samples, setSamples] = useState([])
  const [result, setResult] = useState(null)
  const [batch, setBatch] = useState(null)
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    complaintsApi.samples().then((r) => setSamples(r.data)).catch(() => {})
    complaintsApi.modelInfo().then((r) => setInfo(r.data)).catch(() => {})
  }, [])

  async function handleClassify() {
    if (text.trim().length < 3) {
      setError('Please type at least 3 characters.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await complaintsApi.classify(text)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail?.[0]?.msg || 'Could not reach the backend API. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  async function handleBatch() {
    setError(null)
    setLoading(true)
    try {
      const res = await complaintsApi.classifyBatch(samples)
      setBatch(res.data)
    } catch {
      setError('Could not reach the backend API. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <TopBar title="Complaints (NLP)" subtitle="Classify citizen traffic complaints (English) by category and priority" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ---------- Input ---------- */}
        <div className="space-y-4">
          <div className="glass-panel p-5 space-y-3">
            <span className="eyebrow">Complaint Text</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={1000}
              rows={4}
              placeholder="e.g. There is a big pothole near the bus stop and two bikes have already fallen."
              className="w-full bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm"
            />
            {error && <p className="text-signal-danger text-xs">{error}</p>}
            <button onClick={handleClassify} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
              <LuSend size={15} /> {loading ? 'Working…' : 'Classify'}
            </button>
          </div>

          <div className="glass-panel p-5">
            <span className="eyebrow">Try a sample complaint</span>
            <div className="mt-3 flex flex-wrap gap-2">
              {samples.map((s) => (
                <button
                  key={s}
                  onClick={() => setText(s)}
                  className="text-left text-xs text-ink-muted border border-hairline rounded-lg px-3 py-2 hover:border-signal-amber/40 hover:text-ink-primary transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {info && (
            <div className="glass-panel p-5 space-y-2">
              <span className="eyebrow">About this model</span>
              <p className="text-xs text-ink-muted leading-relaxed">{info.model}</p>
              <p className="font-mono text-xs text-ink-muted">
                trained on {info.n_train} sentences · category accuracy {(info.cv_accuracy.category * 100).toFixed(0)}% ·
                priority accuracy {(info.cv_accuracy.priority_with_safety_rule * 100).toFixed(0)}%
              </p>
              <p className="text-ink-faint text-xs">{info.note}</p>
            </div>
          )}
        </div>

        {/* ---------- Output ---------- */}
        <div className="space-y-4">
          {result ? (
            <ResultCard result={result} />
          ) : (
            <div className="glass-panel p-5 text-ink-faint text-sm font-mono text-center py-16">
              Type or pick a complaint, then press Classify.
            </div>
          )}

          <div className="glass-panel p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="eyebrow">Classify all sample complaints</span>
              <button onClick={handleBatch} disabled={loading || samples.length === 0} className="btn-ghost text-xs flex items-center gap-1.5 disabled:opacity-50">
                <LuListChecks size={14} /> Run on {samples.length} samples
              </button>
            </div>

            {batch && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <StatCard label="Complaints" value={batch.results.length} accent="default" />
                  <StatCard label="Urgent" value={batch.urgent_count} accent="danger" />
                  <StatCard label="Need review" value={batch.needs_review_count} accent="amber" />
                </div>
                <div className="space-y-2">
                  {batch.results.map((r) => (
                    <div key={r.text} className="border border-hairline rounded-lg px-3 py-2 bg-panel-raised">
                      <p className="text-xs text-ink-muted">{r.text}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-xs capitalize text-signal-amber">{prettyName(r.category)}</span>
                        <span className="font-mono text-[11px] text-ink-faint">
                          {(r.category_confidence * 100).toFixed(0)}%
                        </span>
                        <PriorityBadge priority={r.priority} />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
