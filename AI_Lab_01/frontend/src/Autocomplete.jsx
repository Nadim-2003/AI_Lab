import React, {useEffect, useId, useRef, useState} from 'react'
import {api, send} from './api'

export default function Autocomplete({label, value, onChange, onError, disabled = false}) {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [active, setActive] = useState(0)
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)
  const id = useId()
  const selection = useRef(0)
  useEffect(() => {
    if (disabled || query.trim().length < 2) {setItems([]); setBusy(false); return}
    const controller = new AbortController()
    const timer = setTimeout(() => {
      setBusy(true)
      api(`/places?q=${encodeURIComponent(query)}`, {signal: controller.signal}).then(data => {setItems(data); setActive(0)}).catch(error => {if (error.name !== 'AbortError') onError(error.message)}).finally(() => {if (!controller.signal.aborted) setBusy(false)})
    }, 250)
    return () => {clearTimeout(timer); controller.abort()}
  }, [query, disabled])
  async function choose(place) {
    if (disabled) return
    const version = ++selection.current
    setOpen(false)
    setBusy(true)
    try {
      const snapped = await api('/resolve', send('POST', {lat: place.lat, lon: place.lon}))
      if (version === selection.current) {onChange({...snapped, name: place.name}); setQuery('')}
    } catch (error) {onError(error.message)} finally {if (version === selection.current) setBusy(false)}
  }
  return <div className="autocomplete">
    <label htmlFor={id}>{label}</label>
    {value && <div className="selection"><span><strong>{value.name}</strong><small>Road node {value.node} · snapped {value.distance_m.toFixed(0)} m</small></span><button aria-label={`Clear ${label}`} onClick={() => {selection.current++; onChange(null); setQuery(''); setBusy(false)}}>×</button></div>}
    <input id={id} disabled={disabled} role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={`${id}-list`} aria-activedescendant={open && items.length ? `${id}-${active}` : undefined} value={query} placeholder={`Search ${label.toLowerCase()}…`} onFocus={() => setOpen(true)} onChange={e => {setQuery(e.target.value); setOpen(true)}} onKeyDown={e => {
      if (e.key === 'ArrowDown') {e.preventDefault(); setActive(i => Math.min(items.length - 1, i + 1)); setOpen(true)}
      if (e.key === 'ArrowUp') {e.preventDefault(); setActive(i => Math.max(0, i - 1))}
      if (e.key === 'Escape') setOpen(false)
      if (e.key === 'Enter' && open && items[active]) {e.preventDefault(); choose(items[active])}
    }}/>
    {busy && <small role="status">Searching / matching road…</small>}
    {!disabled && open && query.trim().length >= 2 && <ul id={`${id}-list`} role="listbox" aria-label={`${label} suggestions`} className="suggestions">{items.length ? items.map((p, i) => <li key={p.id} id={`${id}-${i}`} role="option" aria-selected={active === i}><button onClick={() => choose(p)}><strong>{p.name}</strong><small>{p.category} {p.locality && `· ${p.locality}`}</small></button></li>) : <li className="empty">{busy ? 'Loading…' : 'No matching places'}</li>}</ul>}
  </div>
}
