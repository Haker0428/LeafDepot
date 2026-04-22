/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2026-01-22 22:30:13
 * @FilePath: /LeafDepot/web/src/App.tsx
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
import React, { useEffect, useState, useRef } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import InventoryStart from "./pages/InventoryStart";
import InventoryProgress from "./pages/InventoryProgress";
import UserManage from "./pages/UserManage";
import History from "./pages/History";
import HistoryDetail from "./pages/HistoryDetail";

import { useAuth } from "./contexts/authContext";
import { GATEWAY_URL } from "./config/ip_address";

// ==================== 全局任务通知弹窗 ====================

type TaskEventType = "completed" | "partial" | "failed" | "cancelled";

interface TaskNotification {
  eventType: TaskEventType;
  taskNo: string;
  operatorName: string;
}

interface ResumeTask {
  taskNo: string;
  operatorName: string;
  startTime: string;
  totalBins: number;
  completedBins: number;
  isOwnTask: boolean;
  taskStatus: string;
}

function TaskNotifyDialog({ notify, onClose }: { notify: TaskNotification; onClose: () => void }) {
  const isFailed = notify.eventType === "failed";

  const icon = isFailed ? (
    <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    </div>
  ) : (
    <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    </div>
  );

  const title =
    notify.eventType === "partial" ? "任务部分完成" :
    notify.eventType === "failed" ? "任务执行失败" :
    notify.eventType === "cancelled" ? "任务已取消" :
    "任务已完成";

  const content =
    notify.eventType === "partial"
      ? `${notify.taskNo} 部分完成（操作人：${notify.operatorName}）`
      : `${notify.taskNo} 已${notify.eventType === "cancelled" ? "被取消" : (notify.eventType === "failed" ? "失败" : "完成")}（操作人：${notify.operatorName}）`;

  return (
    <div
      style={{
        position: "fixed",
        top: 0, left: 0, right: 0, bottom: 0,
        zIndex: 9999,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          width: 400,
          boxShadow: "0 20px 60px rgba(0,0,0,0.18), 0 4px 12px rgba(0,0,0,0.08)",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          overflow: "hidden",
        }}
      >
        {/* 顶部色条 */}
        <div style={{
          height: 4,
          background: isFailed
            ? "linear-gradient(90deg, #ef4444, #f87171)"
            : "linear-gradient(90deg, #3b82f6, #60a5fa)",
        }} />

        <div style={{ padding: "24px 28px 20px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 16 }}>
            {icon}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#111827", marginBottom: 4 }}>
                {title}
              </div>
              <div style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.5 }}>
                {content}
              </div>
            </div>
          </div>

          <div style={{
            background: isFailed ? "#fef2f2" : "#eff6ff",
            borderRadius: 8,
            padding: "10px 14px",
            marginBottom: 20,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#374151" }}>
              <span style={{ color: "#9ca3af" }}>任务号</span>
              <span style={{ fontFamily: "monospace", fontWeight: 500 }}>{notify.taskNo}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#374151", marginTop: 6 }}>
              <span style={{ color: "#9ca3af" }}>操作人</span>
              <span>{notify.operatorName}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              width: "100%",
              padding: "10px 0",
              background: isFailed
                ? "linear-gradient(135deg, #ef4444, #dc2626)"
                : "linear-gradient(135deg, #3b82f6, #2563eb)",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
              transition: "opacity 0.15s",
            }}
            onMouseOver={e => (e.currentTarget.style.opacity = "0.88")}
            onMouseOut={e => (e.currentTarget.style.opacity = "1")}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== 受保护路由组件 ====================

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isVerifying, userId } = useAuth();
  if (isVerifying) return null;
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
};

// ==================== App 根组件 ====================

