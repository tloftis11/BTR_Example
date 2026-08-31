export default function AboutPage() {
  return (
    <div style={{ maxWidth: 680 }}>
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <div className="page-title">About Biothreat Radar</div>
          <div className="page-sub">What this is, what it can honestly show, and what it can't</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="card-header"><span className="card-title">Data Sources</span></div>
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', fontSize: 14, lineHeight: 1.7 }}>
          <div>
            <strong>NWSS / WastewaterSCAN</strong>
            <p className="text-muted" style={{ marginTop: 4 }}>
              CDC's National Wastewater Surveillance System reports SARS-CoV-2 concentrations from
              ~3,000 treatment plants, updated weekly. Data is fetched via the CDC Open Data Socrata API
              (data.cdc.gov). WastewaterSCAN, a Stanford/Emory/Verily collaboration, extends the pathogen panel.
            </p>
          </div>
          <div>
            <strong>Traveler Genomic Surveillance (TGS)</strong>
            <p className="text-muted" style={{ marginTop: 4 }}>
              CDC's voluntary traveler swab program sequences respiratory pathogens at major international airports.
              Over 1 million participants enrolled. The Nowcast publishes weekly variant proportion estimates.
              Airport-level data is approximated from national CDC variant proportion data (data.cdc.gov).
            </p>
          </div>
          <div>
            <strong>SecureBio Detection</strong>
            <p className="text-muted" style={{ marginTop: 4 }}>
              The group formerly known as the Nucleic Acid Observatory runs untargeted metagenomic sequencing at
              ~13 US wastewater sites, depositing raw reads on NCBI SRA (PRJNA729801). A public dashboard is
              available at securebio.org/detection. Site locations are fixed; signal values are fetched when
              a machine-readable API is available.
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Scope and Honest Limitations</span></div>
        <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', fontSize: 14, lineHeight: 1.7 }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>What this system shows</div>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                'Live NWSS pathogen trends via CDC public API',
                'Weekly TGS variant proportions at airports',
                'SecureBio Detection site presence and signal',
                'All three overlaid on a shared map and timeline',
                'Z-score anomaly detection across all streams',
              ].map(s => (
                <li key={s} style={{ display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--ok)', flexShrink: 0 }}>✓</span>
                  <span className="text-muted">{s}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>What would require more</div>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                'Nationwide 24h novel pathogen detection (~13 sites → hundreds)',
                'AMD negative-specimen data via private labs (not public)',
                'Validated anomaly model with published benchmarks',
                'Aircraft wastewater beyond current TGS pilot scope',
              ].map(s => (
                <li key={s} style={{ display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--tx-faint)', flexShrink: 0 }}>—</span>
                  <span className="text-muted">{s}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
