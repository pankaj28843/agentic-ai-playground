import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Read allowed hosts from environment variable (comma-separated list)
// Example: VITE_ALLOWED_HOSTS="app.example.com,*.example.dev"
const allowedHosts = process.env.VITE_ALLOWED_HOSTS
  ? process.env.VITE_ALLOWED_HOSTS.split(",").map((h) => h.trim())
  : [];

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: true,
  },
  server: {
    host: true,
    port: 10000,
    // Allow specific hosts when running behind nginx proxy
    allowedHosts: allowedHosts.length > 0 ? allowedHosts : undefined,
  },
  preview: {
    host: true,
    port: 10000,
    allowedHosts: allowedHosts.length > 0 ? allowedHosts : undefined,
  },
});
