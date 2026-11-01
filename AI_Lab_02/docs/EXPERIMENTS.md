# Executed experiments and observations

The committed JSON/CSV files in `results/` were generated in this environment using seed 42, two solver-seed repeats and a limit of **0.25 seconds / 3,000 search steps per run**. Seven methods were tested: plain BT, BT+MRV, BT+MRV+degree+LCV, CBJ+MRV+degree, FC+MRV+degree, AC-3+MRV+degree and local search. These limits are intentionally small and do not establish full solver capacity. Re-run with the commands in README to obtain measurements for another machine.

There are 112 scale runs, 42 deadline runs and 126 pressure runs: **280 total**. Every returned subset has zero independently detected hard-constraint violations. Results contain feasible, infeasible, timeout and step-limit outcomes; they are not all successful complete solves. The reported completion count is observed coverage, never claimed maximum coverage.

## Scaling

| Requests | Example observed outcome in first repeat |
| --- | --- |
| 10 | All seven methods completed; overhead made plain BT fastest on this easy case |
| 20 | All seven completed; LCV and propagation incurred additional consistency work |
| 30 | Six completed; LCV exceeded the short time budget |
| 50 | Plain BT and local search completed; several heuristic/propagation variants timed out |
| 100, 150, 250, 300 | All methods hit time/step limits in this short batch; partial allocations remain valid |

Resource pools grow with incident resource-slot demand at supply ratio 1.05. Hospital beds grow at patients × 1.1. Resources are therefore finite, not an unlimited independent resource for each slot. Multi-resource incidents, mixed severity, simulated traffic and 4% blocked undirected road pairs create real competition. At large scales even evaluating MRV/LCV or AC arcs can consume the time limit before a useful partial assignment. Zero fully served incidents can therefore mean time spent in preprocessing/ordering, not evidence that the scenario is impossible. Plain BT reaches a deep prefix quickly but can spend its remaining steps on conflicting low-ID resources. Local search often yields broader partial coverage under the same short budget, without proving maximality.

## Deadline sensitivity

The same 20 incidents, locations, resources, hospital beds, roads and budget are cloned for deadlines 30, 60 and 120 minutes. Only the deadline changes. At 30 minutes plain BT hit its 3,000-step limit with 18 fully served incidents in the first repeat; MRV, CBJ, FC, AC-3 and local search completed. At 60 and 120 minutes all seven completed. Domain exclusions explicitly count C4 deadline failures. More generous deadlines enlarge domains; that can also increase heuristic/filtering workload, so runtime need not decrease monotonically. Different valid allocations and coverage under a limit do not establish an optimization ranking.

## Budget/capacity/road pressure

Pressure trials modify one base scenario, keeping locations and unrelated configuration fixed:

- Baseline and increased budget completed with all methods in this batch.
- Reduced budget (`×0.35`) caused bounded incomplete search. C7 rejected choices were recorded; no returned assignment exceeded the actual budget.
- Disabling half the ambulances or rescue units caused bounded incomplete searches and lower observed coverage. Resource exclusivity is never relaxed.
- Occupying every fire unit removes fire-slot domains. Several methods immediately proved complete allocation impossible; plain fixed-order BT can still exhaust its limit in an earlier unrelated subtree.
- Removing hospital beds empties medical domains, proving complete allocation impossible. Rescue-only slots can still appear in partial outcomes.
- Blocking a north-south corridor disconnects the directed grid into regions. Some slots have no reachable responders; other slots retain feasible routes.
- A simultaneous all-severity-5 trial changes priority while keeping the original demands/deadlines fixed, isolating the ordering policy rather than also changing resources. For a severity-dependent deadline trial enable that generator option separately.

The exact failed unary filters, empty domains, rejected search constraints, per-method status and complete/partial/unserved counts are in the saved data. A search limit is not relabeled as infeasibility even if the underlying configuration was designed to be scarce.

## Controlled algorithm witness

`demos/backjumping-comparison.json` measures the same three-slot resource scenario with ordering heuristics disabled. Chronological BT attempts 8 values, CBJ attempts 6 with one true nonchronological jump/one skipped decision, forward checking attempts 4, and AC-3 attempts 3 after filtering. These numbers arise from actual execution. They are a useful explanation of mechanisms, not a claim that these algorithms always rank in that order. Tests also exhaust small CSPs against a reference enumerator.

## Interpretation and limitations

Runtime uses `perf_counter`, includes search/heuristics/propagation and excludes generating scenarios, routing/domain construction, validation, network transport and rendering. Shared preparation and generation times are recorded separately in newer runs. Exact methods are deterministic on the same instance; repeat seeds mainly affect local search. UI charts average repeats but retain each raw run in exports. N/A metrics remain null. Time budgets are cooperative; small overshoots for checks/termination diagnostics are expected. There is no benchmark claim for real Dhaka traffic or actual emergency response, and no maximum-coverage/global-optimality claim.
