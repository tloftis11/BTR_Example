import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import '../landing.css'

const BARS = [
  { id: 'bar-w', color: 'var(--sw)', pct: 72, label: 'NWSS', cls: 'lp-td-sw', change: '↑ 18%' },
  { id: 'bar-t', color: 'var(--st)', pct: 31, label: 'TGS',  cls: 'lp-td-st', change: '+ 2%'  },
  { id: 'bar-m', color: 'var(--sm)', pct: 58, label: 'SBD',  cls: 'lp-td-sm', change: '+ 9%'  },
]

export default function LandingPage() {
  const barRefs = useRef({})

  /* body background */
  useEffect(() => {
    const prev = document.body.style.background
    document.body.style.background = '#090E1A'
    return () => { document.body.style.background = prev }
  }, [])

  /* animate terminal bars */
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      BARS.forEach(({ id, pct }) => {
        const el = barRefs.current[id]
        if (el) el.style.width = pct + '%'
      })
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="lp-page">

      {/* ── Nav ── */}
      <nav className="lp-nav">
        <Link to="/" className="lp-nav-logo">
          <span className="lp-pulse" />
          Biothreat Radar
        </Link>
        <ul className="lp-nav-links">
          <li><a href="#streams">Data Streams</a></li>
          <li><a href="#fusion">Fusion Layer</a></li>
          <li><a href="#scope">Scope</a></li>
          <li><Link to="/dashboard" className="lp-nav-cta">Open Dashboard →</Link></li>
        </ul>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero" id="home">
        <div className="lp-scan" aria-hidden="true" />
        <div className="lp-hero-inner">

          <div className="lp-hero-text">
            <div className="lp-eyebrow">Public Biosurveillance Infrastructure</div>
            <h1 className="lp-h1">
              The signal<br />was already<br />there.<span className="lp-cursor" aria-hidden="true" />
            </h1>
            <p className="lp-hero-sub">
              Three independent public data streams. One fusion layer that reads them together.
              Biothreat Radar surfaces emerging biological threats before they appear in clinical surveillance.
            </p>
            <div className="lp-btns">
              <Link to="/dashboard" className="lp-btn lp-btn-primary">Open Dashboard</Link>
              <a href="#streams" className="lp-btn lp-btn-ghost">How It Works</a>
            </div>
          </div>

          {/* Terminal */}
          <div className="lp-terminal" role="img" aria-label="Live stream monitor">
            <div className="lp-term-bar">
              <div className="lp-td lp-td-r" />
              <div className="lp-td lp-td-y" />
              <div className="lp-td lp-td-g" />
              <span className="lp-term-title">stream-monitor — all sources</span>
            </div>
            <div className="lp-term-body">
              <span className="lp-td-dim">$ biothreat-radar --watch --format=live</span>
              <hr className="lp-term-hr" />
              {BARS.map(b => (
                <div className="lp-srow" key={b.id}>
                  <span className={b.cls}>{b.label}</span>
                  <div className="lp-sbar">
                    <div
                      className="lp-sfill"
                      ref={el => { barRefs.current[b.id] = el }}
                      style={{ background: b.color }}
                    />
                  </div>
                  <span className={`${b.cls} lp-td-bold`}>{b.change}</span>
                  <span className="lp-td-dim">wk35</span>
                </div>
              ))}
              <hr className="lp-term-hr" />
              <div className="lp-td-warn">⚠ anomaly flagged — region NE-07</div>
              <div className="lp-td-dim" style={{ fontSize: '0.68rem', marginTop: '0.25rem' }}>
                NWSS signal +2.4σ above 8-wk baseline<br />
                cross-stream correlation: elevated
              </div>
              <hr className="lp-term-hr" />
              <div className="lp-td-dim">
                synced: <span className="lp-td-acc">2026-08-31 06:00 UTC</span><br />
                next&nbsp;&nbsp;: 2026-09-01 06:00 UTC
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── Problem ── */}
      <section className="lp-section lp-section-alt" id="problem">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">The Gap</div>
          <h2 className="lp-h2">Biosurveillance works in silos.</h2>
          <p className="lp-section-sub">
            The data already exists — wastewater readings, traveler genomics, metagenomic sequences.
            What doesn't exist is the layer that ties them together by time and geography.
          </p>
          <div className="lp-problem-grid">
            {[
              { tag: 'Silo A', title: 'Wastewater Signal', body: 'NWSS data is public and updated weekly, but lives on data.cdc.gov with no automated connection to genomic surveillance at the same sites and times.' },
              { tag: 'Silo B', title: 'Traveler Genomics', body: "TGS Nowcast tracks variant proportions at international airports — catching new subclades days before standard surveillance — but shares no timeline with wastewater data." },
              { tag: 'Silo C', title: 'Metagenomic Signal', body: "SecureBio Detection does untargeted metagenomic sequencing capable of detecting sequences with no name yet. Its outputs are public but disconnected from everything else." },
            ].map(c => (
              <div className="lp-prob-cell" key={c.tag}>
                <div className="lp-prob-tag">{c.tag}</div>
                <h3>{c.title}</h3>
                <p>{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Streams ── */}
      <section className="lp-section" id="streams">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">Data Streams</div>
          <h2 className="lp-h2">Three sources. One schema.</h2>
          <p className="lp-section-sub">
            Each stream has a public API. Biothreat Radar ingests all three daily, normalizes them
            to a common schema, and overlays them on a shared timeline and map.
          </p>
          <div className="lp-streams-grid">

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: 'var(--sw)' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">CDC / WastewaterSCAN</div>
                <div className="lp-sc-name">Wastewater Surveillance</div>
                <div className="lp-sc-cadence">Updated weekly · NWSS + Stanford/Emory/Verily panel</div>
                <p className="lp-sc-desc">Pathogen concentrations in sewage shed days to weeks before clinical cases surface. NWSS covers named pathogens; WastewaterSCAN extends the panel with a broader academic assay.</p>
                <div className="lp-sc-detects">
                  <div className="lp-sc-detects-label">Detects</div>
                  {['SARS-CoV-2','Influenza A/B','RSV','Norovirus','Mpox'].map(t => (
                    <span className="lp-tag" key={t}>{t}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: 'var(--st)' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">CDC Traveler Genomic Surveillance</div>
                <div className="lp-sc-name">Airport Genomics</div>
                <div className="lp-sc-cadence">Weekly Nowcast · 30+ international entry points</div>
                <p className="lp-sc-desc">Voluntary traveler swabs sequenced at international airports, surfacing variant proportions and new subclades days before clinical or wastewater surveillance. Over one million participants enrolled.</p>
                <div className="lp-sc-detects">
                  <div className="lp-sc-detects-label">Detects</div>
                  {['Flu A subclades','Flu B','RSV lineages','SARS-CoV-2 variants'].map(t => (
                    <span className="lp-tag" key={t}>{t}</span>
                  ))}
                  <span className="lp-tag lp-tag-dim">targeted panel</span>
                </div>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: 'var(--sm)' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">SecureBio Detection / NCBI SRA</div>
                <div className="lp-sc-name">Metagenomic Sequencing</div>
                <div className="lp-sc-cadence">Quarterly · 13 active sites · raw reads on NCBI</div>
                <p className="lp-sc-desc">Untargeted metagenomic sequencing of wastewater — no pathogen list required. Capable of detecting novel sequences with no assigned name yet. Over 270 billion read pairs deposited to NCBI SRA.</p>
                <div className="lp-sc-detects">
                  <div className="lp-sc-detects-label">Detects</div>
                  {['Known viruses','Novel sequences','Animal-infecting pathogens'].map(t => (
                    <span className="lp-tag" key={t}>{t}</span>
                  ))}
                  <span className="lp-tag lp-tag-dim">pathogen-agnostic</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── Fusion ── */}
      <section className="lp-section lp-section-alt" id="fusion">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">The Fusion Layer</div>
          <h2 className="lp-h2">What doesn't exist anywhere public — yet.</h2>
          <p className="lp-section-sub">
            A common schema binding a wastewater signal at site X, a genomic blip at airport Y, and an unusual
            metagenomic cluster — together, by time and geography. Plus an anomaly-detection layer that flags
            when more than one stream rises in the same place at once.
          </p>

          <div className="lp-fusion-diagram">
            <div className="lp-fusion-inputs">
              {[
                { color: 'var(--sw)', text: 'NWSS site NE-07 — SARS-CoV-2 +18% week 35' },
                { color: 'var(--st)', text: "TGS Chicago O'Hare — novel Flu A subclade +4% week 35" },
                { color: 'var(--sm)', text: 'SecureBio Chicago — unknown sequence cluster detected' },
              ].map((f, i) => (
                <div className="lp-f-input" key={i}>
                  <div className="lp-f-dot" style={{ background: f.color }} />
                  {f.text}
                </div>
              ))}
            </div>

            <div className="lp-fusion-arrow" aria-hidden="true">→</div>

            <div className="lp-fusion-right">
              <div className="lp-fusion-engine">
                <div className="lp-fe-label">Fusion Layer</div>
                <div className="lp-fe-name">Common schema<br />+ anomaly detection</div>
              </div>
              <div className="lp-alert-box">
                ⚠ ALERT — week 35 / Northeast US<br />
                3 streams elevated in overlapping geography<br />
                Signal: 2.4σ above 8-week baseline<br />
                Action: flag for enhanced surveillance
              </div>
            </div>
          </div>

          <div className="lp-schema-box">
            <h4>Common Schema</h4>
            <code>signal(site_id, source, pathogen, date, lat, lon, value, signal_type, anomaly_score)</code>
          </div>
        </div>
      </section>

      {/* ── Scope ── */}
      <section className="lp-section" id="scope">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">Scope</div>
          <h2 className="lp-h2">What this demo can and can't show.</h2>
          <p className="lp-section-sub">
            A proof of concept built on public data is an honest illustration of the concept. It's not
            a claim that the full operational system described in federal budget documents exists.
          </p>
          <div className="lp-scope-grid">
            <div className="lp-scope-card lp-can">
              <h3>What the dashboard demonstrates</h3>
              <ul>
                {[
                  'Live NWSS + WastewaterSCAN pathogen trends via public API',
                  'Weekly TGS Nowcast variant proportions at airports',
                  'SecureBio Detection public dashboard outputs',
                  'All three overlaid on a shared timeline and map',
                  'Anomaly detection: z-score flags when multiple streams rise in the same geography within a two-week window',
                  'The "known-threat early warning + novel-pathogen signal" concept in working form',
                ].map(s => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div className="lp-scope-card">
              <h3>What would require more</h3>
              <ul>
                {[
                  'Nationwide 24-hour-turnaround novel pathogen detection — requires scaling from ~13 metagenomic sites to hundreds',
                  'AMD negative-specimen deep-dive data routed through private labs — currently not publicly accessible',
                  'A validated anomaly-detection model with published performance benchmarks',
                  'Aircraft wastewater integration beyond the current TGS pilot',
                ].map(s => <li key={s}>{s}</li>)}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="lp-section lp-section-alt lp-cta-section" id="dashboard">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">Dashboard</div>
          <h2 className="lp-h2">See the streams in motion.</h2>
          <p className="lp-section-sub">
            Live data. Shared timeline. One anomaly-detection layer watching across all three sources,
            updated every morning.
          </p>
          <Link to="/dashboard" className="lp-btn lp-btn-primary">Open Dashboard →</Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-logo">Biothreat Radar</div>
        <div className="lp-footer-note">
          Built on public data. No proprietary data required.<br />
          NWSS · TGS Nowcast · SecureBio Detection / NCBI SRA
        </div>
        <div className="lp-footer-links">
          <Link to="/about">About</Link>
          <Link to="/dashboard">Dashboard</Link>
          <a href="https://data.cdc.gov" target="_blank" rel="noopener noreferrer">Data Sources</a>
        </div>
      </footer>

    </div>
  )
}
