import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";
vi.mock("./MapView", () => ({ default: () => <div>Computed map</div> }));
vi.mock("./Charts", () => ({
  RuntimeChart: () => null,
  ExperimentChart: () => null,
}));
const scenario = {
  nodes: { a: [90.4, 23.7] },
  roads: [],
  stations: [],
  hospitals: [],
  resources: [],
  incidents: [
    {
      id: "I1",
      category: "medical",
      node: "a",
      severity: 3,
      deadline: 60,
      requirements: [{ quantity: 1, role: "ambulance" }],
    },
  ],
  budget: 500,
};
afterEach(() => vi.unstubAllGlobals());
test("loads scenario and sends selected solver options", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => scenario });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  expect(await screen.findByText("Computed map")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Algorithm"), {
    target: { value: "backjumping" },
  });
  const result = {
    status: "infeasible",
    summary: {
      fully_served: 0,
      partially_served: 0,
      unserved: 1,
      allocated_units: 0,
      required_slots: 1,
    },
    assignments: [],
    incidents: [],
    metrics: { runtime_ms: 1 },
    validation: { valid: true, violation_count: 0, total_cost: 0 },
    domain_rejections: {},
    constraint_failures: {},
    trace: [],
  };
  fetch.mockResolvedValue({ ok: true, json: async () => result });
  fireEvent.click(screen.getByText("Allocate emergency resources →"));
  expect(await screen.findByText("Allocation results")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.calls[1][1].body).options.algorithm).toBe(
    "backjumping",
  );
  expect(screen.getByText(/Full allocation is infeasible/)).toBeInTheDocument();
});
test("reports server validation errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Invalid scenario" }),
      }),
  );
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Invalid scenario",
  );
});
