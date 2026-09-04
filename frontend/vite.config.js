import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/seats": "http://127.0.0.1:8000",
      "/holds": "http://127.0.0.1:8000",
      "/bookings": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
