/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The FastAPI backend runs on :8000 during local development.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "node",
  },
});
