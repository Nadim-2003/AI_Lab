const { test, expect } = require("@playwright/test");
test("medical allocation, actual map routes, inventory and stale-result clearing", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page
    .getByLabel("Demonstration", { exact: true })
    .selectOption("medical");
  await page
    .getByRole("button", { name: "Generate scenario", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveCount(0);
  const solved = page.waitForResponse(
    (r) => r.url().endsWith("/api/solve") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Allocate emergency resources →" })
    .click();
  const payload = await (await solved).json();
  await expect(page.locator("path.dispatch-route")).toHaveCount(
    payload.assignments.length,
  );
  await expect(
    page.getByText("Allocation results", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("feasible", { exact: true })).toBeVisible();
  await expect(page.locator(".validation")).toContainText("0 violations");
  await expect(page.locator(".leaflet-overlay-pane path")).not.toHaveCount(0);
  await page.getByRole("button", { name: "Resources", exact: true }).click();
  await expect(page.getByLabel("AMBULANCE-001 available")).toBeChecked();
  await page.getByLabel("AMBULANCE-001 available").uncheck();
  await expect(
    page.getByText("Allocation results", { exact: true }),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
});
test("fire allocation and measured same-scenario comparison", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Demonstration", { exact: true }).selectOption("fire");
  await page
    .getByRole("button", { name: "Generate scenario", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveCount(0);
  await page
    .getByLabel("Algorithm", { exact: true })
    .selectOption("forward_checking");
  const solved = page.waitForResponse(
    (r) => r.url().endsWith("/api/solve") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Allocate emergency resources →" })
    .click();
  const payload = await (await solved).json();
  await expect(page.locator("path.dispatch-route")).toHaveCount(
    payload.assignments.length,
  );
  await expect(
    page.getByText("Allocation results", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("feasible", { exact: true })).toBeVisible();
  await expect(page.getByText("FIRE-001 · S5", { exact: true })).toBeVisible();
  await expect(
    page.getByText("AMBULANCE-001 · S5", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Compare current scenario", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Export measured comparison" }),
  ).toBeVisible();
});
test("mobile has no page overflow and permits scenario editing", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".leaflet-container")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Scenario JSON", exact: true })
    .click();
  await expect(page.getByLabel("Scenario JSON editor")).toBeVisible();
  await page.screenshot({
    path: "test-results/control-mobile.png",
    fullPage: true,
  });
});
test("backjumping witness reports an actual skipped decision", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Demonstration", { exact: true })
    .selectOption("backjumping");
  await page
    .getByRole("button", { name: "Generate scenario", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveCount(0);
  const solved = page.waitForResponse(
    (r) => r.url().endsWith("/api/solve") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Allocate emergency resources →" })
    .click();
  const payload = await (await solved).json();
  expect(payload.metrics.backjumps).toBe(1);
  expect(payload.metrics.skipped_levels).toBe(1);
  expect(payload.validation.valid).toBe(true);
  await expect(page.locator("path.dispatch-route")).toHaveCount(
    payload.assignments.length,
  );
  await page
    .getByText("Search metrics, constraint failures & trace", { exact: true })
    .click();
  await expect(
    page.getByText("skip_unrelated", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/control-desktop.png",
    fullPage: true,
  });
});
