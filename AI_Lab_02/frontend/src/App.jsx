import React, { useEffect, useState } from "react";
import MapView from "./MapView";
import { RuntimeChart, ExperimentChart } from "./Charts";
import {
  api,
  algorithms,
  colors,
  presets,
  download,
  labelOptions,
} from "./api";

const initial = {
  count: 10,
  seed: 42,
  deadline: 60,
  supply: 1.05,
  ambulance_factor: 1,
  rescue_factor: 1,
  fire_busy_fraction: 0,
  hospital_factor: 1.1,
  budget_factor: 1.3,
  block_fraction: 0.04,
  demo: "custom",
  severity_deadlines: false,
};
const defaultOptions = {
  algorithm: "backtracking",
  mrv: true,
  degree: true,
  lcv: false,
  severity_order: true,
  mac: false,
  max_steps: 10000,
  timeout: 2,
  seed: 42,
  restarts: 2,
};
const fmt = (n) => (n == null ? "N/A" : Number.isInteger(n) ? n : n.toFixed(2));
const display = (s) => s.replaceAll("_", " ");
function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max = 100000,
  step = 1,
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}
function Metrics({ result }) {
  return (
    <div className="stats">
      {[
        ["Fully served", result.summary.fully_served],
        ["Partly served", result.summary.partially_served],
        ["Unserved", result.summary.unserved],
        ["Units dispatched", result.summary.allocated_units],
        ["Solver time", `${fmt(result.metrics.runtime_ms)} ms`],
        ["Dispatch cost", `৳ ${fmt(result.validation.total_cost)}`],
      ].map(([label, value]) => (
        <div key={label}>
          <strong>{value}</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}
function ComparisonTable({ results }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {[
              "Method",
              "Status",
              "Full / partial / none",
              "Units",
              "Steps",
              "Attempts",
              "Checks",
              "Backtracks",
              "Backjumps",
              "Skipped levels",
              "Pruned",
              "Runtime ms",
              "Deadline / budget / all violations",
            ].map((s) => (
              <th key={s}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((r, index) => (
            <tr key={index}>
              <td>{r.label || labelOptions(r.options)}</td>
              <td>{r.status}</td>
              <td>
                {r.summary.fully_served} / {r.summary.partially_served} /{" "}
                {r.summary.unserved}
              </td>
              <td>{r.summary.allocated_units}</td>
              {[
                "search_steps",
                "assignments_attempted",
                "constraint_checks",
                "backtracks",
                "backjumps",
                "skipped_levels",
                "pruned_values",
                "runtime_ms",
              ].map((k) => (
                <td key={k}>{fmt(r.metrics[k])}</td>
              ))}
              <td>
                {r.validation.deadline_violations} /{" "}
                {r.validation.budget_violations} /{" "}
                {r.validation.violation_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export default function App() {
  const [config, setConfig] = useState(initial),
    [options, setOptions] = useState(defaultOptions),
    [scenario, setScenario] = useState(null),
    [result, setResult] = useState(null),
    [comparisons, setComparisons] = useState([]),
    [experiment, setExperiment] = useState(null),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(""),
    [tab, setTab] = useState("Incidents"),
    [tiles, setTiles] = useState(false),
    [edit, setEdit] = useState(""),
    [place, setPlace] = useState(false),
    [category, setCategory] = useState("medical"),
    [experimentKind, setExperimentKind] = useState("deadline"),
    [chartMetric, setChartMetric] = useState("runtime_ms"),
    [methods, setMethods] = useState([0, 3, 4, 5, 6]),
    [repeats, setRepeats] = useState(1);
  async function perform(label, fn) {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  const installScenario = (s) => {
    setScenario(s);
    setResult(null);
    setComparisons([]);
    setExperiment(null);
    setSelected("");
    setEdit(JSON.stringify(s, null, 2));
  };
  useEffect(() => {
    perform("Preparing scenario", async () =>
      installScenario(await api("/scenarios", initial)),
    );
  }, []);
  const patchConfig = (key, value) =>
    setConfig((c) => ({ ...c, [key]: value }));
  const patchOptions = (key, value) =>
    setOptions((o) => ({ ...o, [key]: value }));
  const changeScenario = (fn) => {
    const s = structuredClone(scenario);
    fn(s);
    installScenario(s);
    setSelected(selected);
  };
  const gen = () =>
    perform("Generating scenario", async () => {
      installScenario(await api("/scenarios", config));
      if (config.demo === "backjumping")
        setOptions((o) => ({
          ...o,
          mrv: false,
          degree: false,
          lcv: false,
          severity_order: false,
          algorithm: "backjumping",
        }));
    });
  const run = () =>
    perform("Solving CSP", async () => {
      const r = await api("/solve", { scenario, options });
      setResult(r);
      setSelected("");
    });
  const compare = () =>
    perform("Comparing identical scenario", async () => {
      const os = methods.map((i) => {
        const { label, ...preset } = presets[i];
        return { ...options, ...preset };
      });
      const data = await api("/compare", { scenario, options: os });
      setComparisons(
        data.results.map((r, i) => ({
          ...r,
          label: presets[methods[i]].label,
        })),
      );
    });
  const runExperiment = () =>
    perform(
      "Running bounded experiment — this can take a few minutes",
      async () => {
        const os = methods.map((i) => {
          const { label, ...preset } = presets[i];
          return {
            ...options,
            ...preset,
            timeout: Math.min(2, options.timeout),
            max_steps: Math.min(10000, options.max_steps),
          };
        });
        const data = await api("/experiments", {
          kind: experimentKind,
          generation: config,
          options: os,
          repeats,
        });
        setExperiment({
          ...data,
          rows: data.rows.map((r) => ({
            ...r,
            method: labelOptions(r.options),
          })),
        });
      },
    );
  const onRoad = (id) => {
    if (!busy)
      changeScenario((s) => {
        const road = s.roads.find((r) => r.id === id);
        road.blocked = !road.blocked;
      });
  };
  const onPoint = (node) => {
    if (place && !busy) {
      changeScenario((s) => {
        let n = s.incidents.length + 1;
        while (s.incidents.some((i) => i.id === `I${n}`)) n++;
        const ambulance = {
          role: "ambulance",
          quantity: 1,
          capacity: 1,
          capabilities: ["medical"],
          patients: 1,
          hospital_capability: "emergency",
        };
        const rescue = {
          role: "rescue",
          quantity: 1,
          capacity: 4,
          capabilities: ["rescue"],
          patients: 0,
          hospital_capability: "emergency",
        };
        const fire = {
          role: "fire",
          quantity: 1,
          capacity: 4,
          capabilities: ["firefighting"],
          patients: 0,
          hospital_capability: "emergency",
        };
        s.incidents.push({
          id: `I${n}`,
          category,
          node,
          severity: 3,
          requested_at: 0,
          deadline: config.deadline,
          service_minutes: 15,
          status: "pending",
          requirements:
            category === "medical"
              ? [ambulance]
              : category === "fire"
                ? [fire, ambulance]
                : category === "accident"
                  ? [ambulance, rescue]
                  : [rescue],
        });
      });
      setPlace(false);
    }
  };
  const selectedIncident = scenario?.incidents.find((i) => i.id === selected);
  const selectedState = result?.incidents.find((i) => i.id === selected);
  return (
    <>
      <header>
        <div className="brand">✚</div>
        <div>
          <h1>
            Dhaka <span>Emergency Control</span>
          </h1>
          <p>AI LAB 02 · CONSTRAINT SATISFACTION · RESPONSE COORDINATION</p>
        </div>
        <div className="header-status">
          SIMULATION ENVIRONMENT<small>FastAPI · React · Leaflet</small>
        </div>
      </header>
      <main>
        <div className="notice">
          <strong>Academic simulation.</strong> Roads, dispatch centers,
          hospitals, capacities, costs and traffic are simulated. Feasible
          allocations are independently checked; no global optimality is
          claimed. Lab 1 remains a separate application.
        </div>
        {error && (
          <div role="alert" className="error">
            {error}
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}
        {busy && (
          <div role="status" className="progress">
            ◌ {busy}… Inputs are locked until the request completes.
          </div>
        )}
        <div className="workspace">
          <aside>
            <fieldset disabled={!!busy}>
              <section className="card">
                <div className="eyebrow">01 / SCENARIO</div>
                <h2>Dispatch conditions</h2>
                <label>
                  Demonstration
                  <select
                    aria-label="Demonstration"
                    value={config.demo}
                    onChange={(e) => patchConfig("demo", e.target.value)}
                  >
                    {[
                      ["custom", "Custom workload"],
                      ["medical", "1 · Single medical"],
                      ["fire", "2 · Fire + medical support"],
                      ["competition", "3 · Simultaneous competition"],
                      ["blocked", "4 · Blocked road detour"],
                      ["insufficient", "5 · Insufficient resources"],
                      ["backjumping", "CBJ conflict witness"],
                    ].map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Workload scale
                  <select
                    aria-label="Workload scale"
                    value={config.count}
                    onChange={(e) => patchConfig("count", +e.target.value)}
                  >
                    {[10, 20, 30, 50, 100, 150, 250, 300].map((n) => (
                      <option key={n} value={n}>
                        {n} requests ·{" "}
                        {n <= 50 ? "small" : n <= 150 ? "medium" : "large"}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="two">
                  <NumberField
                    label="Random seed"
                    value={config.seed}
                    onChange={(v) => patchConfig("seed", v)}
                    max={1000000}
                  />
                  <label>
                    Deadline (minutes)
                    <select
                      aria-label="Deadline (minutes)"
                      value={config.deadline}
                      onChange={(e) => patchConfig("deadline", +e.target.value)}
                    >
                      {[30, 60, 120].map((n) => (
                        <option key={n}>{n}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={config.severity_deadlines}
                    onChange={(e) =>
                      patchConfig("severity_deadlines", e.target.checked)
                    }
                  />{" "}
                  Shorten deadlines by severity
                </label>
                <details>
                  <summary>Resource, budget & road pressure</summary>
                  <div className="two">
                    {[
                      ["supply", "Supply / demand", 0, 2],
                      ["ambulance_factor", "Ambulance multiplier", 0, 2],
                      ["rescue_factor", "Rescue multiplier", 0, 2],
                      ["fire_busy_fraction", "Fire busy fraction", 0, 1],
                      ["hospital_factor", "Beds / patients", 0, 2],
                      ["budget_factor", "Budget multiplier", 0, 3],
                      ["block_fraction", "Blocked road fraction", 0, 0.8],
                    ].map(([key, label, min, max]) => (
                      <NumberField
                        key={key}
                        label={label}
                        value={config[key]}
                        min={min}
                        max={max}
                        step={0.05}
                        onChange={(v) => patchConfig(key, v)}
                      />
                    ))}
                  </div>
                  <p>
                    Generation replaces the current scenario. Supply scales with
                    requested resource slots. For controlled pressure tests use
                    the experiment panel.
                  </p>
                </details>
                <button className="wide" onClick={gen}>
                  Generate scenario
                </button>
              </section>
              <section className="card">
                <div className="eyebrow">02 / SEARCH</div>
                <h2>CSP solver</h2>
                <label>
                  Algorithm
                  <select
                    aria-label="Algorithm"
                    value={options.algorithm}
                    onChange={(e) => patchOptions("algorithm", e.target.value)}
                  >
                    {algorithms.map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
                {options.algorithm !== "local_search" && (
                  <>
                    <div className="two">
                      {[
                        ["mrv", "MRV"],
                        ["degree", "Degree tie-break"],
                        ["lcv", "LCV"],
                        ["severity_order", "Severity / deadline"],
                      ].map(([key, label]) => (
                        <label className="check" key={key}>
                          <input
                            type="checkbox"
                            checked={options[key]}
                            onChange={(e) =>
                              patchOptions(key, e.target.checked)
                            }
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                    {options.algorithm === "arc_consistency" && (
                      <label className="check">
                        <input
                          type="checkbox"
                          checked={options.mac}
                          onChange={(e) =>
                            patchOptions("mac", e.target.checked)
                          }
                        />{" "}
                        Maintain AC during search (MAC)
                      </label>
                    )}
                  </>
                )}
                <div className="two">
                  <NumberField
                    label="Step limit"
                    value={options.max_steps}
                    min={1}
                    max={200000}
                    onChange={(v) => patchOptions("max_steps", v)}
                  />
                  <NumberField
                    label="Time limit (s)"
                    value={options.timeout}
                    min={0.01}
                    max={15}
                    step={0.1}
                    onChange={(v) => patchOptions("timeout", v)}
                  />
                </div>
                {options.algorithm === "local_search" && (
                  <div className="two">
                    <NumberField
                      label="Local-search seed"
                      value={options.seed}
                      onChange={(v) => patchOptions("seed", v)}
                    />
                    <NumberField
                      label="Restarts"
                      value={options.restarts}
                      max={10}
                      onChange={(v) => patchOptions("restarts", v)}
                    />
                  </div>
                )}
                <button
                  className="primary wide"
                  disabled={!scenario}
                  onClick={run}
                >
                  Allocate emergency resources →
                </button>
                <p>
                  Limits return an honest partial result. A feasible subset is
                  neither a maximum allocation nor a proof of optimality.
                </p>
              </section>
            </fieldset>
            <section className="card">
              <h3>Formal model</h3>
              <p>
                <strong>X</strong> One variable per resource slot.
                <br />
                <strong>D</strong> Compatible unit + reachable hospital when
                needed.
                <br />
                <strong>C</strong> Availability, exclusivity, deadlines, roads,
                capacities, budget and hospital beds.
              </p>
              <p>
                Snapshot model: a unit is used at most once per solve. Response
                and patient-transport times are separate. Severity is a
                preference, never permission to violate a hard constraint.
              </p>
            </section>
          </aside>
          <div className="main-column">
            {scenario && (
              <>
                <section className="card map-card">
                  <div className="section-heading">
                    <div>
                      <div className="eyebrow">GEOGRAPHIC DISPATCH VIEW</div>
                      <h2>
                        {selected
                          ? `${selected} · response routes`
                          : "Dhaka response network"}
                      </h2>
                    </div>
                    <span className="tag">
                      {scenario.incidents.length} requests ·{" "}
                      {scenario.resources.length} units
                    </span>
                  </div>
                  <div className="map-toolbar">
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={tiles}
                        onChange={(e) => setTiles(e.target.checked)}
                      />{" "}
                      Optional OSM base map
                    </label>
                    <button onClick={() => setSelected("")}>
                      Show all routes
                    </button>
                    <label>
                      New incident type
                      <select
                        aria-label="New incident type"
                        value={category}
                        disabled={!!busy}
                        onChange={(e) => setCategory(e.target.value)}
                      >
                        {["medical", "fire", "accident", "flood"].map((c) => (
                          <option key={c}>{c}</option>
                        ))}
                      </select>
                    </label>
                    <button
                      disabled={!!busy || scenario.incidents.length >= 300}
                      className={place ? "active" : ""}
                      onClick={() => setPlace(!place)}
                    >
                      {place ? "Click a network node…" : "Add incident on map"}
                    </button>
                  </div>
                  <MapView
                    scenario={scenario}
                    result={result}
                    selected={selected}
                    onSelect={setSelected}
                    onRoad={onRoad}
                    onPoint={onPoint}
                    tiles={tiles}
                  />
                  <p className="footnote">
                    Click an incident to inspect routes; click a road to change
                    its directed accessibility. Any scenario edit clears stale
                    allocations. Default map works without Internet.
                  </p>
                </section>
                {result && (
                  <section className="card">
                    <div className="section-heading">
                      <h2>Allocation results</h2>
                      <span
                        className={`tag ${result.status === "feasible" ? "good" : "warn"}`}
                      >
                        {display(result.status)}
                      </span>
                    </div>
                    <Metrics result={result} />
                    <div className="validation">
                      ✓ Returned assignments:{" "}
                      {result.validation.valid
                        ? "validated against hard constraints"
                        : "INVALID"}{" "}
                      · {result.validation.violation_count} violations ·{" "}
                      {result.summary.allocated_units} /{" "}
                      {result.summary.required_slots} slots
                    </div>
                    {result.status !== "feasible" && (
                      <p>
                        Full allocation{" "}
                        {result.status === "infeasible"
                          ? "is infeasible under these constraints"
                          : "was not established within the search limit"}
                        . Fully served, partly served and unserved incidents are
                        counted separately. Partial coverage is not proven
                        maximum.
                      </p>
                    )}
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Slot / incident</th>
                            <th>Resource / origin</th>
                            <th>Response ETA</th>
                            <th>Hospital / transport</th>
                            <th>Release at</th>
                            <th>Cost BDT</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.assignments.map((a) => (
                            <tr key={a.slot}>
                              <td>
                                <button onClick={() => setSelected(a.incident)}>
                                  {a.slot}
                                </button>
                              </td>
                              <td style={{ color: colors[a.role] }}>
                                {a.resource} · {a.station}
                              </td>
                              <td>{fmt(a.eta_minutes)} min</td>
                              <td>
                                {a.hospital || "—"} · {fmt(a.transport_minutes)}{" "}
                                min
                              </td>
                              <td>{fmt(a.release_at)} min</td>
                              <td>{fmt(a.cost)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <details>
                      <summary>
                        Search metrics, constraint failures & trace
                      </summary>
                      <div className="metric-grid">
                        {Object.entries(result.metrics).map(([key, value]) => (
                          <div key={key}>
                            <span>{display(key)}</span>
                            <strong>{fmt(value)}</strong>
                          </div>
                        ))}
                      </div>
                      <h3>Candidate exclusions before search</h3>
                      <pre>
                        {JSON.stringify(result.domain_rejections, null, 2)}
                      </pre>
                      <h3>Rejected search choices</h3>
                      <pre>
                        {JSON.stringify(result.constraint_failures, null, 2)}
                      </pre>
                      <h3>Local-search unresolved raw assignment</h3>
                      <pre>
                        {JSON.stringify(result.local_unresolved, null, 2)}
                      </pre>
                      <h3>Bounded trace (first 150 events)</h3>
                      <pre>{JSON.stringify(result.trace, null, 2)}</pre>
                      <p>
                        Constraint failure counts describe attempted choices,
                        not violations in returned allocations. N/A metrics do
                        not apply to that method. Domain/routing preparation:{" "}
                        {fmt(result.preparation_ms)} ms; excluded from solver
                        time.
                      </p>
                    </details>
                    <button
                      onClick={() =>
                        download("allocation.json", { scenario, result })
                      }
                    >
                      Export scenario & allocation
                    </button>
                  </section>
                )}
                <section className="card">
                  <nav className="tabs" aria-label="Control center data">
                    {[
                      "Incidents",
                      "Resources",
                      "Hospitals",
                      "Scenario JSON",
                    ].map((name) => (
                      <button
                        className={tab === name ? "active" : ""}
                        key={name}
                        onClick={() => setTab(name)}
                      >
                        {name}
                      </button>
                    ))}
                  </nav>
                  {tab === "Incidents" && (
                    <>
                      <div className="table-scroll inventory">
                        <table>
                          <thead>
                            <tr>
                              <th>Incident</th>
                              <th>Category / node</th>
                              <th>Severity</th>
                              <th>Deadline</th>
                              <th>Requirements</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {scenario.incidents.map((i) => {
                              const state = result?.incidents.find(
                                (r) => r.id === i.id,
                              );
                              return (
                                <tr
                                  className={
                                    selected === i.id ? "selected" : ""
                                  }
                                  key={i.id}
                                >
                                  <td>
                                    <button onClick={() => setSelected(i.id)}>
                                      {i.id}
                                    </button>
                                  </td>
                                  <td>
                                    {i.category} · {i.node}
                                  </td>
                                  <td>{i.severity}</td>
                                  <td>{i.deadline} min</td>
                                  <td>
                                    {i.requirements
                                      .map((q) => `${q.quantity} ${q.role}`)
                                      .join(" + ")}
                                  </td>
                                  <td>{display(state?.status || "pending")}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      {selectedIncident && (
                        <div className="inspector">
                          <h3>Inspect {selectedIncident.id}</h3>
                          <fieldset disabled={!!busy}>
                            <div className="three">
                              <NumberField
                                label="Incident severity"
                                value={selectedIncident.severity}
                                min={1}
                                max={5}
                                onChange={(v) =>
                                  changeScenario((s) => {
                                    s.incidents.find(
                                      (i) => i.id === selected,
                                    ).severity = v;
                                  })
                                }
                              />
                              <NumberField
                                label="Incident deadline"
                                value={selectedIncident.deadline}
                                min={1}
                                max={240}
                                onChange={(v) =>
                                  changeScenario((s) => {
                                    s.incidents.find(
                                      (i) => i.id === selected,
                                    ).deadline = v;
                                  })
                                }
                              />
                              <label>
                                Incident node
                                <select
                                  aria-label="Incident node"
                                  value={selectedIncident.node}
                                  onChange={(e) =>
                                    changeScenario((s) => {
                                      s.incidents.find(
                                        (i) => i.id === selected,
                                      ).node = e.target.value;
                                    })
                                  }
                                >
                                  {Object.keys(scenario.nodes).map((n) => (
                                    <option key={n}>{n}</option>
                                  ))}
                                </select>
                              </label>
                            </div>
                          </fieldset>
                          {selectedState && (
                            <>
                              <strong>{display(selectedState.status)}</strong>
                              <pre>
                                {JSON.stringify(selectedState.unmet, null, 2)}
                              </pre>
                            </>
                          )}
                        </div>
                      )}
                    </>
                  )}
                  {tab === "Resources" && (
                    <>
                      <p>
                        Each row is a physical unit. Capacity means patients for
                        ambulances and personnel/equipment units for
                        fire/rescue. Use Scenario JSON to configure
                        capabilities, costs, release times and additional units.
                      </p>
                      <div className="table-scroll inventory">
                        <table>
                          <thead>
                            <tr>
                              <th>Unit / type</th>
                              <th>Home / current</th>
                              <th>Available</th>
                              <th>Capacity</th>
                              <th>Capabilities</th>
                              <th>Dispatch / per km BDT</th>
                              <th>Assigned to</th>
                            </tr>
                          </thead>
                          <tbody>
                            {scenario.resources.map((r) => (
                              <tr key={r.id}>
                                <td style={{ color: colors[r.role] }}>
                                  {r.id} · {r.role}
                                </td>
                                <td>
                                  {r.home_node} / {r.node}
                                </td>
                                <td>
                                  <input
                                    aria-label={`${r.id} available`}
                                    type="checkbox"
                                    disabled={!!busy}
                                    checked={r.available}
                                    onChange={(e) =>
                                      changeScenario((s) => {
                                        s.resources.find(
                                          (x) => x.id === r.id,
                                        ).available = e.target.checked;
                                      })
                                    }
                                  />
                                </td>
                                <td>{r.capacity}</td>
                                <td>{r.capabilities.join(", ")}</td>
                                <td>
                                  {r.dispatch_cost} / {r.cost_per_km}
                                </td>
                                <td>
                                  {result?.assignments.find(
                                    (a) => a.resource === r.id,
                                  )?.incident || "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                  {tab === "Hospitals" && (
                    <>
                      <p>
                        Compatible, reachable hospitals reserve beds
                        cumulatively. No discharge or bed reuse is assumed
                        during this snapshot.
                      </p>
                      <div className="hospital-grid">
                        {scenario.hospitals.map((h) => (
                          <div key={h.id}>
                            <h3>
                              {h.id} · {h.name}
                            </h3>
                            <p>
                              Node {h.node} · {h.capabilities.join(", ")}
                            </p>
                            <NumberField
                              label={`${h.id} available beds`}
                              value={h.beds}
                              max={100000}
                              onChange={(v) => {
                                if (!busy)
                                  changeScenario((s) => {
                                    s.hospitals.find(
                                      (x) => x.id === h.id,
                                    ).beds = v;
                                  });
                              }}
                            />
                            <p>
                              Reserved:{" "}
                              {result?.assignments
                                .filter((a) => a.hospital === h.id)
                                .reduce((sum, a) => sum + a.patients, 0) || 0}
                            </p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {tab === "Scenario JSON" && (
                    <>
                      <p>
                        Edit demands, incident timestamps, service durations,
                        stations, current/home nodes, capabilities, capacities,
                        budgets, traffic, directed roads and hospitals. Apply
                        validates the complete scenario. No source files are
                        changed.
                      </p>
                      <textarea
                        aria-label="Scenario JSON editor"
                        value={edit}
                        disabled={!!busy}
                        onChange={(e) => setEdit(e.target.value)}
                        spellCheck={false}
                      />
                      <div className="button-row">
                        <button
                          disabled={!!busy}
                          onClick={() =>
                            perform("Validating scenario", async () => {
                              const s = JSON.parse(edit);
                              installScenario(
                                await api("/validate-scenario", s),
                              );
                            })
                          }
                        >
                          Validate & apply JSON
                        </button>
                        <button
                          onClick={() => download("scenario.json", scenario)}
                        >
                          Export current scenario
                        </button>
                        <NumberField
                          label="Current dispatch budget BDT"
                          value={scenario.budget}
                          onChange={(v) => {
                            if (!busy)
                              changeScenario((s) => {
                                s.budget = v;
                              });
                          }}
                        />
                      </div>
                    </>
                  )}
                </section>
                <section className="card">
                  <div className="eyebrow">03 / EVALUATION</div>
                  <h2>Compare algorithms & heuristics</h2>
                  <p>
                    Every selected method receives exactly the current scenario.
                    Select presets to separate heuristic effects from solver
                    differences. Severity remains enabled except Plain BT. Local
                    search uses its seed and bounded restarts.
                  </p>
                  <fieldset disabled={!!busy}>
                    <div className="method-list">
                      {presets.map((p, i) => (
                        <label className="check" key={p.label}>
                          <input
                            type="checkbox"
                            checked={methods.includes(i)}
                            onChange={(e) =>
                              setMethods((m) =>
                                e.target.checked
                                  ? [...m, i].sort((a, b) => a - b)
                                  : m.filter((x) => x !== i),
                              )
                            }
                          />
                          {p.label}
                        </label>
                      ))}
                    </div>
                    <button disabled={!methods.length} onClick={compare}>
                      Compare current scenario
                    </button>
                  </fieldset>
                  {comparisons.length > 0 && (
                    <>
                      <RuntimeChart
                        rows={comparisons.map((r) => ({
                          name: r.label,
                          runtime: r.metrics.runtime_ms,
                        }))}
                      />
                      <ComparisonTable results={comparisons} />
                      <button
                        onClick={() =>
                          download("comparison.json", {
                            scenario,
                            results: comparisons,
                          })
                        }
                      >
                        Export measured comparison
                      </button>
                    </>
                  )}
                  <div className="experiment">
                    <h3>Reproducible experiments</h3>
                    <fieldset disabled={!!busy}>
                      <div className="three">
                        <label>
                          Experiment
                          <select
                            aria-label="Experiment"
                            value={experimentKind}
                            onChange={(e) => setExperimentKind(e.target.value)}
                          >
                            <option value="deadline">
                              30 / 60 / 120 minute deadlines
                            </option>
                            <option value="scale">
                              10 through 300 requests
                            </option>
                            <option value="pressure">
                              Budget / supply / beds / roads
                            </option>
                          </select>
                        </label>
                        <NumberField
                          label="Repeated runs"
                          value={repeats}
                          min={1}
                          max={3}
                          onChange={setRepeats}
                        />
                        <button
                          disabled={!methods.length}
                          onClick={runExperiment}
                        >
                          Run experiment
                        </button>
                      </div>
                    </fieldset>
                    <p>
                      Experiments generate from the left-side settings. Deadline
                      and pressure trials hold the same base
                      locations/resources; scaling regenerates supply in
                      proportion to demand. Each solver has at most 2 seconds /
                      10,000 steps per trial. Repeats change solver seeds only.
                    </p>
                    {experiment && (
                      <>
                        <label>
                          Chart metric
                          <select
                            aria-label="Chart metric"
                            value={chartMetric}
                            onChange={(e) => setChartMetric(e.target.value)}
                          >
                            <option value="runtime_ms">Runtime (ms)</option>
                            <option value="search_steps">Search steps</option>
                            <option value="fully_served">
                              Fully served incidents
                            </option>
                            <option value="constraint_checks">
                              Constraint checks
                            </option>
                          </select>
                        </label>
                        <ExperimentChart
                          rows={experiment.rows}
                          metric={chartMetric}
                        />
                        <p>
                          Charts show means across repeats; exported results
                          retain each run and exact scenario fingerprints.
                        </p>
                        <div className="table-scroll inventory">
                          <table>
                            <thead>
                              <tr>
                                <th>Variant</th>
                                <th>Method</th>
                                <th>Status</th>
                                <th>Full / partial / none</th>
                                <th>Steps</th>
                                <th>Runtime ms</th>
                                <th>Empty domains</th>
                              </tr>
                            </thead>
                            <tbody>
                              {experiment.rows.map((r, n) => (
                                <tr key={n}>
                                  <td>{r.variant}</td>
                                  <td>{r.method}</td>
                                  <td>{r.status}</td>
                                  <td>
                                    {r.summary.fully_served} /{" "}
                                    {r.summary.partially_served} /{" "}
                                    {r.summary.unserved}
                                  </td>
                                  <td>{r.metrics.search_steps}</td>
                                  <td>{fmt(r.metrics.runtime_ms)}</td>
                                  <td>{r.empty_domains}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <button
                          onClick={() =>
                            download(
                              `experiment-${experiment.kind}.json`,
                              experiment,
                            )
                          }
                        >
                          Export raw experiment JSON
                        </button>
                      </>
                    )}
                  </div>
                </section>
              </>
            )}
            {!scenario && !busy && (
              <section className="card">
                <h2>Generate a scenario to begin</h2>
                <button onClick={gen}>Retry scenario setup</button>
              </section>
            )}
          </div>
        </div>
      </main>
      <footer>
        Dhaka Emergency Control · AI Lab 2{" "}
        <span>Feasibility first. Measured search. Honest limits.</span>
      </footer>
    </>
  );
}
