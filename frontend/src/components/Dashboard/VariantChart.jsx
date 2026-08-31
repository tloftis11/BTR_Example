import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { format } from 'date-fns'

// Distinct colors for up to 8 variants, chosen to read on dark backgrounds
const PALETTE = [
  '#7B96F0', '#38D9CC', '#F4A93D', '#F25D5D',
  '#C471ED', '#8FD47A', '#6DB8FF', '#FFD166',
]

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
      <div style={{ color: '#3A5480', marginBottom: 6, fontFamily: 'var(--mono)' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontFamily: 'var(--mono)', fontSize: 11 }}>
          {p.dataKey}: {(p.value * 100).toFixed(1)}%
        </div>
      ))}
    </div>
  )
}

export default function VariantChart({ data, loading }) {
  if (loading) return <div className="empty-state" style={{ height: '100%' }}>Loading…</div>

  const variants = data?.variants || []
  const series   = data?.series   || []

  if (!series.length || !variants.length) {
    return <div className="empty-state" style={{ height: '100%' }}>No variant data</div>
  }

  const tickFormatter = (d) => {
    try { return format(new Date(d), 'M/d') } catch { return d }
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={series} margin={{ top: 8, right: 8, bottom: 4, left: -20 }}>
        <defs>
          {variants.map((v, i) => (
            <linearGradient key={v} id={`vg${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.6} />
              <stop offset="95%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.05} />
            </linearGradient>
          ))}
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
          tickFormatter={v => `${(v * 100).toFixed(0)}%`}
          tick={{ fontSize: 10, fill: '#3A5480', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 10, fontFamily: 'var(--mono)', color: '#6B8DBD' }}
          iconSize={6}
          iconType="circle"
        />
        {variants.map((v, i) => (
          <Area
            key={v}
            type="monotone"
            dataKey={v}
            stackId="1"
            stroke={PALETTE[i % PALETTE.length]}
            fill={`url(#vg${i})`}
            strokeWidth={1.5}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
