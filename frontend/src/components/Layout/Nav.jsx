import { NavLink } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getSummary, triggerPipeline } from '../../api/client'
import { format } from 'date-fns'

export default function Nav() {
  const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: getSummary, refetchInterval: 60_000 })
  const { mutate: runPipeline, isPending } = useMutation({ mutationFn: triggerPipeline })

  const lastSync = summary?.latest_nwss_date
    ? `NWSS updated ${format(new Date(summary.latest_nwss_date), 'MMM d, yyyy')}`
    : 'Awaiting first sync'

  return (
    <nav className="nav">
      <NavLink to="/" className="nav-logo">
        <span className="nav-logo-mark" />
        Biothreat Radar
      </NavLink>

      <ul className="nav-links">
        <li><NavLink to="/dashboard">Dashboard</NavLink></li>
        <li><NavLink to="/about">About</NavLink></li>
      </ul>

      <div className="nav-right">
        <span className="nav-sync mono">{lastSync}</span>
        <button
          className="nav-run-btn"
          onClick={() => runPipeline()}
          disabled={isPending}
        >
          {isPending ? 'Running…' : 'Sync Now'}
        </button>
      </div>
    </nav>
  )
}
