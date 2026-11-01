# Demonstration guide for Palash Sir

Start Lab 2 using the README commands. Keep the default base-map switch off for an offline demo. Each “Generate scenario” replaces current data and clears old solutions. All road paths shown after solving are computed from selected assignments.

1. **Single medical emergency.** Choose “1 · Single medical”, generate, allocate. Show one physical ambulance, its current origin, computed response ETA, reachable hospital, separate patient-transport time and validated budget. This demo places its unit at simulated center S5.
2. **Fire emergency.** Choose “2 · Fire + medical support”, generate, allocate. Show separate fire and ambulance slots and paths. Higher-severity generated fires also require a rescue team. Click the incident to isolate its routes; discuss all-slots full service.
3. **Multiple simultaneous requests.** Choose “3 · Simultaneous competition”. Three medical requests compete for one ambulance. Allocate and show full/partial/unserved counts and the C3 exclusivity conflicts. A resource ID never appears twice in the returned assignments. Try severity ordering and show that hard rules still apply.
4. **Blocked road.** Choose “4 · Blocked road detour”, generate, allocate. The direct S5 road `6:3>6:4` is blocked; a different route is computed. Click a road to toggle a directed blockage: old results disappear, so re-solve. JSON can block both directions or an entire corridor. Never claim a red closed road was used.
5. **Insufficient resources and other constraints.** Choose “5 · Insufficient resources”. Then try setting hospital beds to zero or reducing the current budget in Scenario JSON. Re-solve; explain domain exclusions versus search limits. Fire busy, rescue shortage and ambulance shortage are also available as pressure experiments. A partly staffed multi-resource incident is “partially served”, never “fully served”.
6. **Algorithm comparison and actual CBJ.** On a shared custom workload, select Plain BT, BT+MRV, BT+MRV+LCV, FC, AC-3, CBJ and local search, then “Compare current scenario”. Show measured steps/checks/time, N/A fields and independent validation. For an understandable nonchronological jump choose “CBJ conflict witness”; generation disables MRV/degree/LCV/severity. Compare **Plain BT** and **Plain CBJ** or solve them separately. Inspect trace: C fails on AM1, skips unrelated rescue decision B, jumps to A and changes A to AM2. The saved measured comparison is `demos/backjumping-comparison.json`. Medical care in this tiny witness is on-scene (no patient transport).
7. **Scalability.** Set Demonstration to Custom workload. Select the scale experiment and run with desired methods, e.g. Plain BT, MRV, FC, CBJ, local search. Show 10,20,30,50,100,150,250,300 requests. Switch chart metric between runtime, steps and fully served. Resource counts scale with demand. Explain timeout/step-limit results honestly. Saved measured results are already in `results/scale.json` and `.csv`.
8. **Deadline variation.** Run the deadline experiment. Explain that only 30/60/120-minute limits change; physical locations, resources, roads and budget are held fixed. Compare coverage, domain exclusions and runtime. Export the raw data. Finish with the pressure experiment to show budget, busy units, hospital capacity, road disconnection and competing severe requests.

## Small board example

Write X={A ambulance, B rescue, C ambulance}; D(A)={AM1,AM2}, D(B)={RT1,RT2}, D(C)={AM1}. C has a short deadline, so AM2 is excluded. AM1 cannot serve both A and C in this snapshot. Choosing A=AM1 causes C to fail; B is unrelated. Backtracking revisits B, CBJ skips B, forward checking detects C's empty future domain immediately, and AC-3 can remove AM1 from A before search. All methods can choose A=AM2, B=RT1, C=AM1. This is feasible, not proven cost optimal.

## Import a reproducible scenario

Open `demos/medical.json`, `fire.json`, `competition.json`, `blocked.json`, `insufficient.json` or `backjumping.json`, copy its complete contents into the Scenario JSON editor, then “Validate & apply JSON”. Generation-only configurations `scale-N.generation.json` are inputs to `/api/scenarios`, not full scenario documents. Custom requirement quantities/capabilities can be edited in full JSON. Exports preserve a complete scenario and its measured allocation.

## Questions to be ready for

- **Why CSP?** Several assignment variables share scarce resources, hospital beds and a budget; finding one path alone does not resolve these conflicts.
- **What is hard?** Type/capability, available physical units, exclusivity, deadlines, accessible paths, capacities, budget, hospital reachability/beds and all slots for full service.
- **What is soft?** Severity/deadline ordering and LCV; these guide search but cannot authorize violations.
- **What does AC-3 prove?** Binary consistency or a domain wipeout, not global cumulative feasibility.
- **Can one ambulance be reused?** No, the snapshot model conservatively uses each unit at most once. Release time is displayed, but no time-expanded scheduling is implemented.
- **Is a partial solution optimal?** No. It is an independently valid subset encountered during bounded search.
- **Are these real roads/traffic?** No, the default network and operational data are explicitly simulated over Dhaka coordinates; OSM tiles only provide an optional background.
