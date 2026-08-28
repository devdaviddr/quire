import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // bind 0.0.0.0 so the port is reachable from outside the container
    port: 5173,
    // Same-origin in the browser: the API is proxied rather than called
    // cross-origin, so there is no CORS config to keep in sync.
    proxy: {
      "/api": {
        target: "http://api:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
