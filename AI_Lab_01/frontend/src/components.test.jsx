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
