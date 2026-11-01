import { defineConfig } from "vite";
export default defineConfig({
  server: { proxy: { "/api": "http://127.0.0.1:8002" } },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.js",
    exclude: ["e2e/**", "node_modules/**"],
  },
});
