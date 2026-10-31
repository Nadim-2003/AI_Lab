import React from 'react'
import {act, render, screen} from '@testing-library/react'
import {beforeEach, afterEach, expect, it, vi} from 'vitest'
const state = vi.hoisted(() => ({events: null, map: null, marker: null, circle: null}))
vi.mock('react-leaflet', () => ({
  MapContainer: ({children}) => <div>{children}</div>,
  TileLayer: () => null,
  Polyline: () => <div data-testid="road-layer"/>,
  CircleMarker: () => null,
  Circle: React.forwardRef(({center, radius}, ref) => {
    React.useImperativeHandle(ref, () => state.circle)
    return <div data-testid="scenario-circle" data-center={center.join(',')} data-radius={radius}/>
  }),
  Marker: props => {state.marker = props; return <div data-testid="circle-handle"/>},
  Tooltip: () => null,
  useMap: () => state.map,
  useMapEvents: events => {
    state.events = events
    return {getBounds: () => ({getWest: () => 90.3, getEast: () => 90.5, getSouth: () => 23.7, getNorth: () => 23.9}), getZoom: () => 14}
  },
}))
import MapView from './MapView'
const props = {scenario: 'normal', revision: 0, results: [], visible: {}, selected: 'A*', showPlaces: true, onError: vi.fn()}
beforeEach(() => {
  state.circle = {setLatLng: vi.fn()}
  state.map = {fitBounds: vi.fn(), setView: vi.fn(), getZoom: () => 14}
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn(async url => ({ok: true, json: async () => url.includes('/roads') ? {features: [{properties: {id: '1:2:0', conditions: {traffic: 0, rain: 0, safety: 0}}, geometry: {coordinates: [[90.4, 23.7], [90.41, 23.71]]}}]} : []})))
})
afterEach(() => {vi.useRealTimers(); vi.unstubAllGlobals()})
it('does not request roads or places while unavailable, even after map movement', async () => {
  render(<MapView {...props} ready={false}/>)
  await act(async () => {state.events.moveend(); await vi.advanceTimersByTimeAsync(500)})
  expect(fetch).not.toHaveBeenCalled()
  expect(screen.getByText('Road layers unavailable until the dataset is loaded')).toBeInTheDocument()
})
it('loads real layers when readiness changes and clears them if readiness is lost', async () => {
  const {rerender} = render(<MapView {...props} ready={false}/>)
  rerender(<MapView {...props} ready/>)
  await act(async () => {await vi.advanceTimersByTimeAsync(250)})
  expect(fetch.mock.calls.some(([url]) => url.startsWith('/api/roads?'))).toBe(true)
  expect(fetch.mock.calls.some(([url]) => url.startsWith('/api/places?'))).toBe(true)
  expect(screen.getByTestId('road-layer')).toBeInTheDocument()
  const calls = fetch.mock.calls.length
  rerender(<MapView {...props} ready={false}/>)
  await act(async () => {state.events.moveend(); await vi.advanceTimersByTimeAsync(500)})
  expect(screen.queryByTestId('road-layer')).not.toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(calls)
})

it('fits loaded study bounds once without resetting the map on metadata polls', () => {
  const {rerender} = render(<MapView {...props} ready studyBounds={[90.385, 23.718, 90.412, 23.746]}/>)
  expect(state.map.fitBounds).toHaveBeenCalledWith([[23.718, 90.385], [23.746, 90.412]], {padding: [20, 20]})
  const count = state.map.fitBounds.mock.calls.length
  rerender(<MapView {...props} ready studyBounds={[90.385, 23.718, 90.412, 23.746]}/>)
  expect(state.map.fitBounds).toHaveBeenCalledTimes(count)
  rerender(<MapView {...props} ready studyBounds={[90.3, 23.65, 90.5, 23.9]}/>)
  expect(state.map.fitBounds).toHaveBeenLastCalledWith([[23.65, 90.3], [23.9, 90.5]], {padding: [20, 20]})
})

it('centers the map on the selected trace node, including repeated selection', () => {
  const point = {id: '123', lat: 23.77, lon: 90.4}
  const {rerender} = render(<MapView {...props} traceNode={point}/>)
  expect(state.map.setView).toHaveBeenCalledWith([23.77, 90.4], 17)
  rerender(<MapView {...props} traceNode={{...point}}/>)
  expect(state.map.setView).toHaveBeenCalledTimes(2)
})

it('moves a draft circle through its draggable center without changing its radius', () => {
  const move = vi.fn()
  const area = {lat: 23.77, lon: 90.4, radius_m: 1500, conditions: {rain: 1}}
  const {rerender} = render(<MapView {...props} scenarioAreas={[area]} onAreaMove={move}/>)
  expect(state.marker.draggable).toBe(true)
  state.marker.eventHandlers.drag({target: {getLatLng: () => ({lat: 23.78, lng: 90.41})}})
  expect(state.circle.setLatLng).toHaveBeenCalledWith({lat: 23.78, lng: 90.41})
  expect(move).not.toHaveBeenCalled()
  for (let i = 0; i < 100; i++) state.marker.eventHandlers.drag({target: {getLatLng: () => ({lat: 23.78, lng: 90.41})}})
  expect(move).not.toHaveBeenCalled()
  state.marker.eventHandlers.dragend({target: {getLatLng: () => ({lat: 23.78, lng: 90.41})}})
  expect(move).toHaveBeenCalledTimes(1)
  expect(move).toHaveBeenCalledWith(0, {...area, lat: 23.78, lon: 90.41})
  rerender(<MapView {...props} scenarioAreas={[move.mock.calls[0][1]]} onAreaMove={move}/>)
  expect(screen.getByTestId('scenario-circle')).toHaveAttribute('data-center', '23.78,90.41')
  rerender(<MapView {...props} scenarioAreas={[area]}/>)
  expect(screen.queryByTestId('circle-handle')).not.toBeInTheDocument()
})
