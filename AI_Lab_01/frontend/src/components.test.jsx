import React from 'react'
import {describe, it, expect, vi, beforeEach} from 'vitest'
import {render, screen, fireEvent, waitFor} from '@testing-library/react'
import Autocomplete from './Autocomplete'
import Conditions from './Conditions'
import ScenarioManager from './ScenarioManager'
import {toLeaflet, api} from './api'

beforeEach(() => {vi.restoreAllMocks()})
const mockResponse = value => ({ok: true, json: async () => value})

describe('coordinates and errors', () => {
  it('preserves curved road points while converting GeoJSON to Leaflet order', () => {
    expect(toLeaflet({coordinates: [[90.4, 23.77], [90.401, 23.772], [90.403, 23.771]]})).toEqual([[23.77, 90.4], [23.772, 90.401], [23.771, 90.403]])
    expect(toLeaflet(null)).toEqual([])
  })
  it('surfaces backend validation errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: false, json: async () => ({detail: 'Too far from a road'})}))
    await expect(api('/resolve')).rejects.toThrow('Too far from a road')
  })
})

describe('place autocomplete', () => {
  it('opens a place dropdown before the user types', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse([{id: 'node/1', name: 'Dhaka University', category: 'amenity:university', lat: 23.73, lon: 90.39}])))
    render(<Autocomplete label="Destination" value={null} onChange={vi.fn()} onError={vi.fn()}/>)
    fireEvent.focus(screen.getByRole('combobox'))
    expect(await screen.findByRole('listbox', {name: 'Destination places'})).toBeInTheDocument()
    expect(await screen.findByRole('option')).toHaveTextContent('Dhaka University')
    expect(fetch.mock.calls[0][0]).toContain('q=&limit=25')
  })

  it('supports keyboard selection and resolves a real selected result', async () => {
    const changed = vi.fn()
    vi.stubGlobal('fetch', vi.fn().mockImplementation(url => Promise.resolve(mockResponse(url.includes('/places') ? [{id: 'node/1', name: 'ঢাকা', category: 'place:city', lat: 23.77, lon: 90.4}] : {node: '42', lat: 23.77, lon: 90.4, distance_m: 5}))))
    render(<Autocomplete label="Start" value={null} onChange={changed} onError={vi.fn()}/>)
    fireEvent.change(screen.getByRole('combobox'), {target: {value: 'ঢা'}})
    await screen.findByRole('option')
    fireEvent.keyDown(screen.getByRole('combobox'), {key: 'Enter'})
    await waitFor(() => expect(changed).toHaveBeenCalledWith(expect.objectContaining({node: '42', name: 'ঢাকা'})))
    expect(fetch.mock.calls[1][0]).toContain('/resolve')
  })
  it('can clear an existing selection', () => {
    const changed = vi.fn()
    render(<Autocomplete label="Destination" value={{name: 'Selected', node: '1', distance_m: 4}} onChange={changed} onError={vi.fn()}/>)
    fireEvent.click(screen.getByRole('button', {name: 'Clear Destination'}))
    expect(changed).toHaveBeenCalledWith(null)
  })
  it('shows empty results', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse([])))
    render(<Autocomplete label="Start" value={null} onChange={vi.fn()} onError={vi.fn()}/>)
    fireEvent.change(screen.getByRole('combobox'), {target: {value: 'missing'}})
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    await screen.findByText('No matching places')
  })
})

describe('condition editing', () => {
  it('changes only the requested severity or directed closure', () => {
    const changed = vi.fn(), value = {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}
    render(<Conditions value={value} onChange={changed}/>)
    fireEvent.change(screen.getByLabelText('Road traffic'), {target: {value: '1'}})
    expect(changed).toHaveBeenLastCalledWith({...value, traffic: 1})
    fireEvent.click(screen.getByRole('checkbox'))
    expect(changed).toHaveBeenLastCalledWith({...value, blocked: true})
  })
})

describe('scenario studio', () => {
  it('duplicates and persists the active scenario', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'custom-1'})))
    const saved = vi.fn()
    const current = {id: 'normal', builtin: true, name: 'Normal Day', description: '', conditions: {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}, road_classes: [], edges: {}, weights: {traffic: 2, condition: 1, rain: 2, safety: 1}}
    render(<ScenarioManager current={current} onSaved={saved} onError={vi.fn()}/>)
    fireEvent.click(screen.getByText('Custom scenario studio'))
    fireEvent.click(screen.getByText('Duplicate active'))
    expect(screen.getByLabelText('Name')).toHaveValue('Normal Day copy')
    fireEvent.change(screen.getByLabelText('Road classes'), {target: {value: 'primary'}})
    fireEvent.change(screen.getByLabelText('Road classes'), {target: {value: 'residential'}})
    fireEvent.click(screen.getByLabelText('Remove road class primary'))
    expect(screen.getByLabelText('Remove road class residential')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Road classes'), {target: {value: 'all'}})
    expect(screen.queryByLabelText('Remove road class residential')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Road classes'), {target: {value: 'secondary'}})
    fireEvent.click(screen.getByText('Create scenario'))
    await waitFor(() => expect(saved).toHaveBeenCalledWith('custom-1'))
    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body.name).toBe('Normal Day copy')
    expect(body.road_classes).toEqual(['secondary'])
    expect(body).not.toHaveProperty('builtin')
  })
})

