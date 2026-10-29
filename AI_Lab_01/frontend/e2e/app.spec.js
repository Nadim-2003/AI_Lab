import {test, expect} from '@playwright/test'

test('renders actual Leaflet map and honest missing-data state', async ({page}) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByText('Real road data has not been loaded.')).toBeVisible()
  await expect(page.locator('.leaflet-container')).toBeVisible()
  await expect(page.getByRole('button', {name: 'Run A* →'})).toBeDisabled()
  await expect(page.getByRole('checkbox', {name: 'BFS'})).toBeChecked()
  await page.getByRole('checkbox', {name: 'BFS'}).uncheck()
  await expect(page.getByRole('checkbox', {name: 'BFS'})).not.toBeChecked()
  await page.getByText('Custom scenario studio').click()
  await page.getByRole('button', {name: 'Duplicate active'}).click()
  await expect(page.getByLabel('Name', {exact: true})).toHaveValue('Normal Day copy')
  await expect(page.getByLabel('Scenario traffic', {exact: true})).toHaveValue('0')
  await page.getByLabel('Scenario traffic', {exact: true}).selectOption('1')
  await expect(page.getByLabel('Scenario traffic', {exact: true})).toHaveValue('1')
  await page.screenshot({path: 'test-results/missing-data-desktop.png', fullPage: true})
  expect(errors).toEqual([])
})

test('remains usable at a narrow viewport', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844})
  await page.goto('/')
  await expect(page.getByText('Real road data has not been loaded.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({path: 'test-results/missing-data-mobile.png', fullPage: true})
})
