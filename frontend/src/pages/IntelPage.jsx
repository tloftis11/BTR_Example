import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format, formatDistanceToNow } from 'date-fns'
import {
  getSummary, getAnomalies, getPipelineRuns, getLatestBriefing, sendChatMessage,
} from '../api/client'

const STREAM_LABELS = {
  nwss: 'NWSS', tgs: 'TGS', sbd: 'SBD', hmp: 'HMP',
  who: 'WHO', nao: 'NAO', nst: 'NST',
}
const STREAM_COLORS = {
  nwss: 'var(--nwss)', tgs: 'var(--tgs)', sbd: 'var(--sbd)', hmp: 'var(--hmp)',
  who: 'var(--who)',  nao: 'var(--nao)', nst: 'var(--nst)',
}

export default function IntelPage() {
  const [view, setView]         = useState('briefing')
  const [briefing, setBriefing] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const messagesEndRef           = useRef(null)

  const { data: summary }   = useQuery({ queryKey: ['summary'],   queryFn: getSummary,     refetchInterval: 60_000 })
  const { data: anomalies } = useQuery({ queryKey: ['anomalies'], queryFn: () => getAnomalies({ active_only: true, limit: 20 }) })
  const { data: runs }      = useQuery({ queryKey: ['runs'],      queryFn: getPipelineRuns, refetchInterval: 30_000 })

  const briefingMut = useMutation({
    mutationFn: getLatestBriefing,
    onSuccess: (data) => {
      if (data?.briefing) setBriefing(data.briefing)
      else setBriefing(`Error: ${data?.error || 'No response from server.'}`)
    },
    onError: (err) => setBriefing(`Error: ${err.message}`),
  })

  const chatMut = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      const reply = data?.reply || `Error: ${data?.error || 'No response from server.'}`
      setMessages(prev => [...prev, { role: 'assistant', content: reply }])
    },
    onError: (err) => {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || chatMut.isPending) return
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    chatMut.mutate([...messages, userMsg])
  }

  // Latest run per source
  const latestRuns = runs
    ? Object.values(runs.reduce((acc, r) => { if (!acc[r.source]) acc[r.source] = r; return acc }, {}))
    : []

  const activeCount = anomalies?.length || 0
  const alertTotal  = (summary?.hmp_events_30d || 0) + (summary?.who_events_30d || 0)

  return (
    <div className="intel-layout">
      {/* ── Sidebar: live data context ──────────────────────────── */}
      <div className="intel-sidebar">
        <div className="intel-sidebar-section">
          <div className="intel-sidebar-label">Surveillance State</div>
          <div className="intel-stat">
            <span className="intel-stat-label">NWSS Detection</span>
            <span className="intel-stat-value">
              {summary?.nwss_national_detect_prop != null
                ? `${(summary.nwss_national_detect_prop * 100).toFixed(1)}%`
                : '—'}
            </span>
          </div>
          <div className="intel-stat">
            <span className="intel-stat-label">Active Anomalies</span>
            <span className="intel-stat-value" style={{ color: activeCount > 0 ? 'var(--warn)' : undefined }}>
              {activeCount}
            </span>
          </div>
          <div className="intel-stat">
            <span className="intel-stat-label">Global Alerts (30d)</span>
            <span className="intel-stat-value">{alertTotal || '—'}</span>
          </div>
          <div className="intel-stat">
            <span className="intel-stat-label">TGS Updated</span>
            <span className="intel-stat-value" style={{ fontSize: 12 }}>
              {summary?.latest_tgs_date ? format(new Date(summary.latest_tgs_date), 'MMM d') : '—'}
            </span>
          </div>
          <div className="intel-stat">
            <span className="intel-stat-label">NWSS Updated</span>
            <span className="intel-stat-value" style={{ fontSize: 12 }}>
              {summary?.latest_nwss_date ? format(new Date(summary.latest_nwss_date), 'MMM d') : '—'}
            </span>
          </div>
        </div>

        {activeCount > 0 && (
          <div className="intel-sidebar-section">
            <div className="intel-sidebar-label">Active Anomalies</div>
            {(anomalies || []).slice(0, 6).map((a, i) => (
              <div key={i} className="intel-anomaly">
                <span className="badge badge-crit" style={{ fontSize: 9, padding: '0.1rem 0.3rem' }}>
                  z={a.z_score?.toFixed(1)}
                </span>
                <span className="intel-anomaly-text">
                  {a.source?.toUpperCase()} · {a.site_name || a.site_id}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="intel-sidebar-section">
          <div className="intel-sidebar-label">Pipeline Status</div>
          {latestRuns.length === 0
            ? <span className="intel-stat-label">No runs recorded</span>
            : latestRuns.map(r => (
              <div key={r.source} className="intel-pipeline-item">
                <span className="intel-pipeline-src" style={{ color: STREAM_COLORS[r.source] || 'var(--tx)' }}>
                  {STREAM_LABELS[r.source] || r.source?.toUpperCase()}
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                  <span className={`badge ${r.status === 'success' ? 'badge-ok' : r.status === 'error' ? 'badge-crit' : 'badge-warn'}`} style={{ fontSize: 9 }}>
                    {r.status}
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--tx-faint)' }}>
                    {r.started_at ? formatDistanceToNow(new Date(r.started_at), { addSuffix: true }) : ''}
                  </span>
                </div>
              </div>
            ))
          }
        </div>

        <div className="intel-sidebar-section" style={{ fontSize: 11, color: 'var(--tx-faint)', fontFamily: 'var(--mono)', lineHeight: 1.6 }}>
          <div className="intel-sidebar-label">Data Sources</div>
          <div>NWSS · TGS · SBD · HMP (ReliefWeb) · WHO DON · NAO (NCBI SRA) · NST (Nextstrain)</div>
        </div>
      </div>

      {/* ── Main chat interface ─────────────────────────────────── */}
      <div className="intel-main">
        <div className="intel-topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div className="intel-tabs">
              <button
                className={`intel-tab${view === 'briefing' ? ' active' : ''}`}
                onClick={() => setView('briefing')}
              >
                Situation Briefing
              </button>
              <button
                className={`intel-tab${view === 'chat' ? ' active' : ''}`}
                onClick={() => setView('chat')}
              >
                Ask the Data
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {view === 'briefing' && (
              <button
                className="briefing-btn"
                onClick={() => briefingMut.mutate()}
                disabled={briefingMut.isPending}
              >
                {briefingMut.isPending ? 'Generating…' : '⬡ Generate Briefing'}
              </button>
            )}
            {view === 'briefing' && briefing && (
              <button
                className="briefing-btn"
                onClick={() => setBriefing(null)}
                style={{ color: 'var(--tx-faint)', background: 'transparent', borderColor: 'var(--border)' }}
              >
                Clear
              </button>
            )}
            {view === 'chat' && messages.length > 0 && (
              <button
                className="briefing-btn"
                onClick={() => setMessages([])}
                style={{ color: 'var(--tx-faint)', background: 'transparent', borderColor: 'var(--border)' }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="intel-content">
          {/* Briefing view */}
          {view === 'briefing' && (
            briefing
              ? <div className="intel-briefing">{briefing}</div>
              : <div className="intel-empty">
                  {briefingMut.isPending
                    ? 'Analyzing 7 surveillance streams…'
                    : 'Click "Generate Briefing" to get an AI-synthesized situation report across all active data streams — wastewater, genomics, global alerts, and metagenomic signals.'
                  }
                </div>
          )}

          {/* Chat view */}
          {view === 'chat' && (
            <>
              <div className="intel-messages">
                {messages.length === 0 && (
                  <div className="intel-empty">
                    Ask questions about the surveillance data. Try: "Which SARS-CoV-2 variants are rising?", "Are there concordant signals across streams?", "What does the NWSS trend suggest?", or "Summarize the H5N1 genomic situation."
                  </div>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`intel-msg ${m.role}`}>{m.content}</div>
                ))}
                {chatMut.isPending && (
                  <div className="intel-msg assistant loading">Analyzing surveillance data…</div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="intel-input-row">
                <input
                  className="intel-input"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
                  }}
                  placeholder="Ask about the surveillance data…"
                  disabled={chatMut.isPending}
                />
                <button
                  className="intel-send-btn"
                  onClick={handleSend}
                  disabled={!input.trim() || chatMut.isPending}
                >
                  Send
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
