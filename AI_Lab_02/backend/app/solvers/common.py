from collections import Counter
from time import perf_counter


class SearchLimit(Exception):
    pass


class Engine:
    def __init__(self, problem, options):
        self.p, self.o = problem, options
        self.started = perf_counter()
        self.assignment, self.best = {}, {}
        self.metrics = dict(
            search_steps=0,
            assignments_attempted=0,
            constraint_checks=0,
            backtracks=0,
            backjumps=0,
            skipped_levels=0,
            pruned_values=0,
            arc_revisions=0,
            domain_wipeouts=0,
            conflict_sets=0,
            max_conflict_set=0,
            restarts=0,
        )
        self.failures = Counter()
        self.trace = []
        self.context()

    def context(self):
        if hasattr(self.p, "prepare"):
            self.p.prepare(self.assignment)

    def bound(self):
        if self.metrics["search_steps"] >= self.o.max_steps:
            raise SearchLimit("step_limit")
        if perf_counter() - self.started >= self.o.timeout:
            raise SearchLimit("timeout")

    def check(self, x, value, assignment=None):
        self.metrics["constraint_checks"] += 1
        if self.metrics["constraint_checks"] % 128 == 0:
            self.bound()
        causes, codes = self.p.conflicts(
            x, value, self.assignment if assignment is None else assignment
        )
        self.failures.update(codes)
        return causes, codes

    def put(self, x, v):
        self.assignment[x] = v
        self.context()
        if len(self.assignment) > len(self.best):
            self.best = dict(self.assignment)

    def remove(self, x):
        self.assignment.pop(x, None)
        self.context()

    def ordered_values(self, x, domains):
        values = list(domains[x])
        if not self.o.lcv:
            return values

        # Binary LCV: count affected values; global constraints stay in check().
        def impact(value):
            score = 0
            for y in self.p.neighbors[x] - self.assignment.keys():
                for other in domains[y]:
                    self.metrics["constraint_checks"] += 1
                    score += not self.p.compatible(x, value, y, other)
                    if self.metrics["constraint_checks"] % 128 == 0:
                        self.bound()
            return score

        return sorted(values, key=impact)

    def select(self, domains):
        choices = [x for x in self.p.slots if x not in self.assignment]
        if not self.o.mrv:
            return min(choices, key=lambda x: self.tie(x, domains))
        ranked = []
        for x in choices:
            count = sum(not self.check(x, v)[1] for v in domains[x])
            ranked.append((count, self.tie(x, domains), x))
        return min(ranked)[2]

    def tie(self, x, domains):
        slot = self.p.slots[x]
        severity = (
            (-slot.incident.severity, slot.incident.deadline)
            if self.o.severity_order
            else (0, 0)
        )
        degree = (
            -len(self.p.neighbors[x] - self.assignment.keys()) if self.o.degree else 0
        )
        return (*severity, degree, x)

    def step(self):
        self.bound()
        self.metrics["search_steps"] += 1

    def event(self, event, **data):
        if len(self.trace) < 150:
            self.trace.append({"event": event, **data})
