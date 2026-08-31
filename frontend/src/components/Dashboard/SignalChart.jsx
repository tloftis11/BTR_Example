import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { format } from 'date-fns'

const STREAM_COLORS = { nwss: '#0891B2', tgs: '#7C3AED', sbd: '#059669' }

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'white',
      border: '1px solid #E2E8F0',
      borderRadius: 4,
      padding: '8px 12px',
      fontSize: 12,
      boxShadow: '0 2px 4px rgba(0,0,0,.08)',
    }}>
      <div style={{ color: '#94A3B8', marginBottom: 4 }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontFamily: 'var(--mono)', fontWeight: 500 }}>
          {p.value != null ? p.value.toFixed(4) : '—'}
        </div>
      ))}
    </div>
  )
}

export default function SignalChart({ data = [], source, metric, title, loading }) {
  const color = STREAM_COLORS[source] || '#64748B'

  // Aggregate to weekly averages across sites
  const weekly = aggregateWeekly(data)

  if (loading) return <div className="empty-state" style={{ height: '100%' }}>Loading…</div>
  if (!weekly.length) return <div className="empty-state" style={{ height: '100%' }}>No data</div>

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={weekly} margin={{ top: 8, right: 12, bottom: 4, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={d => format(new Date(d), 'M/d')}
          tick={{ fontSize: 10, fill: '#94A3B8', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#94A3B8', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={v => v.toFixed(2)}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="avg"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function aggregateWeekly(data) {
  const byDate = {}
  for (const d of data) {
    if (d.value == null) continue
    const key = d.signal_date
    if (!byDate[key]) byDate[key] = []
    byDate[key].push(d.value)
  }
  return Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, vals]) => ({
      date,
      avg: vals.reduce((s, v) => s + v, 0) / vals.length,
    }))
}
