import {defineConfig} from 'vite'
export default defineConfig({server: {proxy: {'/api': 'http://127.0.0.1:8000'}}, test: {exclude: ['e2e/**', 'node_modules/**'], environment: 'jsdom', setupFiles: './src/test-setup.js'}})
