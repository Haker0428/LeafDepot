/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-23 23:15:56
 * @FilePath: /Intergration/ui/src/App.tsx
 * @Description: 
 * 
 * Copyright (c) 2025 by lizh, All Rights Reserved. 
 */
import { Routes, Route, Navigate } from "react-router-dom";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import InventoryStart from "@/pages/InventoryStart";
import InventoryProgress from "@/pages/InventoryProgress";
import { useAuth } from '@/contexts/authContext'; // 导入 useAuth

// 受保护路由组件
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth(); // 使用 useAuth 钩子

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default function App() {
  // 注意：现在认证状态由 AuthProvider 管理，所以这里不再需要本地状态

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
      <Route path="/other" element={<div className="text-center text-xl">Other Page - Coming Soon</div>} />
    </Routes>
  );
}