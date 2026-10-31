import React from 'react'
import {it, expect, vi, beforeEach} from 'vitest'
import {render, screen, fireEvent, waitFor} from '@testing-library/react'
vi.mock('./MapView', () => ({default: props => <div data-testid="map" data-results={props.results.length} data-trace-node={props.traceNode?.id} data-area-radius={props.scenarioAreas?.[0]?.radius_m}><button onClick={() => props.onPoint({lat: 23.77, lng: 90.4})}>Map point</button><button onClick={() => props.onRoad({properties: {id: '1:2:0', name: 'Test road', u: '1', v: '2', key: '0', length_m: 100, cost: 0.1, conditions: {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}}})}>Inspect road</button></div>}))
vi.mock('recharts', () => ({ResponsiveContainer: () => null, BarChart: () => null, Bar: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null, Cell: () => null}))
import App from './App'
const stats = {ready: true, nodes: 10, edges: 20, places: 0, categories: {}, metadata: {}, revision: 0}
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url, options) => {
    let data
    if (url.includes('/metadata')) data = stats
    else if (url.includes('/scenarios')) data = [{id: 'normal', name: 'Normal Day', builtin: true, conditions: {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}}]
    else if (url.includes('/resolve')) data = {node: '1', lat: 23.77, lon: 90.4, distance_m: 5}
    else if (url.includes('/routes')) data = {scenario: 'normal', scenario_name: 'Normal Day', revision: 0, snapshot: 'v1', heuristic_cost_per_km: 1, results: [{algorithm: 'A*', found: false, status: 'unreachable', nodes: [], edges: [], geometry: null, expanded: 1, generated: 1, execution_ms: .1, trace: ['123'], trace_points: [[90.4, 23.77]]}]}
    else data = {}
    return {ok: true, json: async () => data}
  }))
})
it('shows missing dataset without fabricating routes', async () => {
  fetch.mockImplementation(async url => ({ok: true, json: async () => url.includes('/metadata') ? {...stats, ready: false, error: 'Road dataset missing'} : []}))
  render(<App/>)
  await screen.findByText('Real road data has not been loaded.')
  expect(screen.getByRole('button', {name: 'Run A* →'})).toBeDisabled()
  expect(screen.getByTestId('map')).toHaveAttribute('data-results', '0')
})
it('selects map endpoints, runs search, reports no route and marks changed endpoints stale', async () => {
  render(<App/>)
  await screen.findByText('● Dataset ready')
  fireEvent.click(screen.getByText('Pick start on map'))
  fireEvent.click(screen.getByText('Map point'))
  await screen.findByLabelText('Clear Start')
  fireEvent.click(screen.getByText('Pick destination'))
  fireEvent.click(screen.getByText('Map point'))
  await screen.findByLabelText('Clear Destination')
  fireEvent.click(screen.getByRole('button', {name: 'Run A* →'}))
  await screen.findByText('unreachable')
  expect(screen.getByTestId('map')).toHaveAttribute('data-results', '1')
  const request = fetch.mock.calls.find(([url]) => url.includes('/routes'))
  expect(JSON.parse(request[1].body).trace_limit).toBe(5000)
  fireEvent.click(screen.getByRole('button', {name: '123'}))
  expect(screen.getByTestId('map')).toHaveAttribute('data-trace-node', '123')
  expect(screen.getByText('Node 123: latitude 23.770000, longitude 90.400000')).toBeInTheDocument()
  fireEvent.click(screen.getByLabelText('Clear Start'))
  await screen.findByText(/Results are stale/)
  expect(screen.getByRole('button', {name: '123'})).toBeDisabled()
  expect(screen.getByTestId('map')).not.toHaveAttribute('data-trace-node')
  expect(screen.getByTestId('map')).toHaveAttribute('data-results', '0')
  fireEvent.click(screen.getByRole('checkbox', {name: 'BFS'}))
  expect(screen.getByRole('checkbox', {name: 'BFS'})).not.toBeChecked()
})
it('opens directed road editor', async () => {
  render(<App/>)
  await screen.findByText('● Dataset ready')
  fireEvent.click(screen.getByText('Inspect road'))
  expect(screen.getByText('Test road')).toBeInTheDocument()
  expect(screen.getByLabelText('Road traffic')).toHaveValue('0')
  expect(screen.getByRole('button', {name: 'Apply conditions to this road'})).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Road traffic'), {target: {value: '1'}})
  expect(screen.getByText('These changes are not applied yet. Use the button below.')).toBeInTheDocument()
  expect(screen.getByRole('button', {name: 'Apply conditions to this road'})).toBeEnabled()
})

it('recovers after a backend restart when the user checks dataset status', async () => {
  let ready = false
  const original = fetch.getMockImplementation()
  fetch.mockImplementation(async (url, options) => url.includes('/metadata') ? {ok: true, json: async () => ({...stats, ready, places: ready ? 10 : 0, error: ready ? null : 'Road dataset missing'})} : original(url, options))
  render(<App/>)
  await screen.findByText('Real road data has not been loaded.')
  expect(screen.getByLabelText('Start')).toBeDisabled()
  expect(screen.getByText('setup_data.bat')).toBeInTheDocument()
  ready = true
  fireEvent.click(screen.getByRole('button', {name: 'Check dataset status'}))
  await screen.findByText('● Dataset ready')
  expect(screen.queryByText('Real road data has not been loaded.')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Start')).toBeEnabled()
})

it('enables routing with an installed graph while warning about incomplete place coverage', async () => {
  const original = fetch.getMockImplementation()
  fetch.mockImplementation(async (url, options) => url.includes('/metadata') ? {ok: true, json: async () => ({...stats, places: 12, metadata: {places_complete: false, completed_place_tiles: 4, total_place_tiles: 9}})} : original(url, options))
  render(<App/>)
  await screen.findByText('Road routing is ready; place coverage is incomplete.')
  expect(screen.queryByText('Real road data has not been loaded.')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Start')).toBeEnabled()
  expect(screen.getByText('Pick start on map')).toBeEnabled()
  expect(screen.getByText(/4 of 9 place tiles installed/)).toBeInTheDocument()
})

it('places a scenario circle with a map click without resolving a route endpoint', async () => {
  render(<App/>)
  await screen.findByText('● Dataset ready')
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.change(screen.getByLabelText('Apply conditions to'), {target: {value: 'circle'}})
  fireEvent.click(screen.getByText('Add circle on map'))
  fireEvent.click(screen.getByText('Map point'))
  expect(screen.getByTestId('map')).toHaveAttribute('data-area-radius', '500')
  expect(fetch.mock.calls.some(([url]) => url.includes('/resolve'))).toBe(false)
  fireEvent.change(screen.getByLabelText('Circle 1 radius (metres)'), {target: {value: '1000'}})
  expect(screen.getByTestId('map')).toHaveAttribute('data-area-radius', '1000')
})
