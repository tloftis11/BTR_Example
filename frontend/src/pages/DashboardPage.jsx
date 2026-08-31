import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, formatDistanceToNow } from 'date-fns'
import {
  getSummary, getSignalSites, getAnomalies,
  getTimeseries, getVariants, getPipelineRuns,
} from '../api/client'
import SiteMap from '../components/Dashboard/SiteMap'
import AnomalyTable from '../components/Dashboard/AnomalyTable'
import SignalChart from '../components/Dashboard/SignalChart'
import VariantChart from '../components/Dashboard/VariantChart'
import ChatPanel from '../components/Dashboard/ChatPanel'

const WEEKS = 13

// Stream definitions — label, color token, primary metric for chart
const STREAMS = {
  nwss: { label: 'NWSS',   color: 'var(--nwss)', metric: 'detect_prop_15d',   title: 'Wastewater Detection',        sub: 'detect_prop_15d · national avg' },
  tgs:  { label: 'TGS',    color: 'var(--tgs)',  metric: 'variant_proportion', title: 'Variant Proportions',         sub: 'stacked by variant · airports' },
  sbd:  { label: 'SBD',    color: 'var(--sbd)',  metric: 'novelty_score',      title: 'Environmental Metagenomic',   sub: 'novelty score' },
  hmp:  { label: 'HMP',    color: 'var(--hmp)',  metric: 'alert_count',        title: 'Global Epidemic Events',      sub: 'ReliefWeb / UN OCHA · epidemics' },
  who:  { label: 'WHO',    color: 'var(--who)',  metric: 'outbreak_event',     title: 'WHO Outbreak Events',         sub: 'declared DON events' },
  nao:  { label: 'NAO',    color: 'var(--nao)',  metric: 'sequencing_runs',    title: 'NAO Metagenomics',            sub: 'NCBI SRA · PRJNA729801' },
  nst:  { label: 'NST',    color: 'var(--nst)',  metric: 'h5n1_sequences',     title: 'Nextstrain Genomics',         sub: 'H5N1 sequences by country' },
}

const ALL_SOURCES = Object.keys(STREAMS)
const INITIAL_ACTIVE = { nwss: true, tgs: true, sbd: true, hmp: true, who: true, nao: true, nst: true }

