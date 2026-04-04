/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

function getPlugins() {
  const plugins = [react(), tsconfigPaths()];
  return plugins;
}

export default defineConfig(({ mode }) => {
  // 读取 .env.local（优先级最高），其次 .env
  const env = loadEnv(mode, process.cwd(), "");
  // VITE_GATEWAY_URL 格式：http://192.168.91.128:8000
  const gatewayUrl = env.VITE_GATEWAY_URL || "http://localhost:8000";

  return {
    plugins: getPlugins(),
    server: {
      host: "0.0.0.0",
      port: 5173,
      allowedHosts: true,
      // 前端发往 /api 的请求代理到 Gateway（解决跨域问题）
      // 在 .env.local 中设置 VITE_GATEWAY_URL 指向实际 Gateway 地址
      proxy: {
        "/api": {
          target: gatewayUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
