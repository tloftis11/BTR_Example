import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getSummary, getSignalSites, getAnomalies, getTimeseries } from '../api/client'
import SiteMap from '../components/Dashboard/SiteMap'
import AnomalyTable from '../components/Dashboard/AnomalyTable'
import SignalChart from '../components/Dashboard/SignalChart'
import { format } from 'date-fns'

const WEEKS = 13

export default function DashboardPage() {
  const [activeStreams, setActiveStreams] = useState({ nwss: true, tgs: true, sbd: true })

  const { data: summary }   = useQuery({ queryKey: ['summary'],   queryFn: getSummary,           refetchInterval: 60_000 })
  const { data: sites }     = useQuery({ queryKey: ['sites'],     queryFn: () => getSignalSites() })
  const { data: anomalies, isLoading: loadAnomaly } = useQuery({
    queryKey: ['anomalies'], queryFn: () => getAnomalies({ active_only: true, limit: 100 })
  })

  const { data: nwssTs, isLoading: loadNwss } = useQuery({
    queryKey: ['ts', 'nwss'], queryFn: () => getTimeseries({ source: 'nwss', metric: 'detect_prop_15d', weeks: WEEKS }),
    enabled: activeStreams.nwss,
  })
  const { data: tgsTs, isLoading: loadTgs } = useQuery({
    queryKey: ['ts', 'tgs'], queryFn: () => getTimeseries({ source: 'tgs', metric: 'variant_proportion', weeks: WEEKS }),
    enabled: activeStreams.tgs,
  })
  const { data: sbdTs, isLoading: loadSbd } = useQuery({
    queryKey: ['ts', 'sbd'], queryFn: () => getTimeseries({ source: 'sbd', metric: 'novelty_score', weeks: WEEKS }),
    enabled: activeStreams.sbd,
  })

  const filteredSites = (sites || []).filter(s => activeStreams[s.source])

  const toggleStream = (s) => setActiveStreams(prev => ({ ...prev, [s]: !prev[s] }))

  const activeAnomalies = (anomalies || []).length
  const nwssDetectPct = summary?.nwss_national_detect_prop != null
    ? `${(summary.nwss_national_detect_prop * 100).toFixed(1)}%`
    : '—'

  return (
    <>
      {/* Page header */}
      <div className="page-header">
        <div>
          <div className="page-title">Biosurveillance Dashboard</div>
          <div className="page-sub">
            Fusing NWSS, Traveler Genomic Surveillance, and SecureBio Detection signals
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: 12, color: 'var(--tx-faint)' }}>Streams:</span>
          <div className="stream-tabs">
            {['nwss', 'tgs', 'sbd'].map(s => (
              <button
                key={s}
                onClick={() => toggleStream(s)}
                className={`stream-tab${activeStreams[s] ? ` active-${s}` : ''}`}
              >
                {s.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stat tiles */}
      <div className="stat-row">
        <div className="stat-tile">
          <div className="stat-label">Active Anomalies</div>
          <div className={`stat-value ${activeAnomalies > 0 ? 'warn' : 'ok'}`}>
            {activeAnomalies}
          </div>
          <div className="stat-meta">across all streams · past 14 days</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">NWSS Detection Rate</div>
          <div className="stat-value">{nwssDetectPct}</div>
          <div className="stat-meta">
            national average · {summary?.latest_nwss_date
              ? format(new Date(summary.latest_nwss_date), 'MMM d')
              : '—'}
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Monitoring Sites</div>
          <div className="stat-value">{summary?.total_sites ?? '—'}</div>
          <div className="stat-meta">NWSS + TGS airports + SecureBio</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">TGS Last Update</div>
          <div className="stat-value" style={{ fontSize: 18 }}>
            {summary?.latest_tgs_date
              ? format(new Date(summary.latest_tgs_date), 'MMM d')
              : '—'}
          </div>
          <div className="stat-meta">variant proportions · airports</div>
        </div>
      </div>

      {/* Map + Anomaly table */}
      <div className="mid-row">
        <div className="card map-card">
          <div className="card-header">
            <span className="card-title">Monitoring Sites</span>
            <span style={{ fontSize: 12, color: 'var(--tx-faint)' }}>
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
            {activeAnomalies > 0 && (
              <span className="badge badge-warn">{activeAnomalies}</span>
            )}
          </div>
          <div className="card-body no-pad" style={{ flex: 1, overflowY: 'auto' }}>
            <AnomalyTable anomalies={anomalies} loading={loadAnomaly} />
          </div>
        </div>
      </div>

      {/* Signal charts */}
      <div className="chart-row">
        {activeStreams.nwss && (
          <div className="card chart-card">
            <div className="card-header">
              <span className="card-title">
                <span className="stream-dot" style={{ background: '#0891B2' }} />
                NWSS — Detection proportion
              </span>
              <span style={{ fontSize: 11, color: 'var(--tx-faint)' }}>{WEEKS}W national avg</span>
            </div>
            <div className="card-body">
              <SignalChart data={nwssTs} source="nwss" metric="detect_prop_15d" loading={loadNwss} />
            </div>
          </div>
        )}
        {activeStreams.tgs && (
          <div className="card chart-card">
            <div className="card-header">
              <span className="card-title">
                <span className="stream-dot" style={{ background: '#7C3AED' }} />
                TGS — Variant proportions
              </span>
              <span style={{ fontSize: 11, color: 'var(--tx-faint)' }}>{WEEKS}W airport avg</span>
            </div>
            <div className="card-body">
              <SignalChart data={tgsTs} source="tgs" metric="variant_proportion" loading={loadTgs} />
            </div>
          </div>
        )}
        {activeStreams.sbd && (
          <div className="card chart-card">
            <div className="card-header">
              <span className="card-title">
                <span className="stream-dot" style={{ background: '#059669' }} />
                SecureBio — Novelty score
              </span>
              <span style={{ fontSize: 11, color: 'var(--tx-faint)' }}>{WEEKS}W</span>
            </div>
            <div className="card-body">
              <SignalChart data={sbdTs} source="sbd" metric="novelty_score" loading={loadSbd} />
            </div>
          </div>
        )}
      </div>
    </>
  )
}
