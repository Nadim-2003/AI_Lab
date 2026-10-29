const {existsSync} = require('node:fs')
const {defineConfig} = require('@playwright/test')
module.exports = defineConfig({testDir: './e2e', use: {baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', launchOptions: {executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined), args: ['--no-sandbox']}}, webServer: {command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: true}})
