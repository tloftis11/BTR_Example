import { format } from 'date-fns'
import clsx from 'clsx'

const STREAM_COLORS = { nwss: '#0891B2', tgs: '#7C3AED', sbd: '#059669' }

function SeverityBadge({ z }) {
  if (Math.abs(z) >= 3) return <span className="badge badge-crit">High</span>
  if (Math.abs(z) >= 2) return <span className="badge badge-warn">Moderate</span>
  return <span className="badge badge-ok">Low</span>
}

function MetricLabel({ metric }) {
  const labels = {
    detect_prop_15d: 'Detection proportion',
    ptc_15d: '% change (15d)',
    variant_proportion: 'Variant share',
    novelty_score: 'Novelty score',
  }
  return <span className="text-muted">{labels[metric] || metric}</span>
}

export default function AnomalyTable({ anomalies = [], loading }) {
  if (loading) {
    return <div className="empty-state">Loading anomalies…</div>
  }
  if (!anomalies.length) {
    return <div className="empty-state">No active anomalies detected.</div>
  }

  return (
    <div className="anomaly-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Site</th>
            <th>Stream</th>
            <th>Pathogen</th>
            <th>Metric</th>
            <th style={{ textAlign: 'right' }}>σ</th>
            <th style={{ textAlign: 'right' }}>Value</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map(a => (
            <tr key={a.id}>
              <td><SeverityBadge z={a.z_score} /></td>
              <td>
                <div style={{ fontWeight: 500 }}>{a.site_name || a.site_id}</div>
                {a.state && <div style={{ fontSize: 11, color: 'var(--tx-faint)' }}>{a.state}</div>}
              </td>
              <td>
                <span className="stream-dot" style={{ background: STREAM_COLORS[a.source] }} />
                {a.source.toUpperCase()}
              </td>
              <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {a.pathogen || '—'}
              </td>
              <td><MetricLabel metric={a.metric} /></td>
              <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', color: a.z_score >= 3 ? 'var(--crit)' : 'var(--warn)' }}>
                {a.z_score.toFixed(2)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'var(--mono)' }}>
                {a.current_value.toFixed(3)}
              </td>
              <td style={{ fontFamily: 'var(--mono)', color: 'var(--tx-faint)', fontSize: 12 }}>
                {format(new Date(a.signal_date), 'MMM d')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
