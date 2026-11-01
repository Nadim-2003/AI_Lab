# Algorithms and architecture

The control center receives a scenario, builds domains once, searches for a feasible assignment and independently validates every returned subset. Dijkstra calculates response and patient-transport paths before CSP search. Domains hold routes by reference; the router caches shortest-path trees by origin. The API returns exact directed edge IDs, geometries, ETAs, costs and incident status from the chosen assignments.

## Systematic search

**Chronological backtracking** selects an unassigned slot, tries its domain values, checks constraints, recurses, and reverses the most recent assignment when it fails. An exhausted root proves there is no complete allocation. Limits interrupt the search and retain the largest valid prefix encountered; this is not a maximum-coverage algorithm.

**Conflict-directed backjumping (CBJ)** records previously assigned variables that block each attempted value. When a child fails, its conflict set is returned. If the current variable is absent, changing its value cannot fix that recorded failure: return past it without trying its remaining values. Otherwise remove the current variable from the returned set, merge the other causes and try another value. On exhaustion, propagate the merged set to the most recent responsible ancestor. Global budget conflicts conservatively name every contributing assigned slot; hospital conflicts name the slots using that hospital. This preserves correctness even with dynamic ordering and non-binary constraints. CBJ does not secretly run forward checking.

The `backjumping` scenario is a concrete witness. Fixed order A, B, C; A can use AM1/AM2, B can use RT1/RT2, C can use AM1 only. A=AM1 makes C fail. B is unrelated, so CBJ skips B and revisits A. With default generated costs and generous budget the measured fixture uses 8 attempted assignments for chronological BT, 6 for CBJ (one nonchronological jump and one skipped level), and 4 for forward checking. MRV would select singleton C first and remove this particular distinction, so the witness explicitly disables ordering heuristics.

**Forward checking** tests remaining values of all unassigned slots after each assignment, including residual global budget and hospital capacity. It stores old domain lists on a trail. A wipeout fails early; reversing the branch restores every list. The same witness avoids B's subtree immediately. It checks consistency against assigned values; it does not assume consistency among all future values.

**AC-3** maintains a directed queue of binary arcs. Revise removes a value only when no neighbor value supports it under physical-unit exclusivity and pairwise hospital capacity. Changed domains re-enqueue affected incoming arcs. A wipeout proves infeasibility. Default AC-3 is preprocessing followed by backtracking. Optional MAC sets assigned domains to singletons and repeats AC-3 in branch-local copies. Global cumulative beds and total budget remain shared search checks: three one-patient slots in a two-bed hospital can be pairwise consistent but globally impossible. A dedicated test verifies this distinction.

## Heuristics and priority

**MRV** counts values currently feasible against the actual partial assignment, rather than just reading the original domain size. Lowest count is first. With MRV enabled, severity is a secondary policy; with it disabled, severity can lead. Severity descending, then shorter relative response deadline are soft preferences; degree is the next tie-breaker and incident/slot ID gives deterministic order. Degree counts binary neighbors sharing potential units or hospitals, not the global budget clique. Fixed order disables MRV, degree and severity.

**LCV** counts incompatible future binary domain values and tries the value removing the fewest first. It does not claim to solve the global budget minimization problem. It may add overhead on easy or large instances. Constraints still check every chosen value. MRV/degree/LCV apply to systematic methods; local search ignores these systematic-order switches.

## Local search

Min-conflicts initializes a complete assignment by seeded random choices from unary-feasible domains, identifies conflicting slots, chooses one and tries the lowest-conflict candidate with random tie-breaking. Binary conflicts count competing units; global constraints include responsible contributors in the conflict score. Bounded restarts provide another initial state, with one overall time/step budget. Empty domains prove no complete solution; failure to converge otherwise means `local_limit`, `step_limit` or `timeout`, never a proof of infeasibility.

A raw local assignment can violate exclusivity, budget or cumulative beds. Its unresolved constraint counts are exposed separately. A severity-ordered repair pass keeps only assignments feasible against the kept subset and saves the best valid subset encountered. Final validation checks that subset independently. A repair result is neither a complete min-conflicts solution nor a maximum allocation. Only a complete, validated assignment receives `feasible`.

## Metric definitions

| Metric | Meaning |
| --- | --- |
| Fully served | All incident requirement slots are assigned |
| Partly served | At least one, but not all, slots are assigned |
| Unserved | No slots assigned |
| Allocated units | Actual assigned slots, with exclusivity enforced |
| Search steps | Attempted value extensions in exact search; repair iterations in local search |
| Assignments attempted | Candidate values attempted by systematic search or scored for a local-search move |
| Constraint checks | Shared consistency evaluations plus binary evaluations for AC/LCV; not CPU instructions |
| Backtracks | Assigned value reversed after a failed subtree |
| Backjumps | Conflict-directed jumps that skip at least one unrelated decision |
| Skipped levels | Decisions bypassed by conflict propagation |
| Pruned values / wipeouts | Actual propagation removals / emptied domains |
| Runtime | Measured solver and heuristic/propagation work, excluding domain/routing preparation and final validation |
| Violations | Independently detected hard violations in returned subset; raw local conflicts reported separately |

Algorithm-native search steps are not identical operations across methods; interpret them alongside candidate attempts, checks and measured time. N/A (`null` in JSON) means an operation does not apply. Search failures count rejected choices, not invalid allocations. Domain exclusions count failed unary candidate filters; one resource is counted at its first failing filter, so these are diagnostics rather than an exhaustive list of every possible reason. Failure sets are bounded in trace output to 150 events. Local raw diagnostics can exceed a strict time budget slightly because termination diagnostics still run. Boundary checks occur periodically during large loops, so time limits are cooperative rather than real-time guarantees.

## Correctness checks

An independent validator traverses each selected route's edges, checks continuity/direction/blockage, recomputes time/distance/cost, verifies capabilities/capacity/availability/deadlines, counts physical resource reuse and hospital patients, and enforces the global budget. It also checks that reported geometry matches the graph. Exact algorithms are tested over all 343 nonempty three-variable domain combinations (per algorithm), and against exhaustive valid allocations for small randomized hospital/budget cases. Separate tests cover domain restoration, actual CBJ skipping, MAC, reachability, local-search failure status, quantities and passenger beds.

## Computational limits

Inputs allow at most 300 incidents, 900 slots, 2,000 resources, 2,000 nodes and 10,000 directed roads. Snapshot exclusivity intentionally avoids the complexity of time-expanded resource reuse. Systematic recursion cannot exceed the 900-slot cap. Dense shared-resource domains make MRV/LCV/AC expensive; large exact problems can exceed search limits. The project measures and reports these effects instead of claiming all 300-request cases solve instantly.
