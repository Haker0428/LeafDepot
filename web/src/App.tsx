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
import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import InventoryStart from "./pages/InventoryStart";
import InventoryProgress from "./pages/InventoryProgress";
import UserManage from "./pages/UserManage";
import History from "./pages/History";
import HistoryDetail from "./pages/HistoryDetail";

import { useAuth } from "./contexts/authContext"; // 导入 useAuth

// 受保护路由组件
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isVerifying } = useAuth(); // 使用 useAuth 钩子

  // token 验证中，不跳转，等待验证结果
  if (isVerifying) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default function App() {
  return (
    // 移除本地的 AuthContext.Provider，应该在 main.tsx 或 index.tsx 中使用 AuthProvider 包装整个应用
    <Routes>
      <Route path="/" element={<Home />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/start"
        element={
          <ProtectedRoute>
            <InventoryStart />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/progress"
        element={
          <ProtectedRoute>
            <InventoryProgress />
          </ProtectedRoute>
        }
      />

      <Route
        path="/user_manage"
        element={
          <ProtectedRoute>
            <UserManage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/inventory/history"
        element={
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        }
      />

      <Route
        path="/inventory/history/:taskId"
        element={
          <ProtectedRoute>
            <HistoryDetail />
          </ProtectedRoute>
        }
      />

      <Route
        path="/other"
        element={
          <div className="text-center text-xl">Other Page - Coming Soon</div>
        }
      />
    </Routes>
  );
}
