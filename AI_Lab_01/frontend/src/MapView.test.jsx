import React from 'react'
import {act, render, screen} from '@testing-library/react'
import {beforeEach, afterEach, expect, it, vi} from 'vitest'
const state = vi.hoisted(() => ({events: null, map: null}))
vi.mock('react-leaflet', () => ({
  MapContainer: ({children}) => <div>{children}</div>,
  TileLayer: () => null,
  Polyline: () => <div data-testid="road-layer"/>,
  CircleMarker: () => null,
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