export default function App() {
  const [pendingNotify, setPendingNotify] = useState<TaskNotification | null>(null);
  const [resumeTask, setResumeTask] = useState<ResumeTask | null>(null);
  const { userId, authToken } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const isProgressPage = location.pathname === "/inventory/progress";
  // 弹窗显示时暂停轮询，用户点"忽略"后恢复
  const pollingPaused = useRef(false);

  // 1. 每 30 秒轮询一次，检查自己是否有待处理任务
  useEffect(() => {
    if (!authToken || !userId) return;

    const checkRunningTask = async () => {
      if (pollingPaused.current) return;
      try {
        const response = await fetch(`${GATEWAY_URL}/api/inventory/running-task`, {
          headers: { authToken },
        });
        if (response.ok) {
          const result = await response.json();
          if (result.code === 200 && result.data) {
            pollingPaused.current = true; // 弹窗出来后暂停轮询
            setResumeTask({ ...result.data, isOwnTask: true });
          }
        }
      } catch {}
    };

    checkRunningTask(); // 立即查一次
    const intervalId = setInterval(checkRunningTask, 30000);
    return () => clearInterval(intervalId);
  }, [authToken, userId]);

  // 2. WebSocket task_running：其他用户发起任务时弹窗提示（同样暂停轮询）
  // 注意：handler 3 中的 userId 过滤已覆盖此逻辑，此处保留仅用于暂停轮询
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent).detail;
      if (msg.event !== "task_running" || !msg.data?.userId || msg.data.userId === userId) return;
      // 其他用户发起了任务，弹窗提示
      pollingPaused.current = true;
      setResumeTask({
        taskNo: msg.taskNo,
        operatorName: msg.data.userName || "",
        startTime: msg.data.startTime || "",
        totalBins: msg.data.totalBins || 0,
        completedBins: 0,
        isOwnTask: false,
        taskStatus: "running",
      });
    };
    window.addEventListener("remote-task-event", handler as EventListener);
    return () => window.removeEventListener("remote-task-event", handler as EventListener);
  }, [userId]);

  // 全局 WebSocket 连接
  useEffect(() => {
    const wsUrl = GATEWAY_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:") + "/ws";

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => console.log("[WS] 全局连接已建立，等待任务通知...");
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          window.dispatchEvent(new CustomEvent("remote-task-event", { detail: msg }));
        } catch { /* ignore */ }
      };
      ws.onerror = () => console.warn("[WS] 连接错误");
      ws.onclose = () => { reconnectTimer = setTimeout(connect, 3000); };
    };

    connect();
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  // 3. 监听任务完成事件，其他用户任务完成时弹通知（盘点页面不弹）
  useEffect(() => {
    if (isProgressPage) return;
    const handler = (e: Event) => {
      const msg = (e as CustomEvent).detail;
      const { event: eventType, taskNo, data } = msg;
      if (eventType === "task_running") return; // task_running 由 resume 弹窗处理
      if (data?.userId && data.userId === userId) return; // 忽略自己的广播
      setPendingNotify({
        eventType: eventType.replace("task_", "") as TaskEventType,
        taskNo,
        operatorName: data?.operatorName || "未知",
      });
    };
    window.addEventListener("remote-task-event", handler as EventListener);
    return () => window.removeEventListener("remote-task-event", handler as EventListener);
  }, [userId, isProgressPage]);

  // 4. 清空弹窗事件（盘点页面提交任务时调用，防止旧任务完成通知误弹）
  useEffect(() => {
    const clearHandler = () => { setPendingNotify(null); setResumeTask(null); };
    window.addEventListener("clear-task-notify", clearHandler);
    return () => window.removeEventListener("clear-task-notify", clearHandler);
  }, []);

  return (
    <>
      {/* 全局任务通知弹窗（其他用户任务完成） */}
      {pendingNotify && !isProgressPage && (
        <TaskNotifyDialog
          notify={pendingNotify}
          onClose={() => setPendingNotify(null)}
        />
      )}

      {/* 继续盘点弹窗（自己有待处理任务时显示，除盘点页面外所有页面） */}
      {resumeTask && !isProgressPage && (
        <div
          style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 9999, background: "rgba(0,0,0,0.45)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <div style={{ background: "#fff", borderRadius: 12, width: 440, boxShadow: "0 20px 60px rgba(0,0,0,0.18)", fontFamily: "-apple-system, sans-serif", overflow: "hidden" }}>
            <div style={{ height: 4, background: "linear-gradient(90deg, #10b981, #34d399)" }} />
            <div style={{ padding: "24px 28px 20px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 16 }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#ecfdf5", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <svg style={{ width: 20, height: 20, color: "#10b981" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "#111827", marginBottom: 4 }}>
                    {resumeTask.isOwnTask
                      ? resumeTask.taskStatus === "running"
                        ? "您有正在进行的盘点任务"
                        : "您有待确认的盘点任务"
                      : "有用户发起了盘点任务"}
                  </div>
                  <div style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.5 }}>
                    {resumeTask.isOwnTask
                      ? resumeTask.taskStatus === "running"
                        ? "是否继续进行该盘点任务？"
                        : "任务已完成，请确认盘点结果。"
                      : `${resumeTask.operatorName} 发起了一个盘点任务，是否查看？`}
                  </div>
                </div>
              </div>

              <div style={{ background: "#f9fafb", borderRadius: 8, padding: "10px 14px", marginBottom: 20, fontSize: 13, color: "#374151" }}>
                <div style={{ display: "flex", gap: 16, marginBottom: 4 }}>
                  <span style={{ color: "#6b7280", flexShrink: 0 }}>任务号：</span>
                  <span style={{ fontFamily: "monospace", fontWeight: 500 }}>{resumeTask.taskNo}</span>
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ color: "#6b7280", flexShrink: 0 }}>操作人：</span>
                  <span>{resumeTask.operatorName}</span>
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ color: "#6b7280", flexShrink: 0 }}>储位进度：</span>
                  <span>{resumeTask.completedBins} / {resumeTask.totalBins} 个</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
                <button
                  onClick={() => {
                    pollingPaused.current = false; // 恢复轮询
                    setResumeTask(null);
                  }}
                  style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #d1d5db", background: "#fff", color: "#374151", cursor: "pointer", fontSize: 14 }}
                >
                  忽略（30秒后再提示）
                </button>
                <button
                  onClick={() => {
                    navigate("/inventory/progress", {
                      state: {
                        taskNo: resumeTask.taskNo,
                        resumeMode: true,
                        taskStatus: resumeTask.taskStatus,
                      },
                    });
                    setResumeTask(null);
                  }}
                  style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#10b981", color: "#fff", cursor: "pointer", fontSize: 14, fontWeight: 500 }}
                >
                  {resumeTask.taskStatus === "running" ? "继续盘点" : "查看结果"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/inventory/start" element={<ProtectedRoute><InventoryStart /></ProtectedRoute>} />
        <Route path="/inventory/progress" element={<ProtectedRoute><InventoryProgress /></ProtectedRoute>} />
        <Route path="/user_manage" element={<ProtectedRoute><UserManage /></ProtectedRoute>} />
        <Route path="/inventory/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/inventory/history/:taskId" element={<ProtectedRoute><HistoryDetail /></ProtectedRoute>} />
        <Route path="/other" element={<div className="text-center text-xl">Other Page - Coming Soon</div>} />
      </Routes>
    </>
  );
}
