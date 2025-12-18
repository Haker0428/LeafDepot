/**
 * 前端日志工具
 * 将前端日志发送到后端保存到 debug 目录
 */

import { GATEWAY_URL } from '@/config/ip_address';

interface LogOptions {
  level: 'log' | 'info' | 'warn' | 'error';
  message: string;
  source?: string;
  extra?: Record<string, any>;
}

class Logger {
  private source: string;
  private enabled: boolean = true;

  constructor(source: string = 'frontend') {
    this.source = source;
    // 从 localStorage 读取日志开关
    const logEnabled = localStorage.getItem('frontend_log_enabled');
    if (logEnabled === 'false') {
      this.enabled = false;
    }
  }

  /**
   * 发送日志到后端
   */
  private async sendLog(options: LogOptions): Promise<void> {
    if (!this.enabled) {
      return;
    }

    try {
      await fetch(`${GATEWAY_URL}/api/log/frontend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          level: options.level,
          message: options.message,
          timestamp: new Date().toISOString(),
          source: options.source || this.source,
          extra: options.extra,
        }),
      });
    } catch (error) {
      // 静默失败，避免日志收集本身导致错误
      console.warn('Failed to send log to backend:', error);
    }
  }

  /**
   * 记录普通日志
   */
  log(message: string, ...args: any[]): void {
    console.log(`[${this.source}]`, message, ...args);
    this.sendLog({
      level: 'log',
      message: `${message} ${args.length > 0 ? JSON.stringify(args) : ''}`,
      extra: args.length > 0 ? { args } : undefined,
    });
  }

  /**
   * 记录信息日志
   */
  info(message: string, ...args: any[]): void {
    console.info(`[${this.source}]`, message, ...args);
    this.sendLog({
      level: 'info',
      message: `${message} ${args.length > 0 ? JSON.stringify(args) : ''}`,
      extra: args.length > 0 ? { args } : undefined,
    });
  }

  /**
   * 记录警告日志
   */
  warn(message: string, ...args: any[]): void {
    console.warn(`[${this.source}]`, message, ...args);
    this.sendLog({
      level: 'warn',
      message: `${message} ${args.length > 0 ? JSON.stringify(args) : ''}`,
      extra: args.length > 0 ? { args } : undefined,
    });
  }

  /**
   * 记录错误日志
   */
  error(message: string, error?: Error | any, ...args: any[]): void {
    console.error(`[${this.source}]`, message, error, ...args);
    
    const errorInfo: Record<string, any> = {};
    if (error) {
      if (error instanceof Error) {
        errorInfo.error = {
          name: error.name,
          message: error.message,
          stack: error.stack,
        };
      } else {
        errorInfo.error = error;
      }
    }
    if (args.length > 0) {
      errorInfo.args = args;
    }

    this.sendLog({
      level: 'error',
      message: `${message} ${error instanceof Error ? error.message : JSON.stringify(error)}`,
      extra: Object.keys(errorInfo).length > 0 ? errorInfo : undefined,
    });
  }

  /**
   * 启用/禁用日志
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    localStorage.setItem('frontend_log_enabled', enabled.toString());
  }

  /**
   * 检查日志是否启用
   */
  isEnabled(): boolean {
    return this.enabled;
  }
}

// 创建默认日志实例
const defaultLogger = new Logger('frontend');

// 重写全局 console 方法（可选）
const originalConsole = {
  log: console.log,
  info: console.info,
  warn: console.warn,
  error: console.error,
};

// 可选：拦截全局 console 调用
export function interceptConsole(): void {
  console.log = (...args: any[]) => {
    originalConsole.log(...args);
    defaultLogger.log(args.join(' '));
  };

  console.info = (...args: any[]) => {
    originalConsole.info(...args);
    defaultLogger.info(args.join(' '));
  };

  console.warn = (...args: any[]) => {
    originalConsole.warn(...args);
    defaultLogger.warn(args.join(' '));
  };

  console.error = (...args: any[]) => {
    originalConsole.error(...args);
    defaultLogger.error(args.join(' '));
  };
}

// 导出默认日志实例和类
export { Logger, defaultLogger as logger };
export default defaultLogger;

