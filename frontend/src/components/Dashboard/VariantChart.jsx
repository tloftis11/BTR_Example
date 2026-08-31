import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { format } from 'date-fns'

const PALETTE = [
  '#5568D6', '#0AA09A', '#C87A0A', '#C83030',
  '#8632BA', '#2A9452', '#2272C0', '#B85E1A',
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 4,
      padding: '8px 12px',
      fontSize: 12,
      boxShadow: 'var(--shadow)',
    }}>
      <div style={{ color: 'var(--tx-faint)', marginBottom: 6, fontFamily: 'var(--mono)' }}>{label}</div>
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
              <stop offset="5%"  stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.5} />
              <stop offset="95%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.04} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={tickFormatter}
          tick={{ fontSize: 10, fill: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={v => `${(v * 100).toFixed(0)}%`}
          tick={{ fontSize: 10, fill: 'var(--tx-faint)', fontFamily: 'var(--mono)' }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--tx-faint)' }}
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
