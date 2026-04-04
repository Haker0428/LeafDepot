// 操作记录接口定义
export interface OperationLog {
  id: string;
  timestamp: string;
  operation_type: string;
  user_id?: string;
  user_name?: string;
  action: string;
  target?: string;
  status: string;
  details: Record<string, any>;
  ip_address?: string;
}

// API 基础路径
import { GATEWAY_URL } from '../config/ip_address';

/**
 * 添加操作记录
 */
export async function addOperationLog(log: Omit<OperationLog, 'id' | 'timestamp'>): Promise<OperationLog> {
  try {
    // 从 sessionStorage 获取 authToken
    const authToken = sessionStorage.getItem('authToken');

    const response = await fetch(`${GATEWAY_URL}/api/operationLogs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authToken ? { 'authToken': authToken } : {}),
      },
      body: JSON.stringify(log),
    });

    if (!response.ok) {
      console.error('添加操作记录失败:', response.statusText);
      // 返回一个临时的本地日志对象
      return {
        id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date().toISOString(),
        ...log,
      };
    }

    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error('添加操作记录失败:', error);
    // 返回一个临时的本地日志对象
    return {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      ...log,
    };
  }
}

/**
 * 获取所有操作记录
 */
export async function getOperationLogs(): Promise<OperationLog[]> {
  try {
    const response = await fetch(`${GATEWAY_URL}/api/operationLogs`);

    if (!response.ok) {
      console.error('获取操作记录失败:', response.statusText);
      return [];
    }

    const result = await response.json();
    return result.data?.logs || [];
  } catch (error) {
    console.error('获取操作记录失败:', error);
    return [];
  }
}

/**
 * 获取最近N条操作记录
 */
export async function getRecentOperationLogs(limit: number = 5): Promise<OperationLog[]> {
  try {
    const response = await fetch(`${GATEWAY_URL}/api/operationLogs?limit=${limit}`);

    if (!response.ok) {
      console.error('获取操作记录失败:', response.statusText);
      return [];
    }

    const result = await response.json();
    return result.data?.logs || [];
  } catch (error) {
    console.error('获取操作记录失败:', error);
    return [];
  }
}

/**
 * 清理过期操作记录（超过指定天数）
 * 注意：此功能需要后端支持，目前暂不实现
 */
export async function cleanupOldOperationLogs(daysToKeep: number = 90): Promise<number> {
  console.warn('cleanupOldOperationLogs 暂未实现');
  return 0;
}

/**
 * 清空所有操作记录
 */
export async function clearAllOperationLogs(): Promise<void> {
  try {
    const response = await fetch(`${GATEWAY_URL}/api/operationLogs`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      console.error('清空操作记录失败:', response.statusText);
      throw new Error('清空操作记录失败');
    }
  } catch (error) {
    console.error('清空操作记录失败:', error);
    throw error;
  }
}

/**
 * 删除指定ID的操作记录
 * 注意：此功能需要后端支持，目前暂不实现
 */
export async function deleteOperationLog(id: string): Promise<boolean> {
  console.warn('deleteOperationLog 暂未实现');
  return false;
}
