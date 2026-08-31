import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import '../landing.css'

const BARS = [
  { id: 'bar-w', color: '#0AA09A', pct: 72, label: 'NWSS', cls: 'lp-td-sw', change: '↑ 18%' },
  { id: 'bar-t', color: '#5568D6', pct: 31, label: 'TGS',  cls: 'lp-td-st', change: '+ 2%'  },
  { id: 'bar-m', color: '#2A9452', pct: 58, label: 'SBD',  cls: 'lp-td-sm', change: '+ 9%'  },
]

export default function LandingPage() {
  const barRefs = useRef({})

  /* animate terminal bars after mount */
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
          <li><a href="#fusion">How It Works</a></li>
          <li><a href="#scope">Scope</a></li>
          <li><Link to="/briefing" className="lp-nav-cta">View Briefing →</Link></li>
        </ul>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero" id="home">
        <div className="lp-hero-inner">

          <div className="lp-hero-text">
            <div className="lp-eyebrow">Public Biosurveillance Infrastructure</div>
            <h1 className="lp-h1">
              The signal<br />was already<br />there.<span className="lp-cursor" aria-hidden="true" />
            </h1>
            <p className="lp-hero-sub">
              Seven independent public data streams. One AI fusion layer that reads them together.
              Biothreat Radar surfaces emerging biological threats as a daily intelligence briefing.
            </p>
            <div className="lp-btns">
              <Link to="/briefing" className="lp-btn lp-btn-primary">View Today's Briefing</Link>
              <Link to="/intel" className="lp-btn lp-btn-ghost">Ask BTR a Question</Link>
            </div>
          </div>

          {/* Terminal — stays dark, deliberate contrast */}
          <div className="lp-terminal" role="img" aria-label="Live stream monitor">
            <div className="lp-term-bar">
              <div className="lp-td lp-td-r" />
              <div className="lp-td lp-td-y" />
              <div className="lp-td lp-td-g" />
              <span className="lp-term-title">stream-monitor — 7 sources</span>
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
            The data already exists — wastewater readings, traveler genomics, metagenomic sequences, global alert feeds.
            What doesn't exist is the layer that ties them together by time, geography, and pathogen.
          </p>
          <div className="lp-problem-grid">
            {[
              { tag: 'Silo A', title: 'Wastewater Signal', body: 'NWSS data is public and updated weekly, but lives on data.cdc.gov with no automated connection to genomic surveillance at the same sites and times.' },
              { tag: 'Silo B', title: 'Traveler Genomics', body: "TGS Nowcast tracks variant proportions at international airports — catching new subclades days before standard surveillance — but shares no timeline with wastewater data." },
              { tag: 'Silo C', title: 'Global Alert Feeds', body: "WHO Disease Outbreak News, ReliefWeb epidemic events, and Nextstrain phylogenetic data are all public — but nobody is fusing them with domestic wastewater and genomic signals." },
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
          <h2 className="lp-h2">Seven sources. One schema.</h2>
          <p className="lp-section-sub">
            Each stream has a public API. Biothreat Radar ingests all seven daily, normalizes them
            to a common schema, and synthesizes them into a single daily briefing.
          </p>
          <div className="lp-streams-grid">

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#0AA09A' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">CDC / WastewaterSCAN</div>
                <div className="lp-sc-name">Wastewater Surveillance</div>
                <div className="lp-sc-cadence">Updated weekly · NWSS national network</div>
                <p className="lp-sc-desc">Pathogen concentrations in sewage shed days to weeks before clinical cases surface. NWSS covers named pathogens across hundreds of US treatment plants.</p>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#5568D6' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">CDC Traveler Genomic Surveillance</div>
                <div className="lp-sc-name">Airport Genomics</div>
                <div className="lp-sc-cadence">Weekly Nowcast · 30+ international entry points</div>
                <p className="lp-sc-desc">Voluntary traveler swabs sequenced at international airports, surfacing SARS-CoV-2 variant proportions days before clinical or wastewater surveillance catches them.</p>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#2A9452' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">SecureBio / NCBI SRA</div>
                <div className="lp-sc-name">Environmental Metagenomics</div>
                <div className="lp-sc-cadence">Quarterly · 13 active sites · raw reads on NCBI</div>
                <p className="lp-sc-desc">Untargeted metagenomic sequencing of wastewater — no pathogen list required. Over 270 billion read pairs deposited to NCBI SRA. Detects novel sequences with no assigned name.</p>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#C87A0A' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">ReliefWeb / UN OCHA</div>
                <div className="lp-sc-name">Global Epidemic Events</div>
                <div className="lp-sc-cadence">Updated daily · worldwide coverage</div>
                <p className="lp-sc-desc">UN OCHA ReliefWeb tracks confirmed epidemic and outbreak events globally — cholera, Ebola, mpox, and more — with country-level location data.</p>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#C83030' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">WHO Disease Outbreak News</div>
                <div className="lp-sc-name">WHO DON</div>
                <div className="lp-sc-cadence">Official IHR outbreak declarations</div>
                <p className="lp-sc-desc">Formally declared International Health Regulation outbreak events from WHO — the most authoritative signal for cross-border biological threats.</p>
              </div>
            </div>

            <div className="lp-stream-card">
              <div className="lp-stream-stripe" style={{ background: '#8632BA' }} />
              <div className="lp-sc-body">
                <div className="lp-sc-source">Nextstrain</div>
                <div className="lp-sc-name">Phylogenetic Genomics</div>
                <div className="lp-sc-cadence">Real-time · H5N1 + Mpox datasets</div>
                <p className="lp-sc-desc">Open phylogenetic trees for H5N1 avian influenza and mpox — sequence counts by country and week, tracking genomic spread in near real-time.</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="lp-section lp-section-alt" id="fusion">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">The AI Layer</div>
          <h2 className="lp-h2">Seven streams. One daily briefing.</h2>
          <p className="lp-section-sub">
            Every morning, BTR ingests all seven streams, normalizes them to a common schema,
            runs anomaly detection, and passes the full picture to Claude to synthesize a
            professional intelligence briefing — ready before you start your day.
          </p>
          <div className="lp-fusion-diagram">
            <div className="lp-fusion-inputs">
              {[
                { color: '#0AA09A', text: 'NWSS site NE-07 — SARS-CoV-2 +18% week 35' },
                { color: '#5568D6', text: "TGS airports — XFG.1.1 at 32% of travelers" },
                { color: '#C87A0A', text: 'ReliefWeb — 3 new epidemic events, West Africa' },
                { color: '#8632BA', text: 'Nextstrain — H5N1 sequences rising in SE Asia' },
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
                <div className="lp-fe-label">AI Fusion Layer</div>
                <div className="lp-fe-name">Claude · Anomaly detection<br />+ schema normalization</div>
              </div>
              <div className="lp-alert-box">
                DAILY BRIEFING — August 31, 2026<br />
                XFG.1.1 dominant at US airports (32%). NWSS NE-07 elevated.
                WHO monitoring H5N1 cluster in Cambodia. No cross-stream
                concordance for novel threats at this time.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Scope ── */}
      <section className="lp-section" id="scope">
        <div className="lp-section-inner">
          <div className="lp-section-eyebrow">Scope</div>
          <h2 className="lp-h2">What this demo can and can't show.</h2>
          <p className="lp-section-sub">
            A proof of concept built on public data. An honest illustration of the fusion concept —
            not a claim that the full operational system described in federal budget documents exists.
          </p>
          <div className="lp-scope-grid">
            <div className="lp-scope-card lp-can">
              <h3>What the demo shows</h3>
              <ul>
                {[
                  'Live NWSS wastewater pathogen trends via public API',
                  'Weekly TGS Nowcast variant proportions at airports',
                  'SecureBio / NCBI SRA metagenomic sequencing signal',
                  'ReliefWeb and WHO DON global epidemic event tracking',
                  'Nextstrain H5N1 and Mpox phylogenetic sequence counts',
                  'AI-synthesized daily briefing from all seven streams',
                  'Filter-based briefing regeneration by pathogen, stream, region',
                  'Interactive Q&A: "Ask BTR" natural language data exploration',
                ].map(s => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div className="lp-scope-card">
              <h3>What would require more</h3>
              <ul>
                {[
                  'Nationwide 24-hour-turnaround novel pathogen detection',
                  'AMD negative-specimen data from private labs (not public)',
                  'A validated anomaly-detection model with published benchmarks',
                  'Aircraft wastewater integration beyond the current TGS pilot',
                  'Operational reliability guarantees on any external API',
                ].map(s => <li key={s}>{s}</li>)}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="lp-section lp-section-alt lp-cta-section" id="app">
        <div className="lp-section-inner lp-cta-inner">
          <div>
            <div className="lp-section-eyebrow">Live Demo</div>
            <h2 className="lp-h2">Seven streams. One briefing. Updated daily.</h2>
            <p className="lp-section-sub">
              See the streams in motion. Today's AI briefing is ready — or ask BTR anything
              about the surveillance data directly.
            </p>
          </div>
          <div className="lp-cta-btns">
            <Link to="/briefing" className="lp-btn lp-btn-primary">View Today's Briefing →</Link>
            <Link to="/intel" className="lp-btn lp-btn-ghost">Ask BTR a Question</Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-logo">Biothreat Radar</div>
        <div className="lp-footer-note">
          Built on public data. No proprietary data required.<br />
          NWSS · TGS · SBD · WHO DON · ReliefWeb · NCBI SRA · Nextstrain
        </div>
        <div className="lp-footer-links">
          <Link to="/about">About</Link>
          <Link to="/briefing">Briefing</Link>
          <Link to="/intel">Intel</Link>
          <Link to="/data">Data</Link>
        </div>
      </footer>

    </div>
  )
}