export default function DashboardPage() {
  const [active, setActive] = useState(INITIAL_ACTIVE)
  const toggle = (s) => setActive(prev => ({ ...prev, [s]: !prev[s] }))

  const { data: summary }   = useQuery({ queryKey: ['summary'],   queryFn: getSummary,     refetchInterval: 60_000 })
  const { data: runs }      = useQuery({ queryKey: ['runs'],      queryFn: getPipelineRuns, refetchInterval: 15_000 })
  const { data: sites }     = useQuery({ queryKey: ['sites'],     queryFn: getSignalSites })
  const { data: anomalies, isLoading: loadAnomaly } = useQuery({
    queryKey: ['anomalies'], queryFn: () => getAnomalies({ active_only: true, limit: 100 }),
  })

  // NWSS timeseries
  const { data: nwssTs, isLoading: loadNwss } = useQuery({
    queryKey: ['ts', 'nwss'], enabled: active.nwss,
    queryFn: () => getTimeseries({ source: 'nwss', metric: 'detect_prop_15d', weeks: WEEKS }),
  })
  // TGS variants (stacked)
  const { data: variants, isLoading: loadTgs } = useQuery({
    queryKey: ['variants'], enabled: active.tgs,
    queryFn: () => getVariants({ weeks: WEEKS }),
  })
  // SBD
  const { data: sbdTs, isLoading: loadSbd } = useQuery({
    queryKey: ['ts', 'sbd'], enabled: active.sbd,
    queryFn: () => getTimeseries({ source: 'sbd', metric: 'novelty_score', weeks: WEEKS }),
  })
  // HealthMap
  const { data: hmpTs, isLoading: loadHmp } = useQuery({
    queryKey: ['ts', 'hmp'], enabled: active.hmp,
    queryFn: () => getTimeseries({ source: 'hmp', metric: 'alert_count', weeks: WEEKS }),
  })
  // WHO DON
  const { data: whoTs, isLoading: loadWho } = useQuery({
    queryKey: ['ts', 'who'], enabled: active.who,
    queryFn: () => getTimeseries({ source: 'who', metric: 'outbreak_event', weeks: WEEKS }),
  })
  // NAO
  const { data: naoTs, isLoading: loadNao } = useQuery({
    queryKey: ['ts', 'nao'], enabled: active.nao,
    queryFn: () => getTimeseries({ source: 'nao', metric: 'sequencing_runs', weeks: WEEKS }),
  })
  // Nextstrain H5N1
  const { data: nstTs, isLoading: loadNst } = useQuery({
    queryKey: ['ts', 'nst'], enabled: active.nst,
    queryFn: () => getTimeseries({ source: 'nst', metric: 'h5n1_sequences', weeks: WEEKS }),
  })

  const filteredSites  = (sites || []).filter(s => active[s.source])
  const activeAnomalies = (anomalies || []).length
  const nwssDetectPct  = summary?.nwss_national_detect_prop != null
    ? `${(summary.nwss_national_detect_prop * 100).toFixed(1)}%`
    : '—'

  // Chart entries for active non-TGS streams
  const CHARTS = [
    { key: 'nwss', data: nwssTs,  loading: loadNwss, type: 'line' },
    { key: 'tgs',  data: variants, loading: loadTgs, type: 'variant' },
    { key: 'sbd',  data: sbdTs,   loading: loadSbd,  type: 'line' },
    { key: 'hmp',  data: hmpTs,   loading: loadHmp,  type: 'line' },
    { key: 'who',  data: whoTs,   loading: loadWho,  type: 'line' },
    { key: 'nao',  data: naoTs,   loading: loadNao,  type: 'line' },
    { key: 'nst',  data: nstTs,   loading: loadNst,  type: 'line' },
  ].filter(c => active[c.key])

  return (
    <>
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <div className="page-title">Biosurveillance Dashboard</div>
          <div className="page-sub">7-stream global threat intelligence fusion</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}>streams:</span>
          <div className="stream-tabs">
            {ALL_SOURCES.map(s => (
              <button
                key={s}
                onClick={() => toggle(s)}
                className={`stream-tab${active[s] ? ` active-${s}` : ''}`}
              >
                <span className="stream-dot" style={{ background: STREAMS[s].color }} />
                {STREAMS[s].label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Stat tiles ─────────────────────────────────────────── */}
      <div className="stat-row">
        <div className="stat-tile">
          <div className="stat-label">Active Anomalies</div>
          <div className={`stat-value ${activeAnomalies > 0 ? 'warn' : 'ok'}`}>
            {activeAnomalies}
          </div>
          <div className="stat-meta">across all streams · past 14 days</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">NWSS Detection</div>
          <div className="stat-value">{nwssDetectPct}</div>
          <div className="stat-meta">
            wastewater avg ·{' '}
            {summary?.latest_nwss_date ? format(new Date(summary.latest_nwss_date), 'MMM d') : '—'}
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Global Alert Events</div>
          <div className={`stat-value ${(summary?.hmp_events_30d || 0) + (summary?.who_events_30d || 0) > 5 ? 'warn' : ''}`}>
            {((summary?.hmp_events_30d || 0) + (summary?.who_events_30d || 0)) || '—'}
          </div>
          <div className="stat-meta">HealthMap + WHO DON · 30 days</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">TGS Last Update</div>
          <div className="stat-value" style={{ fontSize: 18 }}>
            {summary?.latest_tgs_date ? format(new Date(summary.latest_tgs_date), 'MMM d') : '—'}
          </div>
          <div className="stat-meta">variant proportions · airports</div>
        </div>
      </div>

      {/* ── AI Intelligence Panel ───────────────────────────────── */}
      <div className="card" style={{ borderColor: 'var(--ac-mid)' }}>
        <div className="card-header">
          <span className="card-title">
            <span style={{ color: 'var(--ac)', fontSize: 10, fontFamily: 'var(--mono)', letterSpacing: '0.06em', marginRight: 6 }}>⬡ AI</span>
            Intelligence Analysis
          </span>
          <span style={{ fontSize: 11, color: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}>
            powered by Claude · live DB context
          </span>
        </div>
        <div className="card-body">
          <ChatPanel />
        </div>
      </div>

      {/* ── Map + Anomaly table ─────────────────────────────────── */}
      <div className="mid-row">
        <div className="card map-card">
          <div className="card-header">
            <span className="card-title">Global Monitoring Sites</span>
            <span style={{ fontSize: 11, color: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}>
              {filteredSites.length} sites · red = active anomaly
            </span>
          </div>
          <div className="card-body">
            <SiteMap sites={filteredSites} />
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div className="card-header">
            <span className="card-title">Active Anomalies</span>
            {activeAnomalies > 0 && <span className="badge badge-warn">{activeAnomalies}</span>}
          </div>
          <div className="card-body no-pad" style={{ flex: 1, overflowY: 'auto' }}>
            <AnomalyTable anomalies={anomalies} loading={loadAnomaly} />
          </div>
        </div>
      </div>

      {/* ── Signal charts ───────────────────────────────────────── */}
      {CHARTS.length > 0 && (
        <div className="chart-grid">
          {CHARTS.map(({ key, data, loading, type }) => {
            const s = STREAMS[key]
            return (
              <div key={key} className="card chart-card">
                <div className="card-header">
                  <span className="card-title">
                    <span className="stream-dot" style={{ background: s.color }} />
                    {s.title}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}>
                    {s.sub}
                  </span>
                </div>
                <div className="card-body">
                  {type === 'variant'
                    ? <VariantChart data={data} loading={loading} />
                    : <SignalChart data={data} source={key} metric={s.metric} loading={loading} />
                  }
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Pipeline status ─────────────────────────────────────── */}
      {runs && runs.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Pipeline Status</span>
            <span style={{ fontSize: 10, color: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}>
              refreshes every 15s
            </span>
          </div>
          <div className="pipeline-grid">
            {/* Deduplicate: show only the most recent run per source */}
            {Object.values(
              runs.reduce((acc, r) => {
                if (!acc[r.source]) acc[r.source] = r
                return acc
              }, {})
            ).map(r => {
              const color = STREAMS[r.source]?.color || 'var(--tx-faint)'
              return (
                <div key={r.source} className="pipeline-item">
                  <div className="pipeline-source">
                    <span className="stream-dot" style={{ background: color }} />
                    {(STREAMS[r.source]?.label || r.source).toUpperCase()}
                    <span className={`badge ${r.status === 'success' ? 'badge-ok' : r.status === 'error' ? 'badge-crit' : 'badge-warn'}`} style={{ marginLeft: 'auto' }}>
                      {r.status}
                    </span>
                  </div>
                  <div className="pipeline-rows">
                    {r.rows_inserted ?? 0} rows · {r.started_at ? formatDistanceToNow(new Date(r.started_at), { addSuffix: true }) : '—'}
                  </div>
                  {r.error && <div className="pipeline-err" title={r.error}>{r.error}</div>}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}
