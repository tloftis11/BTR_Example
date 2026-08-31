import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getSummary } from '../api/client'

const STREAMS = [
  {
    key: 'nwss',
    label: 'NWSS',
    color: '#0891B2',
    bg: '#ECFEFF',
    border: '#A5F3FC',
    name: 'National Wastewater Surveillance',
    stat: '~3,000 sites',
    desc: 'CDC reports SARS-CoV-2 and pathogen concentrations from ~3,000 treatment plants weekly. The broadest geographic coverage of any surveillance stream.',
  },
  {
    key: 'tgs',
    label: 'TGS',
    color: '#7C3AED',
    bg: '#F5F3FF',
    border: '#DDD6FE',
    name: 'Traveler Genomic Surveillance',
    stat: '8 airports · 1M+ participants',
    desc: "CDC's voluntary swab program at major international airports sequences respiratory pathogens and publishes weekly variant proportion estimates.",
  },
  {
    key: 'sbd',
    label: 'SecureBio',
    color: '#059669',
    bg: '#ECFDF5',
    border: '#A7F3D0',
    name: 'SecureBio Detection',
    stat: '13 sites · untargeted',
    desc: 'Untargeted metagenomic sequencing at ~13 US wastewater sites. Raw reads on NCBI SRA — capable of detecting novel pathogens without a known target sequence.',
  },
]

const STEPS = [
  { n: '01', title: 'Daily ingest', body: 'A scheduled pipeline pulls fresh data from the CDC Socrata API each morning at 06:00 UTC — no manual intervention required.' },
  { n: '02', title: 'Schema fusion', body: 'All three streams normalize to a common schema keyed by source, site, pathogen, date, and metric — enabling cross-stream queries for the first time.' },
  { n: '03', title: 'Anomaly detection', body: 'Z-scores are computed for every (site, metric) pair against an 8-week rolling baseline. Signals beyond 2σ are flagged automatically.' },
  { n: '04', title: 'Unified dashboard', body: 'An interactive map, timeline charts, and anomaly table surface the fused picture across all three streams in one view.' },
]

export default function LandingPage() {
  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn: getSummary,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  return (
    <div className="lp">

      {/* ── Nav ── */}
      <header className="lp-nav">
        <div className="lp-inner lp-nav-inner">
          <div className="lp-logo">
            <span className="lp-logo-dot" />
            Biothreat Radar
          </div>
          <nav className="lp-nav-links">
            <a href="#data">Data</a>
            <a href="#how">How it works</a>
            <Link to="/about">About</Link>
          </nav>
          <Link to="/dashboard" className="lp-launch-btn">Launch Dashboard →</Link>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <div className="lp-inner lp-hero-inner">
          <div className="lp-eyebrow">
            <span className="lp-pulse" />
            Live biosurveillance · updated daily
          </div>
          <h1 className="lp-h1">
            Three surveillance streams.<br />One fused picture.
          </h1>
          <p className="lp-lead">
            Biothreat Radar ingests CDC wastewater surveillance, traveler genomic sequencing,
            and metagenomic detection data — overlaying all three on a shared map and timeline
            with automated anomaly detection.
          </p>
          <div className="lp-hero-ctas">
            <Link to="/dashboard" className="lp-btn-primary">Open Dashboard</Link>
            <a href="#how" className="lp-btn-ghost">How it works</a>
          </div>

          {summary && (
            <div className="lp-live-stats">
              <div className="lp-live-stat">
                <span className="lp-live-n">{summary.total_sites?.toLocaleString() ?? '—'}</span>
                <span className="lp-live-l">monitoring sites</span>
              </div>
              <div className="lp-live-divider" />
              <div className="lp-live-stat">
                <span className="lp-live-n" style={{ color: summary.active_anomalies > 0 ? '#F59E0B' : 'inherit' }}>
                  {summary.active_anomalies ?? '—'}
                </span>
                <span className="lp-live-l">active anomalies</span>
              </div>
              <div className="lp-live-divider" />
              <div className="lp-live-stat">
                <span className="lp-live-n">3</span>
                <span className="lp-live-l">data streams</span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Streams ── */}
      <section className="lp-section" id="data">
        <div className="lp-inner">
          <div className="lp-section-label">Data Sources</div>
          <h2 className="lp-h2">Fusing three independent streams</h2>
          <p className="lp-body">
            Each stream measures a different exposure pathway. Combining them reveals signals
            no single source can detect alone.
          </p>
          <div className="lp-stream-grid">
            {STREAMS.map(s => (
              <div key={s.key} className="lp-stream-card" style={{ '--sc': s.color, '--sb': s.bg, '--sbd': s.border }}>
                <div className="lp-stream-top">
                  <span className="lp-stream-tag">{s.label}</span>
                  <span className="lp-stream-stat">{s.stat}</span>
                </div>
                <div className="lp-stream-name">{s.name}</div>
                <p className="lp-stream-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="lp-section lp-section-alt" id="how">
        <div className="lp-inner">
          <div className="lp-section-label">Architecture</div>
          <h2 className="lp-h2">How it works</h2>
          <div className="lp-steps">
            {STEPS.map(s => (
              <div key={s.n} className="lp-step">
                <div className="lp-step-n">{s.n}</div>
                <div className="lp-step-title">{s.title}</div>
                <p className="lp-step-body">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="lp-cta">
        <div className="lp-inner lp-cta-inner">
          <h2 className="lp-cta-h">Ready to explore the data?</h2>
          <p className="lp-cta-sub">
            The dashboard shows live NWSS, TGS, and SecureBio data with anomaly alerts,
            site maps, and signal trend charts.
          </p>
          <Link to="/dashboard" className="lp-btn-primary lp-btn-lg">Open Dashboard →</Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-inner lp-footer-inner">
          <div className="lp-logo" style={{ fontSize: 13 }}>
            <span className="lp-logo-dot" />
            Biothreat Radar
          </div>
          <div className="lp-footer-links">
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/about">About</Link>
            <a href="https://data.cdc.gov" target="_blank" rel="noopener noreferrer">CDC Open Data</a>
            <a href="https://securebio.org/detection" target="_blank" rel="noopener noreferrer">SecureBio</a>
          </div>
        </div>
      </footer>

    </div>
  )
}