describe('unavailable place dataset', () => {
  it('disables autocomplete and does not issue searches until enabled', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse([])))
    const props = {label: 'Start', value: null, onChange: vi.fn(), onError: vi.fn()}
    const {rerender} = render(<Autocomplete {...props} disabled/>)
    expect(screen.getByRole('combobox')).toBeDisabled()
    fireEvent.change(screen.getByRole('combobox'), {target: {value: 'dhaka'}})
    expect(fetch).not.toHaveBeenCalled()
    rerender(<Autocomplete {...props} disabled={false}/>)
    expect(screen.getByRole('combobox')).toBeEnabled()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
  })
})

it('saves selected-roads scope without requiring global conditions to be reset', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'local'})))
  const saved = vi.fn()
  render(<ScenarioManager road={{properties: {id: 'a:b:0'}}} onSaved={saved} onError={vi.fn()}/>)
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.change(screen.getByLabelText('Name'), {target: {value: 'Local rain'}})
  fireEvent.change(screen.getByLabelText('Apply conditions to'), {target: {value: 'selected_roads'}})
  expect(screen.getByLabelText('Apply conditions to')).toHaveValue('selected_roads')
  expect(screen.getByText('Create scenario')).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Scenario rain'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('Add selected directed road with these conditions'))
  fireEvent.click(screen.getByText('Create scenario'))
  await waitFor(() => expect(saved).toHaveBeenCalledWith('local'))
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.scope).toBe('selected_roads')
  expect(body.edges['a:b:0'].rain).toBe(1)
  expect(body.conditions.rain).toBe(1)
})

it('picks and resizes a circle and saves its area with the scenario', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'circle'})))
  const saved = vi.fn(), pick = vi.fn()
  function Studio() {
    const [areas, setAreas] = React.useState([])
    return <ScenarioManager areas={areas} onAreasChange={setAreas} onPickArea={() => {pick(); setAreas(previous => [...(previous || []), {lat: 23.77, lon: 90.4, radius_m: 500}])}} onSaved={saved} onError={vi.fn()}/>
  }
  render(<Studio/>)
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.change(screen.getByLabelText('Name'), {target: {value: 'Circle rain'}})
  fireEvent.change(screen.getByLabelText('Apply conditions to'), {target: {value: 'circle'}})
  expect(screen.getByText('Create scenario')).toBeDisabled()
  fireEvent.click(screen.getByText('Add circle on map'))
  expect(pick).toHaveBeenCalledOnce()
  fireEvent.change(screen.getByLabelText('Circle 1 radius (metres)'), {target: {value: '1500'}})
  fireEvent.click(screen.getByText('Add circle on map'))
  fireEvent.change(screen.getByLabelText('Circle 2 radius (metres)'), {target: {value: '2500'}})
  expect(screen.getByLabelText('Circle 1 radius (metres)')).toHaveValue('1500')
  fireEvent.click(screen.getByText('Remove circle 2'))
  expect(screen.queryByLabelText('Circle 2 radius (metres)')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Add circle on map'))
  fireEvent.change(screen.getByLabelText('Circle 1 rain'), {target: {value: '1'}})
  fireEvent.change(screen.getByLabelText('Circle 2 traffic'), {target: {value: '1'}})
  fireEvent.change(screen.getByLabelText('Scenario rain'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('Create scenario'))
  await waitFor(() => expect(saved).toHaveBeenCalledWith('circle'))
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.scope).toBe('circle')
  expect(body.areas[0]).toMatchObject({radius_m: 1500, conditions: {rain: 1, traffic: 0}})
  expect(body.areas[1]).toMatchObject({radius_m: 500, conditions: {rain: 0, traffic: 1}})
  expect(body.conditions.rain).toBe(1)
})

it('edits each selected road independently inside one scenario', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'roads'})))
  const saved = vi.fn()
  const normal = {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}
  const current = {id: 'roads', builtin: false, name: 'Two roads', description: '', scope: 'selected_roads', road_classes: [], conditions: normal, edges: {'a:b:0': {...normal}, 'b:c:0': {...normal}}, weights: {traffic: 2, condition: 1, rain: 2, safety: 1}}
  render(<ScenarioManager current={current} onSaved={saved} onError={vi.fn()}/>)
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.click(screen.getByText('Edit active'))
  fireEvent.click(screen.getByText('a:b:0 · open'))
  fireEvent.change(screen.getByLabelText('Selected road a:b:0 rain'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('b:c:0 · open'))
  fireEvent.change(screen.getByLabelText('Selected road b:c:0 traffic'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('Update scenario'))
  await waitFor(() => expect(saved).toHaveBeenCalledWith('roads'))
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.edges['a:b:0']).toMatchObject({rain: 1, traffic: 0})
  expect(body.edges['b:c:0']).toMatchObject({rain: 0, traffic: 1})
})

