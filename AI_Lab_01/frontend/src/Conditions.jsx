import React from 'react'
export const baseline = {traffic: 0, condition: 0, rain: 0, safety: 0, blocked: false}
export default function Conditions({value, onChange, prefix = 'Road'}) {
  const options = {
    traffic: [['Low', 0], ['Moderate', 0.33], ['High', 0.67], ['Severe', 1]],
    condition: [['Good', 0], ['Fair', 0.5], ['Poor', 1]],
    rain: [['None', 0], ['Low', 0.33], ['Moderate', 0.67], ['Severe', 1]],
  }
  return <div className="condition-grid">{Object.entries(options).map(([key, items]) => <label key={key}>{key === 'rain' ? 'Rain / waterlogging' : key === 'condition' ? 'Road condition' : 'Traffic'}<select aria-label={`${prefix} ${key}`} value={value[key]} onChange={e => onChange({...value, [key]: Number(e.target.value)})}>{!items.some(([, n]) => n === value[key]) && <option value={value[key]}>Custom: {value[key]}</option>}{items.map(([label, n]) => <option key={n} value={n}>{label}</option>)}</select></label>)}<label>Safety penalty {value.safety}<input aria-label={`${prefix} safety`} type="range" min="0" max="1" step="0.1" value={value.safety} onChange={e => onChange({...value, safety: Number(e.target.value)})}/></label><label className="check"><input type="checkbox" checked={value.blocked} onChange={e => onChange({...value, blocked: e.target.checked})}/> Block this direction</label></div>
}
