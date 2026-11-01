// Reuses Lab 1's React-Leaflet layers, route geometry conversion and teal map language.
import React, { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Tooltip,
  useMapEvents,
  useMap,
} from "react-leaflet";
import { colors } from "./api";
const point = (s, node) => {
  const [lon, lat] = s.nodes[node];
  return [lat, lon];
};
const line = (route) => route.geometry.map(([lon, lat]) => [lat, lon]);
function Fit({ nodes }) {
  const map = useMap();
  const coords = Object.values(nodes);
  const west = Math.min(...coords.map((p) => p[0])),
    east = Math.max(...coords.map((p) => p[0])),
    south = Math.min(...coords.map((p) => p[1])),
    north = Math.max(...coords.map((p) => p[1]));
  useEffect(() => {
    map.fitBounds(
      [
        [south, west],
        [north, east],
      ],
      { padding: [35, 35] },
    );
  }, [west, east, south, north, map]);
  return null;
}
function Click({ scenario, onPoint }) {
  useMapEvents({
    click: (e) => {
      let closest;
      let best = Infinity;
      for (const [id, [lon, lat]] of Object.entries(scenario.nodes)) {
        const d = (e.latlng.lat - lat) ** 2 + (e.latlng.lng - lon) ** 2;
        if (d < best) {
          closest = id;
          best = d;
        }
      }
      onPoint(closest);
    },
  });
  return null;
}
export default function MapView({
  scenario,
  result,
  selected,
  onSelect,
  onRoad,
  onPoint,
  tiles = false,
}) {
  const states = Object.fromEntries(
    (result?.incidents || []).map((i) => [i.id, i.status]),
  );
  const routes = (result?.assignments || []).filter(
    (a) => !selected || a.incident === selected,
  );
  return (
    <>
      <MapContainer
        center={[23.785, 90.39]}
        zoom={12}
        className="map"
        scrollWheelZoom
      >
        {tiles && (
          <TileLayer
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />
        )}
        <Fit nodes={scenario.nodes} />
        <Click scenario={scenario} onPoint={onPoint} />
        {scenario.roads.map((road) => (
          <Polyline
            key={road.id}
            positions={[point(scenario, road.u), point(scenario, road.v)]}
            pathOptions={{
              color: road.blocked ? "#d0404e" : "#739c98",
              weight: road.blocked ? 5 : 2,
              opacity: road.blocked ? 0.9 : 0.35,
              dashArray: road.blocked ? "5 5" : undefined,
            }}
            eventHandlers={{
              click: (e) => {
                e.originalEvent?.stopPropagation();
                onRoad(road.id);
              },
            }}
          >
            <Tooltip>
              {road.id} · {road.distance_km.toFixed(2)} km ·{" "}
              {road.blocked
                ? "CLOSED — click to reopen"
                : "click to block directed road"}
            </Tooltip>
          </Polyline>
        ))}
        {Object.entries(scenario.nodes).map(([id]) => (
          <CircleMarker
            key={id}
            center={point(scenario, id)}
            radius={2}
            pathOptions={{ color: "#aac3bc", weight: 0, fillOpacity: 0.6 }}
          >
            <Tooltip>Node {id}</Tooltip>
          </CircleMarker>
        ))}
        {scenario.stations.map((station) => (
          <CircleMarker
            key={station.id}
            center={point(scenario, station.node)}
            radius={11}
            pathOptions={{
              color: "#12363d",
              fillColor: "#12363d",
              fillOpacity: 1,
            }}
          >
            <Tooltip permanent direction="top">
              {station.id}
            </Tooltip>
          </CircleMarker>
        ))}
        {scenario.hospitals.map((h) => (
          <CircleMarker
            key={h.id}
            center={point(scenario, h.node)}
            radius={8}
            pathOptions={{
              color: "#3983bb",
              fillColor: "#fff",
              fillOpacity: 1,
              weight: 3,
            }}
          >
            <Tooltip>
              {h.id} ✚ {h.name} · {h.beds} beds
            </Tooltip>
          </CircleMarker>
        ))}
        {routes.map((a) => (
          <React.Fragment key={a.slot}>
            <Polyline
              className="dispatch-route"
              positions={line(a.response)}
              pathOptions={{
                color: colors[a.role] || "#17383d",
                weight: 5,
                opacity: 0.85,
              }}
            >
              <Tooltip>
                {a.resource} → {a.incident} · {a.eta_minutes.toFixed(1)} min
              </Tooltip>
            </Polyline>
            {a.transport && (
              <Polyline
                className="transport-route"
                positions={line(a.transport)}
                pathOptions={{ color: "#3983bb", weight: 3, dashArray: "5 8" }}
              >
                <Tooltip>
                  Patient transport → {a.hospital} ·{" "}
                  {a.transport_minutes.toFixed(1)} min (after response)
                </Tooltip>
              </Polyline>
            )}
            <CircleMarker
              center={point(scenario, a.response.origin)}
              radius={5}
              pathOptions={{ color: colors[a.role], fillOpacity: 1 }}
            >
              <Tooltip>
                {a.resource} dispatch origin · {a.station}
              </Tooltip>
            </CircleMarker>
          </React.Fragment>
        ))}
        {scenario.incidents.map((i) => (
          <CircleMarker
            key={i.id}
            center={point(scenario, i.node)}
            radius={selected === i.id ? 11 : 7}
            pathOptions={{
              color: selected === i.id ? "#17383d" : "white",
              weight: 2,
              fillColor:
                states[i.id] === "fully_served"
                  ? "#168c79"
                  : states[i.id] === "partially_served"
                    ? "#dc9e39"
                    : states[i.id] === "unserved"
                      ? "#d0404e"
                      : "#dc9e39",
              fillOpacity: 1,
            }}
            eventHandlers={{ click: () => onSelect(i.id) }}
          >
            <Tooltip>
              {i.id} · {i.category} · severity {i.severity} ·{" "}
              {states[i.id] || "pending"}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="map-legend">
        <span>● Center</span>
        <span className="blue">✚ Hospital / transport</span>
        {Object.entries(colors).map(([role, color]) => (
          <span style={{ color }} key={role}>
            ━ {role}
          </span>
        ))}
        <span className="red">┄ Closed road / unserved</span>
      </div>
    </>
  );
}
