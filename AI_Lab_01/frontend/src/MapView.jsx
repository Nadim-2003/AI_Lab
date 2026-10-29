import React, {useEffect, useState} from 'react'
import {MapContainer, TileLayer, Polyline, CircleMarker, Tooltip, useMap, useMapEvents} from 'react-leaflet'
import L from 'leaflet'
import {api, colors, toLeaflet} from './api'

function Viewport({onBounds, selectionMode, onPoint}) {
  const map = useMapEvents({moveend: () => report(), click: event => {if (selectionMode) onPoint(event.latlng)}})
  function report() {const b = map.getBounds(); onBounds({west: b.getWest(), east: b.getEast(), south: b.getSouth(), north: b.getNorth(), zoom: map.getZoom()})}
  useEffect(() => {report()}, [])
  return null
}
function Focus({route, focusKey}) {
  const map = useMap()
  useEffect(() => {const points = toLeaflet(route?.geometry); if (points.length > 1) map.fitBounds(L.latLngBounds(points), {padding: [40, 40]})}, [focusKey])
  return null
}
function StudyArea({bbox}) {
  const map = useMap()
  const [west, south, east, north] = bbox || []
  useEffect(() => {
    if ([west, south, east, north].every(Number.isFinite) && west < east && south < north) {
      map.fitBounds([[south, west], [north, east]], {padding: [20, 20]})
    }
  }, [west, south, east, north, map])
  return null
}
export default function MapView({ready = false, studyBounds, scenario, revision, results, visible, selected, start, destination, selectionMode, onPoint, onRoad, roadClass, placeCategory, showPlaces, showTrace, focusKey, onError}) {
  const [bounds, setBounds] = useState(null)
  const [roads, setRoads] = useState({features: []})
  const [places, setPlaces] = useState([])
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (!ready || !bounds) {
      setRoads({features: []}); setPlaces([]); setLoading(false)
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      setLoading(true)
      const params = new URLSearchParams({...bounds, scenario, road_class: roadClass})
      api(`/roads?${params}`, {signal: controller.signal}).then(setRoads).catch(e => {if (e.name !== 'AbortError') {setRoads({features: []}); onError(e.message)}}).finally(() => {if (!controller.signal.aborted) setLoading(false)})
      if (showPlaces && bounds.zoom >= 13) api(`/places?${new URLSearchParams({...bounds, category: placeCategory, limit: 100})}`, {signal: controller.signal}).then(setPlaces).catch(e => {if (e.name !== 'AbortError') onError(e.message)})
      else setPlaces([])
    }, 200)
    return () => {clearTimeout(timer); controller.abort()}
  }, [ready, bounds, scenario, revision, roadClass, placeCategory, showPlaces])
  const chosen = results.find(r => r.algorithm === selected)
  const sorted = [...results].sort((a, b) => (a.algorithm === selected) - (b.algorithm === selected))
  return <div className={`map-shell ${selectionMode ? 'selecting' : ''}`}>
    <MapContainer center={[23.732, 90.3985]} zoom={14} scrollWheelZoom className="map">
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'/>
      <StudyArea bbox={studyBounds}/>
      <Viewport onBounds={setBounds} selectionMode={selectionMode} onPoint={onPoint}/>
      <Focus route={chosen} focusKey={focusKey}/>
      {roads.features.map(road => {
        const c = road.properties.conditions
        const penalized = ['traffic', 'condition', 'rain', 'safety'].some(key => Number(c[key]) > 0)
        return <Polyline key={road.properties.id} positions={toLeaflet(road.geometry)} pathOptions={{color: c.blocked ? '#d32f43' : penalized ? '#d59932' : '#517e80', weight: c.blocked ? 5 : 3, opacity: 0.65, dashArray: c.blocked ? '5 7' : undefined, bubblingMouseEvents: false}} eventHandlers={{click: event => {L.DomEvent.stopPropagation(event.originalEvent); selectionMode ? onPoint(event.latlng) : onRoad(road)}}}><Tooltip>{road.properties.name || 'Unnamed road'} · {road.properties.u} → {road.properties.v}</Tooltip></Polyline>
      })}
      {places.map(place => <CircleMarker key={place.id} center={[place.lat, place.lon]} radius={4} pathOptions={{color: '#567bb3', fillOpacity: 0.8}}><Tooltip>{place.name} · {place.category}</Tooltip></CircleMarker>)}
      {showTrace && chosen?.trace_points.map(([lon, lat], i) => <CircleMarker key={`trace-${i}`} center={[lat, lon]} radius={3} pathOptions={{color: colors[chosen.algorithm], opacity: 0.4, fillOpacity: 0.3, interactive: false}}/>)}
      {sorted.filter(r => r.found && visible[r.algorithm] && r.geometry).map((route, i) => <Polyline key={route.algorithm} positions={toLeaflet(route.geometry)} pathOptions={{color: colors[route.algorithm], weight: route.algorithm === selected ? 7 : 4, opacity: 0.9, dashArray: route.algorithm === selected ? undefined : `${6 + i * 3} ${3 + i * 2}`, interactive: false}}/>)}
      {[['Start', start, '#0e9e81'], ['Destination', destination, '#e04b65']].map(([label, point, color]) => point && <CircleMarker key={label} center={[point.lat, point.lon]} radius={9} pathOptions={{color: 'white', weight: 3, fillColor: color, fillOpacity: 1}}><Tooltip permanent>{label}: {point.name}</Tooltip></CircleMarker>)}
    </MapContainer>
    <div className="map-note">{!ready ? 'Road layers unavailable until the dataset is loaded' : loading ? 'Loading roads…' : selectionMode ? `Click the map to set ${selectionMode}` : 'Click a road to inspect its directed edge'}{roads.truncated && <span> · Showing {roads.features.length} of {roads.matched} edges; zoom in</span>}</div>
    <div className="map-key"><i className="road-dot"/> OSM roads <i className="amber-dot"/> Simulated penalties <i className="red-dot"/> Closed</div>
  </div>
}
