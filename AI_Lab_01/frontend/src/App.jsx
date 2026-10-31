import React, {useEffect, useRef, useState} from 'react'
import {BarChart, Bar, XAxis, YAxis, Tooltip as ChartTooltip, ResponsiveContainer, Cell} from 'recharts'
import Autocomplete from './Autocomplete'
import Conditions, {baseline} from './Conditions'
import MapView from './MapView'
import ScenarioManager from './ScenarioManager'
import {api, send, colors} from './api'

const initialVisibility = Object.fromEntries(Object.keys(colors).map(k => [k, true]))
export default function App() {
  const [metadata, setMetadata] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenario, setScenario] = useState('normal')
  const [algorithm, setAlgorithm] = useState('A*')
  const [start, setStart] = useState(null)
  const [destination, setDestination] = useState(null)
  const [selectionMode, setSelectionMode] = useState('')
  const [run, setRun] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [visible, setVisible] = useState(initialVisibility)
  const [selected, setSelected] = useState('A*')
  const [scenarioAreas, setScenarioAreas] = useState(null)
  const circleToMove = useRef(null)
  const [road, setRoad] = useState(null)
  const [conditions, setConditions] = useState(null)
  const [saving, setSaving] = useState(false)
  const [roadClass, setRoadClass] = useState('')
  const [placeCategory, setPlaceCategory] = useState('')
  const [showPlaces, setShowPlaces] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const [traceNode, setTraceNode] = useState(null)
  const [focusKey, setFocusKey] = useState(0)
  const [maxDepth, setMaxDepth] = useState(100)
  const [comparisons, setComparisons] = useState([])
  const [compareIds, setCompareIds] = useState(['normal', 'traffic'])
  const queryVersion = useRef(0)
  const pointVersion = useRef(0)
  async function refresh() {
    const [stats, list] = await Promise.all([api('/metadata'), api('/scenarios')])
    setMetadata(stats); setScenarios(list)
  }
  useEffect(() => {refresh().catch(e => setError(e.message)); const timer = setInterval(() => api('/metadata').then(setMetadata).catch(() => {}), 15000); return () => clearInterval(timer)}, [])
  useEffect(() => {
    if (!road || !metadata?.ready) return
    let active = true
    api(`/road?${new URLSearchParams({id: road.properties.id, scenario})}`).then(data => {if (active) {setRoad(data); setConditions(data.properties.conditions)}}).catch(e => {if (active) setError(e.message)})
    return () => {active = false}
  }, [scenario, metadata?.revision, metadata?.ready])
  const results = run?.results || []
  const stale = run && (!metadata?.ready || run.scenario !== scenario || run.revision !== metadata?.revision || run.start !== start?.node || run.destination !== destination?.node)
  const activeScenario = scenarios.find(s => s.id === scenario)
  const roadEditsPending = Boolean(road && conditions && JSON.stringify(conditions) !== JSON.stringify(road.properties.conditions))
  const chosen = results.find(r => r.algorithm === selected)
  useEffect(() => {setTraceNode(null)}, [run, selected, stale])
  function selectTraceNode(index) {
    const point = chosen?.trace_points?.[index]
    if (stale || !point) return
    setTraceNode({id: chosen.trace[index], lon: point[0], lat: point[1]})
    setSelectionMode('')
  }
  const overlap = results.filter(r => r.found && chosen?.found && JSON.stringify(r.edges) === JSON.stringify(chosen.edges)).map(r => r.algorithm)
  function changePoint(setter, value) {queryVersion.current++; setter(value)}
  async function selectPoint(latlng) {
    if (!metadata?.ready || !selectionMode) return
    if (selectionMode === 'scenario area') {
      setScenarioAreas(previous => {
        const areas = previous || []
        const index = circleToMove.current
        const area = {conditions: {...baseline}, ...areas[index], lat: latlng.lat, lon: latlng.lng, radius_m: areas[index]?.radius_m || 500}
        return index === null ? (areas.length < 20 ? [...areas, area] : areas) : areas.map((item, i) => i === index ? {...item, ...area} : item)
      })
      setSelectionMode(''); return
    }
    const version = ++pointVersion.current
    const target = selectionMode
    try {
      const point = await api('/resolve', send('POST', {lat: latlng.lat, lon: latlng.lng}))
      if (version !== pointVersion.current) return
      changePoint(target === 'start' ? setStart : setDestination, {...point, name: `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`})
      setSelectionMode(''); setError('')
    } catch (e) {setError(e.message)}
  }
  async function route(all = false, compare = false) {
    if (!metadata?.ready || !start || !destination) return
    const version = ++queryVersion.current
    const query = {start: start.node, destination: destination.node, algorithm: all ? 'all' : algorithm, scenario, max_depth: maxDepth, trace_limit: 5000}
    setBusy(true); setError(''); setNotice('')
    try {
      if (compare) {
        const data = await api('/compare-scenarios', send('POST', {query, scenarios: compareIds}))
        if (version === queryVersion.current) setComparisons(data)
      } else {
        const data = await api('/routes', send('POST', query))
        if (version === queryVersion.current) {
          setRun({...data, start: start.node, destination: destination.node})
          setSelected(data.results.some(r => r.algorithm === algorithm) ? algorithm : data.results[0].algorithm)
          setFocusKey(n => n + 1)
        }
      }
    } catch (e) {setError(e.message)} finally {setBusy(false)}
  }
  async function editRoad(action) {
    setSaving(true); setError('')
    try {
      const suffix = road ? `?${new URLSearchParams({id: road.properties.id})}` : ''
      await api(`/overrides${action === 'all' ? '' : suffix}`, action === 'save' ? send('PUT', conditions) : {method: 'DELETE'})
      await refresh(); setNotice(action === 'save' ? 'Road conditions applied. Run the route again; UCS and A* will use the updated cost.' : 'Overrides reset. Scenario conditions now apply.')
    } catch (e) {setError(e.message)} finally {setSaving(false)}
  }
  function inspectRoad(value) {setRoad(value); setConditions({...value.properties.conditions})}
  return <>
    <header><div className="brand-mark">ঢ</div><div><h1>Dhaka <span>Route Lab</span></h1><p>INTELLIGENT VEHICLE ROUTING · AI SEARCH LABORATORY</p></div><div className={`status ${metadata?.ready ? 'online' : ''}`}>{metadata?.ready ? '● Dataset ready' : '○ Dataset unavailable'}<small>Conditions are simulated</small></div></header>
    <main>
      {error && <div className="banner error" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
      {notice && <div className="banner success" role="status">{notice}<button aria-label="Dismiss notice" onClick={() => setNotice('')}>×</button></div>}
      {metadata && !metadata.ready && <section className="banner warning dataset-help" aria-label="Dataset setup"><strong>Real road data has not been loaded.</strong><p>{metadata.error}</p><p>From AI_Lab_01, download the actual OSM roads and places around Dhaka University once. Internet access is required; this can take several minutes.</p><div><strong>Windows Command Prompt</strong><code>setup_data.bat</code></div><div><strong>macOS / Linux</strong><code>.venv/bin/python scripts/acquire_data.py</code></div><p>After the download completes, stop the backend with Ctrl+C and restart it. Refresh the dataset status below. Panning and searching will not send road or place requests until the dataset is ready.</p><button onClick={async () => {try {await refresh(); setError('')} catch (e) {setError(e.message)}}}>Check dataset status</button><p>The map tiles are separate from the routing dataset. No sample routes or places are substituted.</p></section>}
      {metadata?.ready && metadata.metadata?.places_complete === false && <div className="banner warning" role="status"><strong>Road routing is ready; place coverage is incomplete.</strong><span>{metadata.metadata.completed_place_tiles} of {metadata.metadata.total_place_tiles} place tiles installed, with {metadata.places.toLocaleString()} valid places. Use map clicks if a location is missing from search. To finish downloading places later, run setup_data.bat --replace, then restart the backend.</span></div>}
      <div className="workspace">
        <aside className="controls">
          <section className="card"><div className="eyebrow">01 / PLAN A JOURNEY</div><h2>Where are you heading?</h2><Autocomplete label="Start" disabled={!metadata?.ready || metadata.places === 0} value={start} onChange={p => changePoint(setStart, p)} onError={setError}/><Autocomplete label="Destination" disabled={!metadata?.ready || metadata.places === 0} value={destination} onChange={p => changePoint(setDestination, p)} onError={setError}/><div className="button-row"><button className={selectionMode === 'start' ? 'active' : ''} disabled={!metadata?.ready} onClick={() => setSelectionMode(m => m === 'start' ? '' : 'start')}>Pick start on map</button><button className={selectionMode === 'destination' ? 'active' : ''} disabled={!metadata?.ready} onClick={() => setSelectionMode(m => m === 'destination' ? '' : 'destination')}>Pick destination</button></div></section>
          <section className="card"><div className="eyebrow">02 / SIMULATED CONDITIONS</div><label>Active scenario<select value={scenario} onChange={e => {queryVersion.current++; setScenario(e.target.value)}}>{scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><p>{activeScenario?.description || 'Deterministic simulated penalties on configured road classes.'}</p><div className="scenario-tags">{activeScenario && Object.entries(activeScenario.conditions).filter(([, v]) => v).map(([k, v]) => <span key={k}>{k}: {String(v)}</span>)}</div><label>Search algorithm<select value={algorithm} onChange={e => setAlgorithm(e.target.value)}>{Object.keys(colors).map(name => <option key={name}>{name}</option>)}</select></label><details><summary>Search limits & cost model</summary><label>DFS / IDS maximum depth<input type="number" min="0" max="500" value={maxDepth} onChange={e => setMaxDepth(Number(e.target.value))}/></label><p>Each search: 100,000 expansions, 3 seconds. Trace: at most 5,000 explored nodes. BFS minimizes hops; DFS and IDS are depth limited. UCS and A* optimize generalized cost.</p><code>cost = km × (1 + Σ weight × severity)</code><p>A* uses a geographic lower bound scaled by the minimum traversable cost per endpoint kilometer. Zero heuristic results are also measured. Cost is neither distance nor travel time.</p></details><button className="primary wide" disabled={busy || !start || !destination || !metadata?.ready} onClick={() => route(false)}>{busy ? 'Searching…' : `Run ${algorithm} →`}</button><button className="wide" disabled={busy || !start || !destination || !metadata?.ready} onClick={() => route(true)}>Compare all five algorithms</button></section>
          <ScenarioManager areas={scenarioAreas || []} onAreasChange={setScenarioAreas} onPickArea={(index = null) => {circleToMove.current = index; setSelectionMode('scenario area')}} onCancelArea={() => setSelectionMode('')} ready={Boolean(metadata?.ready)} current={activeScenario} road={road} onError={setError} onSaved={async id => {queryVersion.current++; await refresh(); setScenario(id); setNotice('Scenario saved. Recalculate to apply it.')}}/>
          <details className="card"><summary>Compare scenarios</summary><p>Same source, destination, algorithm and override revision.</p>{scenarios.map(s => <label className="check" key={s.id}><input type="checkbox" checked={compareIds.includes(s.id)} onChange={e => setCompareIds(ids => e.target.checked ? [...ids, s.id].slice(0, 8) : ids.filter(id => id !== s.id))}/>{s.name}</label>)}<button disabled={busy || !metadata?.ready || !start || !destination || !compareIds.length} onClick={() => route(false, true)}>Run scenario comparison</button>{comparisons.length > 0 && <><p>Historical comparison; rerun after changing endpoints or conditions.</p><table><thead><tr><th>Scenario</th><th>Cost / status</th></tr></thead><tbody>{comparisons.map(c => <tr key={c.scenario}><td>{c.scenario_name}</td><td>{c.results.map(r => `${r.algorithm}: ${r.found ? r.cost.toFixed(3) : r.status}`).join(', ')}</td></tr>)}</tbody></table></>}</details>
        </aside>
        <div className="main-column"><section className="card map-card"><div className="section-heading"><div><div className="eyebrow">{metadata?.metadata?.study_area?.name || (metadata?.ready ? 'DHAKA, BANGLADESH' : 'DHAKA UNIVERSITY & NEARBY')}</div><h2>Explore the local road network</h2></div><button disabled={!chosen?.geometry} onClick={() => setFocusKey(n => n + 1)}>Fit selected route</button></div><div className="map-filters"><label>Road class<select value={roadClass} onChange={e => setRoadClass(e.target.value)}><option value="">All roads</option>{['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'service', 'unclassified'].map(v => <option key={v}>{v}</option>)}</select></label><label className="check"><input type="checkbox" checked={showPlaces} onChange={e => setShowPlaces(e.target.checked)}/>Places at zoom 13+ (up to 100)</label><label>Place category<select value={placeCategory} onChange={e => setPlaceCategory(e.target.value)}><option value="">All categories</option>{Object.keys(metadata?.categories || {}).map(c => <option key={c}>{c}</option>)}</select></label></div><MapView onAreaMove={scenarioAreas && metadata?.ready ? (index, area) => setScenarioAreas(areas => areas.map((item, i) => i === index ? {...item, ...area} : item)) : undefined} scenarioAreas={scenarioAreas ?? (activeScenario?.scope === 'groups' ? activeScenario.groups.map(group => group.target === 'circle' ? group.area : null) : activeScenario?.scope === 'circle' ? (activeScenario.areas?.length ? activeScenario.areas : activeScenario.area ? [activeScenario.area] : []) : [])} studyBounds={metadata?.metadata?.study_area?.bbox} ready={Boolean(metadata?.ready)} scenario={scenario} revision={metadata?.revision} results={stale ? [] : results} visible={visible} selected={selected} start={start} destination={destination} selectionMode={selectionMode} onPoint={selectPoint} onRoad={inspectRoad} roadClass={roadClass} placeCategory={placeCategory} showPlaces={showPlaces} showTrace={showTrace} traceNode={stale ? null : traceNode} onTraceNode={selectTraceNode} focusKey={focusKey} onError={setError}/><div className="legend" aria-label="Route visibility">{Object.entries(colors).map(([name, color]) => <label key={name} style={{'--route-color': color}}><input type="checkbox" checked={visible[name]} onChange={e => setVisible({...visible, [name]: e.target.checked})}/><span className="route-swatch"/>{name}</label>)}</div><p className="map-footnote">Exact selected OSM edges · Dashed layers distinguish overlaps; select a route to bring it to the front. Roads are directed: u → v.</p></section>
          <section className="card"><div className="section-heading"><div><div className="eyebrow">03 / COMPARE THE SEARCH</div><h2>Routes & performance</h2></div>{run && <small>{run.scenario_name} · snapshot {run.snapshot}</small>}</div>{stale && <div className="banner warning" role="status">Results are stale. Endpoints or conditions changed; recalculate. Historical routes are hidden from the map.</div>}{!run ? <div className="empty-state"><span>↗</span><h3>Your next route starts here</h3><p>Select two locations and run a search to compare actual routes and measured performance.</p></div> : <><div className="table-scroll"><table><thead><tr><th>Algorithm</th><th>Status</th><th>Distance km</th><th>Cost</th><th>Nodes</th><th>Expanded</th><th>Generated</th><th>Search ms</th></tr></thead><tbody>{results.map(r => <tr className={selected === r.algorithm ? 'selected-row' : ''} key={r.algorithm}><td><button onClick={() => {setSelected(r.algorithm); setFocusKey(n => n + 1)}} style={{color: colors[r.algorithm]}}>{r.algorithm}</button></td><td>{r.status}</td><td>{r.distance_km?.toFixed(3) ?? '—'}</td><td>{r.cost?.toFixed(3) ?? '—'}</td><td>{r.nodes.length}</td><td>{r.expanded}</td><td>{r.generated}</td><td>{r.execution_ms.toFixed(2)}</td></tr>)}</tbody></table></div>{overlap.length > 1 && <p>Identical selected road sequence: {overlap.join(', ')}.</p>}<div className="chart" aria-label="Expanded node comparison"><ResponsiveContainer width="100%" height={180}><BarChart data={results}><XAxis dataKey="algorithm"/><YAxis/><ChartTooltip/><Bar dataKey="expanded" name="Expanded nodes">{results.map(r => <Cell key={r.algorithm} fill={colors[r.algorithm]}/>)}</Bar></BarChart></ResponsiveContainer></div>{chosen?.zero_heuristic && <p>A* geographic bound: {run.heuristic_cost_per_km.toFixed(5)} cost/km. Zero heuristic: {chosen.zero_heuristic.expanded} expanded, {chosen.zero_heuristic.execution_ms.toFixed(2)} ms, cost {chosen.zero_heuristic.cost?.toFixed(3) ?? chosen.zero_heuristic.status}.</p>}</>}</section>
          <section className="card dataset"><div><div className="eyebrow">SOURCE & COVERAGE</div><h2>Real roads. Transparent simulations.</h2><p>OpenStreetMap contributors · ODbL 1.0. Original road attributes remain unchanged. No real-time traffic, weather or safety feed is connected.</p></div><div className="stat-grid">{[['Road nodes', metadata?.nodes], ['Directed edges', metadata?.edges], ['Unique places', metadata?.places]].map(([label, value]) => <div key={label}><strong>{value?.toLocaleString() ?? '—'}</strong><span>{label}</span></div>)}</div>{metadata?.metadata.retrieved_at && <small>Retrieved {metadata.metadata.retrieved_at}. Study area: {metadata.metadata.study_area?.name || 'explicit configured rectangle'}, not an administrative boundary.</small>}<details><summary>Place categories and data quality</summary><pre>{JSON.stringify({categories: metadata?.categories, quality: metadata?.metadata.quality_report}, null, 2)}</pre></details></section>
        </div>
        <aside className="inspector"><details className="card" open><summary>Road Inspector</summary><h2>{road?.properties.name || (road ? 'Unnamed road' : 'Select a road')}</h2>{!road ? <p>Click a visible road segment to inspect its original attributes and edit simulated conditions.</p> : <><dl><dt>Directed edge</dt><dd>{road.properties.u} → {road.properties.v} / {road.properties.key}</dd><dt>OSM ID</dt><dd>{String(road.properties.osmid ?? 'Unavailable')}</dd><dt>Road class</dt><dd>{String(road.properties.highway ?? 'Unavailable')}</dd><dt>Length</dt><dd>{Number(road.properties.length_m).toFixed(1)} m</dd><dt>One way</dt><dd>{String(road.properties.oneway ?? 'Unavailable')}</dd><dt>Active cost</dt><dd>{road.properties.cost?.toFixed(4) ?? 'Blocked'}</dd></dl><h3>Simulated conditions</h3><Conditions value={conditions} onChange={setConditions}/>{roadEditsPending && <div className="banner warning" role="status">These changes are not applied yet. Use the button below.</div>}<p>Applies only to this directed edge. The reverse direction is unchanged. After applying it, run the route again. UCS and A* respond to cost; every algorithm avoids a blocked road.</p><button disabled={saving || !roadEditsPending} className="primary wide" onClick={() => editRoad('save')}>{saving ? 'Applying…' : 'Apply conditions to this road'}</button><div className="button-row"><button disabled={saving || !roadEditsPending} onClick={() => setConditions({...road.properties.conditions})}>Cancel edits</button><button disabled={saving} onClick={() => editRoad('reset')}>Reset road</button></div></>}<button className="danger wide" disabled={saving || !metadata?.ready} onClick={() => {if (window.confirm('Reset all saved road overrides? Custom scenarios remain saved.')) editRoad('all')}}>Reset all overrides</button><button className="wide" onClick={() => {queryVersion.current++; pointVersion.current++; setScenario('normal'); setStart(null); setDestination(null); setRun(null); setComparisons([]); setRoad(null); setSelectionMode(''); setError(''); setNotice('Journey reset. Saved overrides remain; use Reset all overrides to restore baseline conditions.')}}>Reset journey</button></details>{run && <details className="card search-trace" open><summary>Bounded search trace</summary><label className="check"><input type="checkbox" checked={showTrace} onChange={e => setShowTrace(e.target.checked)}/>Show explored nodes for selected algorithm</label><p>Exploration is separate from the final route. Captured {chosen?.trace.length || 0} nodes{chosen?.trace_truncated ? ' (bounded / truncated)' : ''}.</p><p>Click a node ID to highlight its map location.</p>{traceNode && !stale && <p role="status">Node {traceNode.id}: latitude {traceNode.lat.toFixed(6)}, longitude {traceNode.lon.toFixed(6)}</p>}<div className="trace">{chosen?.trace.map((id, index) => <React.Fragment key={index}>{index > 0 && ' → '}<button className="trace-node" disabled={Boolean(stale) || !chosen.trace_points?.[index]} aria-pressed={!stale && traceNode?.id === id} onClick={() => selectTraceNode(index)}>{id}</button></React.Fragment>)}</div></details>}</aside>
      </div>
    </main><footer>Dhaka Route Lab <span>Five search algorithms. One directed road network.</span></footer>
  </>
}
