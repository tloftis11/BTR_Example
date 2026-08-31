import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { getLatestBriefing, generateBriefing, getPipelineRuns } from '../api/client'

const PATHOGENS = [
  { id: 'sars2', label: 'SARS-CoV-2' },
  { id: 'h5n1',  label: 'H5N1' },
  { id: 'mpox',  label: 'Mpox' },
  { id: 'cholera', label: 'Cholera' },
  { id: 'ebola', label: 'Ebola' },
]

const STREAMS = [
  { id: 'NWSS', label: 'NWSS', color: 'var(--nwss)' },
  { id: 'TGS',  label: 'TGS',  color: 'var(--tgs)' },
  { id: 'SBD',  label: 'SBD',  color: 'var(--sbd)' },
  { id: 'HMP',  label: 'HMP',  color: 'var(--hmp)' },
  { id: 'WHO',  label: 'WHO',  color: 'var(--who)' },
  { id: 'NAO',  label: 'NAO',  color: 'var(--nao)' },
  { id: 'NST',  label: 'NST',  color: 'var(--nst)' },
]

function parseParagraphs(text) {
  if (!text) return []
  return text.split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
}

export default function BriefingPage() {
  const [selectedPathogens, setSelectedPathogens] = useState([])
  const [selectedStreams,   setSelectedStreams]    = useState([])
  const [region,            setRegion]            = useState('global')
  const [customBriefing,    setCustomBriefing]    = useState(null)

  const { data: stored, isLoading: loadingStored, refetch: refetchStored } = useQuery({
    queryKey: ['briefing', 'latest'],
    queryFn: getLatestBriefing,
    staleTime: 5 * 60 * 1000,
  })

  const { data: runs } = useQuery({ queryKey: ['runs'], queryFn: getPipelineRuns })

  const genMut = useMutation({
    mutationFn: generateBriefing,
    onSuccess: (data) => {
      if (data.briefing) setCustomBriefing(data)
      else if (data.error) setCustomBriefing({ error: data.error })
    },
    onError: (err) => setCustomBriefing({ error: err.message }),
  })

  const togglePathogen = (id) =>
    setSelectedPathogens(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const toggleStream = (id) =>
    setSelectedStreams(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const handleRegenerate = () => {
    const filters = {}
    if (selectedPathogens.length) {
      filters.pathogens = PATHOGENS.filter(p => selectedPathogens.includes(p.id)).map(p => p.label)
    }
    if (selectedStreams.length) filters.streams = selectedStreams
    if (region === 'us') filters.region = 'us'
    setCustomBriefing(null)
    genMut.mutate(Object.keys(filters).length ? filters : null)
  }

  const handleReset = () => {
    setCustomBriefing(null)
    setSelectedPathogens([])
    setSelectedStreams([])
    setRegion('global')
  }

  // Which briefing to display: custom > stored
  const activeBriefing = customBriefing || stored
  const paragraphs     = parseParagraphs(activeBriefing?.briefing)
  const isCustom       = Boolean(customBriefing?.briefing)
  const hasFilters     = selectedPathogens.length > 0 || selectedStreams.length > 0 || region !== 'global'

  // Latest successful run per source
  const latestRuns = runs ? Object.values(
    runs.reduce((acc, r) => { if (!acc[r.source]) acc[r.source] = r; return acc }, {})
  ) : []

  return (
    <div className="br-layout">
      {/* ── Header ── */}
      <div className="br-header">
        <div>
          <div className="br-kicker">BIOSURVEILLANCE INTELLIGENCE</div>
          <h1 className="br-title">Daily Briefing</h1>
          <div className="br-dateline">
            {format(new Date(), 'MMMM d, yyyy')}
            {activeBriefing?.generated_at && (
              <span className="br-generated">
                {' '}· Generated {format(new Date(activeBriefing.generated_at), 'HH:mm')} UTC
                {isCustom ? ' · Custom filter' : ' · Daily default'}
              </span>
            )}
          </div>
        </div>
        <Link to="/intel" className="br-intel-cta">
          Ask BTR a question →
        </Link>
      </div>

      <div className="br-body">
        {/* ── Main briefing ── */}
        <div className="br-main">
          {loadingStored && !customBriefing && (
            <div className="br-loading">Loading today's briefing…</div>
          )}

          {genMut.isPending && (
            <div className="br-loading">Regenerating briefing with filters…</div>
          )}

          {!loadingStored && !genMut.isPending && activeBriefing?.error && (
            <div className="br-error">{activeBriefing.error}</div>
          )}

          {!loadingStored && !genMut.isPending && !activeBriefing?.briefing && !activeBriefing?.error && (
            <div className="br-empty">
              <div className="br-empty-title">No briefing available yet.</div>
              <p>The daily briefing is generated automatically after each pipeline sync. You can generate the first one now.</p>
              <button className="br-generate-btn" onClick={handleRegenerate}>
                Generate Today's Briefing
              </button>
            </div>
          )}

          {!genMut.isPending && paragraphs.length > 0 && (
            <div className="br-content">
              {isCustom && (
                <div className="br-custom-banner">
                  Custom filter active ·{' '}
                  <button className="br-inline-link" onClick={handleReset}>View default briefing</button>
                </div>
              )}
              {paragraphs.map((p, i) => (
                <p key={i} className="br-paragraph">{p}</p>
              ))}
            </div>
          )}

          {/* ── Filter section ── */}
          <div className="br-filters">
            <div className="br-filter-heading">Refine this briefing</div>

            <div className="br-filter-row">
              <span className="br-filter-label">Pathogens</span>
              <div className="br-chips">
                {PATHOGENS.map(p => (
                  <button
                    key={p.id}
                    className={`br-chip${selectedPathogens.includes(p.id) ? ' active' : ''}`}
                    onClick={() => togglePathogen(p.id)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="br-filter-row">
              <span className="br-filter-label">Streams</span>
              <div className="br-chips">
                {STREAMS.map(s => (
                  <button
                    key={s.id}
                    className={`br-chip${selectedStreams.includes(s.id) ? ' active' : ''}`}
                    onClick={() => toggleStream(s.id)}
                    style={selectedStreams.includes(s.id) ? { borderColor: s.color, color: s.color, background: `color-mix(in srgb, ${s.color} 10%, transparent)` } : {}}
                  >
                    <span
                      className="stream-dot"
                      style={{ background: s.color, marginRight: 4 }}
                    />
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="br-filter-row">
              <span className="br-filter-label">Region</span>
              <div className="br-chips">
                {[{ id: 'global', label: 'Global' }, { id: 'us', label: 'US Only' }].map(r => (
                  <button
                    key={r.id}
                    className={`br-chip${region === r.id ? ' active' : ''}`}
                    onClick={() => setRegion(r.id)}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="br-filter-actions">
              <button
                className="br-generate-btn"
                onClick={handleRegenerate}
                disabled={genMut.isPending}
              >
                {genMut.isPending ? 'Generating…' : hasFilters ? '⟳ Regenerate with Filters' : '⟳ Regenerate'}
              </button>
              {(isCustom || hasFilters) && (
                <button className="br-reset-btn" onClick={handleReset}>
                  Reset to default
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── Sidebar: pipeline status ── */}
        <div className="br-sidebar">
          <div className="br-sidebar-card">
            <div className="br-sidebar-label">Data Streams</div>
            {latestRuns.length === 0
              ? <div className="br-sidebar-empty">No sync data yet</div>
              : latestRuns.map(r => (
                <div key={r.source} className="br-stream-row">
                  <span
                    className="stream-dot"
                    style={{ background: STREAMS.find(s => s.id === r.source?.toUpperCase())?.color || 'var(--tx-faint)' }}
                  />
                  <span className="br-stream-name">
                    {r.source?.toUpperCase()}
                  </span>
                  <span className={`badge ${r.status === 'success' ? 'badge-ok' : r.status === 'error' ? 'badge-crit' : 'badge-warn'}`} style={{ fontSize: 9 }}>
                    {r.status}
                  </span>
                  <span className="br-stream-rows">{r.rows_inserted ?? 0} rows</span>
                </div>
              ))
            }
          </div>

          <div className="br-sidebar-card">
            <div className="br-sidebar-label">How this works</div>
            <p className="br-sidebar-body">
              BTR fuses 7 public surveillance streams — wastewater detection (NWSS), traveler genomics (TGS),
              environmental metagenomics (SBD), global epidemic alerts (ReliefWeb + WHO), NCBI sequencing runs,
              and Nextstrain phylogenetics — into a daily AI briefing.
            </p>
            <p className="br-sidebar-body">
              Briefings are auto-generated after each morning sync. Use the filters to focus on specific
              pathogens or streams.
            </p>
            <Link to="/intel" className="br-sidebar-link">Ask BTR a question →</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