it('saves circle, selected-road, and class groups in one scenario with shared weights', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'mixed'})))
  const saved = vi.fn()
  function Studio() {
    const [areas, setAreas] = React.useState([])
    return <ScenarioManager areas={areas} onAreasChange={setAreas} onPickArea={index => setAreas(previous => previous.map((area, i) => i === index ? {lat: 23.77, lon: 90.4, radius_m: 500} : area))} road={{properties: {id: 'a:b:0'}}} onSaved={saved} onError={vi.fn()}/>
  }
  render(<Studio/>)
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.change(screen.getByLabelText('Name'), {target: {value: 'Mixed'}})
  expect(screen.getByLabelText('Apply conditions to')).toHaveValue('groups')
  expect(screen.getByText('Create scenario')).toBeDisabled()
  fireEvent.click(screen.getByText('Add condition'))
  fireEvent.change(screen.getByLabelText('Condition 1 applies to'), {target: {value: 'classes'}})
  fireEvent.change(screen.getByLabelText('Condition 1 road classes'), {target: {value: 'primary'}})
  fireEvent.change(screen.getByLabelText('Condition 1 traffic'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('Add condition'))
  fireEvent.change(screen.getByLabelText('Condition 2 applies to'), {target: {value: 'roads'}})
  expect(screen.getByText('Create scenario')).toBeDisabled()
  fireEvent.click(screen.getByText('Add selected road to condition 2'))
  fireEvent.change(screen.getByLabelText('Condition 2 condition'), {target: {value: '1'}})
  fireEvent.click(screen.getByText('Add condition'))
  expect(screen.getByText('Create scenario')).toBeDisabled()
  fireEvent.click(screen.getByText('Pick condition 3 circle'))
  fireEvent.change(screen.getByLabelText('Condition 3 rain'), {target: {value: '1'}})
  fireEvent.change(screen.getByLabelText('traffic weight'), {target: {value: '4'}})
  fireEvent.click(screen.getByText('Create scenario'))
  await waitFor(() => expect(saved).toHaveBeenCalledWith('mixed'))
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.scope).toBe('groups')
  expect(body.weights.traffic).toBe(4)
  expect(body.groups[0]).toMatchObject({target: 'classes', road_classes: ['primary'], conditions: {traffic: 1}})
  expect(body.groups[1]).toMatchObject({target: 'roads', road_ids: ['a:b:0'], conditions: {condition: 1}})
  expect(body.groups[2]).toMatchObject({target: 'circle', area: {lat: 23.77, lon: 90.4, radius_m: 500}, conditions: {rain: 1}})
  expect(body.edges).toEqual({})
})

it('restores groups for editing and keeps the correct circle after a group is removed', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({id: 'existing'})))
  const saved = vi.fn()
  const normal = {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}
  const current = {id: 'existing', builtin: false, name: 'Existing groups', description: '', scope: 'groups', conditions: normal, road_classes: [], edges: {}, weights: {traffic: 2, condition: 1, rain: 2, safety: 1}, groups: [
    {target: 'classes', conditions: normal, road_classes: ['primary'], road_ids: []},
    {target: 'roads', conditions: normal, road_ids: ['a:b:0'], road_classes: []},
    {target: 'circle', conditions: {...normal, rain: 1}, area: {lat: 23.77, lon: 90.4, radius_m: 800}, road_ids: [], road_classes: []},
  ]}
  function Studio() {
    const [areas, setAreas] = React.useState([])
    return <ScenarioManager current={current} areas={areas} onAreasChange={setAreas} onSaved={saved} onError={vi.fn()}/>
  }
  render(<Studio/>)
  fireEvent.click(screen.getByText('Custom scenario studio'))
  fireEvent.click(screen.getByText('Edit active'))
  expect(screen.getByLabelText('Condition 3 radius (metres)')).toHaveValue('800')
  fireEvent.click(screen.getByText('Remove condition 2'))
  expect(screen.getByLabelText('Condition 2 radius (metres)')).toHaveValue('800')
  expect(screen.getByLabelText('Condition 2 rain')).toHaveValue('1')
  fireEvent.click(screen.getByText('Update scenario'))
  await waitFor(() => expect(saved).toHaveBeenCalledWith('existing'))
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.groups).toHaveLength(2)
  expect(body.groups[1]).toMatchObject({target: 'circle', area: {radius_m: 800}, conditions: {rain: 1}})
})
