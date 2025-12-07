/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 22:32:22
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-28 00:16:07
 * @FilePath: /ui/src/config/ip_address.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by lizh, All Rights Reserved. 
 */

// 获取网关地址，支持环境变量和默认值
function getGatewayUrl(): string {
  // 优先使用环境变量
  const envUrl = import.meta.env.VITE_GATEWAY_URL;
  if (envUrl) {
    // 确保 URL 包含协议
    return envUrl.startsWith('http://') || envUrl.startsWith('https://') 
      ? envUrl 
      : `http://${envUrl}`;
  }
  
  // 根据当前主机名自动判断
  // 如果运行在 10.16.82.95，使用该 IP；否则使用 localhost
  const hostname = window.location.hostname;
  if (hostname === '10.16.82.95' || hostname.includes('10.16.82.95')) {
    return 'http://10.16.82.95:8000';
  }
  
  // 默认使用 localhost
  return 'http://localhost:8000';
}

// 网关地址配置
export const GATEWAY_URL = getGatewayUrl();