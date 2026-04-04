/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 22:32:22
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2026-04-04
 * @FilePath: /ui/src/config/ip_address.ts
 * @Description: 网关地址配置 - 从后端 /config/gateway 动态获取
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */

const DEFAULT_GATEWAY_URL = "http://10.16.82.95:8000";

// cachedGatewayUrl: null = 未获取, string = 已缓存
let cachedGatewayUrl: string | null = null;
let fetchPromise: Promise<string> | null = null;

/**
 * 获取网关地址（异步，推荐）。
 * 首次调用时从后端 /config/gateway 动态获取，之后使用缓存值。
 * 获取失败时回退到 DEFAULT_GATEWAY_URL。
 */
export async function getGatewayUrl(): Promise<string> {
  if (cachedGatewayUrl) return cachedGatewayUrl;
  if (fetchPromise) return fetchPromise;

  fetchPromise = (async () => {
    try {
      // 尝试通过 /api 代理访问网关（适用于 Vite dev server 跨域场景）
      const resp = await fetch("/api/config/gateway", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (resp.ok) {
        const data = (await resp.json()) as { gateway_url?: string };
        if (data.gateway_url) {
          cachedGatewayUrl = data.gateway_url;
          console.info("[Config] 网关地址已从后端获取:", cachedGatewayUrl);
          return cachedGatewayUrl;
        }
      }
    } catch (e) {
      console.warn("[Config] 无法从后端获取网关地址:", e);
    }
    // 回退到默认值
    cachedGatewayUrl = DEFAULT_GATEWAY_URL;
    console.info("[Config] 使用默认网关地址:", cachedGatewayUrl);
    return cachedGatewayUrl;
  })();

  return fetchPromise;
}

/**
 * 同步获取缓存的网关地址。
 * 在 getGatewayUrl() 首次完成前返回 null。
 */
export function getCachedGatewayUrl(): string | null {
  return cachedGatewayUrl;
}

/**
 * 网关地址常量（向后兼容）。
 * 建议优先使用 getGatewayUrl() 异步获取动态地址。
 */
export const GATEWAY_URL = DEFAULT_GATEWAY_URL;
