export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {...options, headers: {'Content-Type': 'application/json', ...options.headers}})
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
  return data
}
export const send = (method, value) => ({method, body: JSON.stringify(value)})
export const colors = {'BFS': '#2885ca', 'DFS': '#9a62cb', 'IDS': '#e59023', 'UCS': '#0e9e81', 'A*': '#e04b65'}
export const toLeaflet = geometry => geometry?.coordinates.map(([lon, lat]) => [lat, lon]) || []
