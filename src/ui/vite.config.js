import { defineConfig } from "vite";
import path from "path";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "#app": path.resolve(__dirname, "./src/app"),
      "#hooks": path.resolve(__dirname, "./src/app/hooks"),
      "#components": path.resolve(__dirname, "./src/components"),
      "#store": path.resolve(__dirname, "./src/app/store"),
      "#utils": path.resolve(__dirname, "./src/utils"),
    },
  },
});
