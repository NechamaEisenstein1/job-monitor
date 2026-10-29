import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // The articles (../content) are shared with the backend, which renders their SEO pages.
  server: { proxy: { "/api": "http://localhost:8000" }, fs: { allow: [".", "../content"] } },
});
