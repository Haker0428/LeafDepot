/**
 * 前端日志模块
 * 将日志批量发送到 Gateway，写入 frontend_YYYYMMDD.log
 */
import { GATEWAY_URL } from "../config/ip_address";

type LogLevel = "debug" | "info" | "warn" | "error";
type Source = "api" | "auth" | "inventory" | "websocket" | "error" | "action" | "page";

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  source: Source;
  extra?: Record<string, unknown>;
}

const _queue: LogEntry[] = [];
const _batchSize = 20;
const _flushInterval = 5000; // ms
let _timer: ReturnType<typeof setTimeout> | null = null;

function _enqueue(entry: LogEntry) {
  _queue.push(entry);
  if (_queue.length >= _batchSize) {
    _flush();
  } else if (!_timer) {
    _timer = setTimeout(_flush, _flushInterval);
  }
}

function _flush() {
  if (_timer) {
    clearTimeout(_timer);
    _timer = null;
  }
  if (_queue.length === 0) return;

  const batch = _queue.splice(0);
  fetch(`${GATEWAY_URL}/api/log/frontend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries: batch }),
  }).catch(() => {
    // silent fail
  });
}

// 页面卸载时flush
window.addEventListener("beforeunload", _flush);

export const logger = {
  debug(msg: string, extra?: Record<string, unknown>, source: Source = "action") {
    _enqueue({ level: "debug", message: msg, timestamp: new Date().toISOString(), source, extra });
  },
  info(msg: string, extra?: Record<string, unknown>, source: Source = "action") {
    _enqueue({ level: "info", message: msg, timestamp: new Date().toISOString(), source, extra });
  },
  warn(msg: string, extra?: Record<string, unknown>, source: Source = "action") {
    _enqueue({ level: "warn", message: msg, timestamp: new Date().toISOString(), source, extra });
  },
  error(msg: string, extra?: Record<string, unknown>, source: Source = "error") {
    _enqueue({ level: "error", message: msg, timestamp: new Date().toISOString(), source, extra });
  },
};

// ===== 统一错误捕获 =====
window.onerror = (msg, _src, line, col, err) => {
  logger.error(`[UNCAUGHT] ${msg}`, {
    line,
    col,
    stack: err?.stack,
  });
  return false;
};

window.onunhandledrejection = (e) => {
  logger.error(`[PROMISE_REJECT] ${e.reason}`, {
    reason: String(e.reason),
  });
};

// ===== API 拦截器（可选，在使用时显式调用）====
// 提供一个 fetch 包装器，也可以直接在组件中调用 logger
export function wrapFetch(originalFetch: typeof fetch) {
  return async function loggedFetch(
    input: RequestInfo | URL,
    init?: RequestInit
  ): Promise<Response> {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method || "GET";
    const start = Date.now();
    try {
      const res = await originalFetch(input, init);
      const ms = Date.now() - start;
      if (!res.ok) {
        logger.warn(`[API FAIL] ${method} ${url} → ${res.status} (${ms}ms)`, {}, "api");
      }
      return res;
    } catch (e: unknown) {
      const ms = Date.now() - start;
      logger.error(`[API ERROR] ${method} ${url} → 网络错误 (${ms}ms)`, { error: String(e) }, "api");
      throw e;
    }
  };
}
