import React, {useState} from 'react'
import Conditions, {baseline} from './Conditions'
import {api, send} from './api'
const defaults = {name: '', description: '', road_classes: [], conditions: baseline, edges: {}, weights: {traffic: 2, condition: 1, rain: 2, safety: 1}}
export default function ScenarioManager({current, road, onSaved, onError}) {
  const [draft, setDraft] = useState(defaults)
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  function load(duplicate) {
    const {id, builtin, ...data} = current
    setDraft({...data, name: duplicate ? `${data.name} copy` : data.name})
    setEditing(duplicate ? null : id)
  }
  async function save(e) {
    e.preventDefault(); setBusy(true)
    try {
      const result = await api(editing ? `/scenarios/${editing}` : '/scenarios', send(editing ? 'PUT' : 'POST', draft))
      await onSaved(result.id); setDraft(defaults); setEditing(null)
    } catch (e) {onError(e.message)} finally {setBusy(false)}
  }
  return <details className="card"><summary>Custom scenario studio</summary><p>Create deterministic simulated conditions. Individual road overrides take precedence.</p><div className="button-row"><button disabled={!current} onClick={() => load(true)}>Duplicate active</button><button disabled={!current || current.builtin} onClick={() => load(false)}>Edit active</button><button className="danger" disabled={!current || current.builtin || busy} onClick={async () => {if (!window.confirm(`Delete ${current.name}?`)) return; setBusy(true); try {await api(`/scenarios/${current.id}`, {method: 'DELETE'}); await onSaved('normal')} catch (e) {onError(e.message)} finally {setBusy(false)}}}>Delete active</button></div>
    <form onSubmit={save}><label>Name<input required maxLength={80} value={draft.name} onChange={e => setDraft({...draft, name: e.target.value})}/></label><label>Description<input maxLength={500} value={draft.description} onChange={e => setDraft({...draft, description: e.target.value})}/></label><label>Road classes (comma separated; blank = all)<input value={draft.road_classes.join(',')} onChange={e => setDraft({...draft, road_classes: e.target.value.split(',').map(s => s.trim()).filter(Boolean)})}/></label><Conditions prefix="Scenario" value={draft.conditions} onChange={conditions => setDraft({...draft, conditions})}/><div className="condition-grid">{Object.keys(draft.weights).map(key => <label key={key}>{key} weight<input type="number" min="0" max="10" step="0.1" value={draft.weights[key]} onChange={e => setDraft({...draft, weights: {...draft.weights, [key]: Number(e.target.value)}})}/></label>)}</div><button type="button" disabled={!road} onClick={() => setDraft({...draft, edges: {...draft.edges, [road.properties.id]: {...draft.conditions}}})}>Add selected directed road with these conditions</button><div className="edge-list">{Object.entries(draft.edges).map(([id, c]) => <div key={id}><span>{id} {c.blocked ? '· closed' : '· open'}</span><button type="button" onClick={() => {const edges = {...draft.edges}; delete edges[id]; setDraft({...draft, edges})}}>Remove</button></div>)}</div><button className="primary" disabled={busy}>{busy ? 'Saving…' : editing ? 'Update scenario' : 'Create scenario'}</button></form>
  </details>
}
