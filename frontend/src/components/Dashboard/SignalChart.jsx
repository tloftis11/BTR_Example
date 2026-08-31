import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts'
import { format } from 'date-fns'

const STREAM_COLORS = {
  nwss: '#38D9CC',
  tgs:  '#7B96F0',
  sbd:  '#8FD47A',
  hmp:  '#F4A93D',
  who:  '#F25D5D',
  nao:  '#6DB8FF',
  nst:  '#C471ED',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0C1528',
      border: '1px solid #1A2E52',
      borderRadius: 4,
      padding: '8px 12px',
      fontSize: 12,
    }}>
      <div style={{ color: '#3A5480', marginBottom: 4, fontFamily: 'var(--mono)' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontFamily: 'var(--mono)', fontWeight: 500 }}>
          {p.value != null ? p.value.toFixed(4) : '—'}
        </div>
      ))}
    </div>
  )
}

export default function SignalChart({ data = [], source, metric, loading }) {
  const color = STREAM_COLORS[source] || '#6B8DBD'
  const weekly = aggregateWeekly(data)

  if (loading) return <div className="empty-state" style={{ height: '100%' }}>Loading…</div>
  if (!weekly.length) return <div className="empty-state" style={{ height: '100%' }}>No data</div>

  const tickFormatter = (d) => {
    try { return format(new Date(d), 'M/d') } catch { return d }
  }

  const gradId = `sg_${source}`

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={weekly} margin={{ top: 8, right: 8, bottom: 4, left: -20 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.4} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2E52" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={tickFormatter}
          tick={{ fontSize: 10, fill: '#3A5480', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#3A5480', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          width={36}
          tickFormatter={v => v.toFixed(2)}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="avg"
          stroke={color}
          fill={`url(#${gradId})`}
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, strokeWidth: 0, fill: color }}
        />
      </AreaChart>
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
