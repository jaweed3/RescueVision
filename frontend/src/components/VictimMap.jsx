// VictimMap.jsx — Leaflet map showing victim coordinates
import { MapContainer, TileLayer, Popup, CircleMarker } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix leaflet default icon
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

export default function VictimMap({ detections }) {
  const validDetections = detections.filter(d => d.lat && d.lon)
  if (!validDetections.length) return null

  const center = [
    validDetections.reduce((s, d) => s + d.lat, 0) / validDetections.length,
    validDetections.reduce((s, d) => s + d.lon, 0) / validDetections.length,
  ]

  return (
    <div style={{ borderRadius: 12, overflow: 'hidden', height: 300, marginTop: 16 }}>
      <MapContainer center={center} zoom={17} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />
        {validDetections.map(d => (
          <CircleMarker
            key={d.id}
            center={[d.lat, d.lon]}
            radius={10}
            fillColor="#ef4444"
            color="#ffffff"
            weight={2}
            fillOpacity={0.8}
          >
            <Popup>
              <strong>Korban #{d.id}</strong><br />
              Confidence: {(d.confidence * 100).toFixed(1)}%<br />
              Lat: {d.lat.toFixed(6)}<br />
              Lon: {d.lon.toFixed(6)}<br />
              Akurasi: ±{d.accuracy_m}m
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
