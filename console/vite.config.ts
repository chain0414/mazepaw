import fs from "fs";
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";

/**
 * embed 输出到 `src/copaw/console`；FastAPI 在部分情况下会从 `console/dist` 读静态文件。
 * 每次 embed 构建结束后镜像到 `console/dist`，避免 8088 仍 serve 旧 hash。
 */
function syncEmbedToConsoleDistPlugin(embedOutDir: string): Plugin {
  const destDir = path.resolve(path.dirname(embedOutDir), "../../console/dist");
  return {
    name: "sync-embed-to-console-dist",
    apply: "build",
    closeBundle() {
      fs.rmSync(destDir, { recursive: true, force: true });
      fs.cpSync(embedOutDir, destDir, { recursive: true });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Empty = same-origin; frontend and backend served together, no hardcoded host.
  const apiBaseUrl = env.BASE_URL ?? "";
  const embed = mode === "embed";
  const embedOutDir = path.resolve(__dirname, "../src/copaw/console");

  return {
    define: {
      BASE_URL: JSON.stringify(apiBaseUrl),
      TOKEN: JSON.stringify(env.TOKEN || ""),
      MOBILE: false,
    },
    plugins: [
      react(),
      ...(embed ? [syncEmbedToConsoleDistPlugin(embedOutDir)] : []),
    ],
    css: {
      modules: {
        localsConvention: "camelCase",
        generateScopedName: "[name]__[local]__[hash:base64:5]",
      },
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      // Dev: Vite (5173) + API on 8088 — same-origin `/api/*` as production behind copaw app
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8088",
          changeOrigin: true,
        },
      },
    },
    optimizeDeps: {
      include: ["diff"],
    },
    ...(embed
      ? {
          build: {
            outDir: embedOutDir,
            emptyOutDir: true,
          },
        }
      : {}),
  };
});
