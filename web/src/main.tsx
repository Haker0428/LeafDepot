/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-23 23:15:46
 * @FilePath: /Intergration/ui/src/main.tsx
 * @Description: 
 * 
 * Copyright (c) 2025 by lizh, All Rights Reserved. 
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from 'sonner';
import App from "./App.tsx";
import "./index.css";
import React from 'react';
import ReactDOM from 'react-dom/client';
import { AuthProvider } from '@/contexts/authContext'; // 导入 AuthProvider
import 'antd/dist/reset.css';

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider> {/* 在这里使用 AuthProvider */}
        <App />
      </AuthProvider>
      <Toaster />
    </BrowserRouter>
  </StrictMode>
);
