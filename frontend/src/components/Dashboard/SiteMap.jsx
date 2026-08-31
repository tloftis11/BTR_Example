import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { useEffect } from 'react'

const STREAM_COLORS = {
  nwss: '#0891B2',
  tgs:  '#7C3AED',
  sbd:  '#059669',
}

function FitBounds({ sites }) {
  const map = useMap()
  useEffect(() => {
    if (!sites?.length) return
    const valid = sites.filter(s => s.lat && s.lon)
    if (!valid.length) return
    const bounds = valid.map(s => [s.lat, s.lon])
    map.fitBounds(bounds, { padding: [40, 40] })
  }, [sites, map])
  return null
}

export default function SiteMap({ sites = [] }) {
  const valid = sites.filter(s => s.lat && s.lon)

  return (
    <MapContainer
      center={[38.5, -95]}
      zoom={4}
      style={{ height: '100%', width: '100%' }}
      zoomControl={true}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={19}
      />

      <FitBounds sites={valid} />

      {valid.map(site => {
        const color = STREAM_COLORS[site.source] || '#64748B'
        const anomaly = site.has_anomaly
        return (
          <CircleMarker
            key={site.site_id}
            center={[site.lat, site.lon]}
            radius={anomaly ? 8 : 5}
            pathOptions={{
              fillColor: anomaly ? '#DC2626' : color,
              fillOpacity: anomaly ? 0.9 : 0.75,
              color: anomaly ? '#991B1B' : color,
              weight: anomaly ? 2 : 1,
            }}
          >
            <Popup>
              <div className="popup-source">{site.source.toUpperCase()}</div>
              <div className="popup-name">{site.site_name || site.site_id}</div>
              {site.state && <div className="popup-value">{site.state}</div>}
              {site.latest_value != null && (
                <div className="popup-value">
                  {site.metric}: {site.latest_value.toFixed(3)}
                </div>
              )}
              {anomaly && (
                <div style={{ color: '#DC2626', fontSize: 11, marginTop: 4, fontWeight: 500 }}>
                  ⚠ Anomaly flagged
                </div>
              )}
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
