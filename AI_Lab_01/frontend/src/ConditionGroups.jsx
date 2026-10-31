import React from 'react'
import Conditions, {baseline} from './Conditions'

const classes = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'residential', 'service', 'unclassified', 'living_street', 'road']
export default function ConditionGroups({groups, onChange, areas, onAreasChange, onPickArea, onCancelArea, road, ready}) {
  function update(index, changes) {onChange(groups.map((group, i) => i === index ? {...group, ...changes} : group))}
  return <section aria-label="Condition groups">
    <p>Add conditions for circles, selected directed roads, or road classes in the same scenario. All groups use the shared weights below. On overlapping roads, the highest severity for each condition applies; any blocked group closes the road. Road Inspector overrides take priority.</p>
    <button type="button" disabled={groups.length >= 20} onClick={() => {onCancelArea(); onChange([...groups, {target: 'circle', conditions: {...baseline}, road_ids: [], road_classes: []}]); onAreasChange([...areas, null])}}>Add condition</button>
    {groups.map((group, index) => <details className="condition-group" key={index} open>
      <summary>Condition {index + 1} · {group.target === 'circle' ? 'Circle' : group.target === 'roads' ? 'Selected roads' : 'Road classes'}</summary>
      <label>Condition {index + 1} applies to<select value={group.target} onChange={e => {onCancelArea(); update(index, {target: e.target.value, road_ids: [], road_classes: []}); onAreasChange(areas.map((area, i) => i === index ? null : area))}}><option value="circle">Circle on map</option><option value="roads">Selected roads</option><option value="classes">Road classes</option></select></label>
      {group.target === 'circle' && <>
        <button type="button" disabled={!ready} onClick={() => onPickArea(index)}>{areas[index] ? `Move condition ${index + 1} circle` : `Pick condition ${index + 1} circle`}</button>
        <label>Condition {index + 1} radius (metres)<input type="range" min="50" max="20000" step="50" disabled={!areas[index]} value={areas[index]?.radius_m || 500} onChange={e => onAreasChange(areas.map((area, i) => i === index ? {...area, radius_m: Number(e.target.value)} : area))}/></label>
        <p>{areas[index] ? `Radius: ${areas[index].radius_m} m. Drag the center handle to move this circle.` : 'Click the pick button, then click the map.'} Every intersecting road segment is affected along its whole length.</p>
      </>}
      {group.target === 'roads' && <>
        <button type="button" disabled={!road || group.road_ids.includes(road.properties.id)} onClick={() => update(index, {road_ids: [...group.road_ids, road.properties.id]})}>Add selected road to condition {index + 1}</button>
        <p>Click a road on the map, then add it here. Only the selected direction is included.</p>
        {group.road_ids.map(id => <div key={id}>{id} <button type="button" aria-label={`Remove ${id} from condition ${index + 1}`} onClick={() => update(index, {road_ids: group.road_ids.filter(item => item !== id)})}>Remove road</button></div>)}
      </>}
      {group.target === 'classes' && <>
        <label>Condition {index + 1} road classes<select value="" onChange={e => update(index, {road_classes: e.target.value === 'all' ? [] : [...group.road_classes, e.target.value]})}><option value="" disabled>{group.road_classes.length ? 'Add another class…' : 'All road classes'}</option><option value="all">All road classes</option>{[...new Set([...classes, ...group.road_classes])].filter(value => !group.road_classes.includes(value)).map(value => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
        <p>{group.road_classes.length ? 'Applies to these road classes across the loaded network.' : 'Applies to all road classes across the loaded network.'}</p>
        {group.road_classes.map(value => <button type="button" key={value} aria-label={`Remove ${value} from condition ${index + 1}`} onClick={() => update(index, {road_classes: group.road_classes.filter(item => item !== value)})}>{value} ×</button>)}
      </>}
      <Conditions prefix={`Condition ${index + 1}`} value={group.conditions} onChange={conditions => update(index, {conditions})}/>
      <button type="button" className="danger" onClick={() => {onCancelArea(); onChange(groups.filter((_, i) => i !== index)); onAreasChange(areas.filter((_, i) => i !== index))}}>Remove condition {index + 1}</button>
    </details>)}
  </section>
}
