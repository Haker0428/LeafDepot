/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-08 00:12:30
 * @FilePath: /ui/src/pages/InventoryProgress.tsx
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "@/config/ip_address"; // 导入常量
import { useAuth } from "@/contexts/authContext";

import { v4 as uuidv4 } from "uuid";
import { createTaskGroupData } from "../hooks/taskUtils";
import {
  CreateTaskGroupRequest,
  TaskData,
  TargetRoute,
  ApiResponse,
} from "../hooks/types";

// 定义接口类型
interface InventoryItem {
  id: string;
  productName: string;
  specification: string;
  systemQuantity: number;
  actualQuantity: number | null;
  unit: string;
  locationId: string;
  locationName: string;
  taskNo: string; // 添加任务编号字段
  startTime?: number; // 可选字段
  status?: string; // 可选状态字段
}

interface LocationInfo {
  warehouseId: string;
  warehouseName: string;
  storageAreaId: string;
  storageAreaName: string;
  locationId: string;
  locationName: string;
}

// 盘点任务结构体
interface InventoryTask {
  taskNo: string;
  taskDetailId: string;
  binId: string;
  binDesc: string;
  binCode: string;
  itemId: string;
  itemCode: string;
  itemDesc: string;
  invQty: number;
  qtyUnit: string;
  countQty: number;
  status: string;
}

// 定义任务清单接口
interface TaskManifest {
  id: string;
  name?: string;
  createdAt: string;
  createdTimestamp?: number;
  taskCount: number;
  tasks: InventoryTask[];
  status: string;
  totalItems: number;
  progress?: {
    total: number;
    completed: number;
    pending: number;
    percentage: number;
  };
  statistics?: {
    totalItems: number;
    totalValue: number;
    locations: number;
    products: number;
  };
  metadata?: {
    createdBy: string;
    version: string;
    source: string;
  };
}

// 定义任务状态响应接口
interface TaskStatusResponse {
  success: boolean;
  data: {
    taskNo: string;
    status: string;
    totalTasks: number;
    completedTasks: number;
    progress: number;
    completedItems: Array<{
      taskDetailId: string;
      status: string;
      countedQty: number;
    }>;
  };
  message?: string;
}

// 盘点任务状态
const taskStatus = (status: string) => {
  switch (status) {
    case "1":
      return "未开始";
    case "2":
      return "进行中";
    case "3":
      return "已完成";
    case "4":
      return "异常任务状态";
    default:
      return "未开始";
  }
};

const img_index = 0;

// 新增：格式化时间函数

const formatTime = (milliseconds: number) => {
  const seconds = Math.floor(milliseconds / 1000);

  const minutes = Math.floor(seconds / 60);

  const remainingSeconds = seconds % 60;

  return `${minutes}分${remainingSeconds}秒`;
};

// 新增：计算准确率函数

const calculateAccuracyRate = (
  items: InventoryItem[],
  abnormalTasks: any[]
) => {
  // 计算准确率：准确数量 / 总数量

  const totalItems = items.length;

  const accurateItems = totalItems - abnormalTasks.length;

  return (accurateItems / totalItems) * 100;
};

export default function InventoryProgress() {
  // 统一使用 useAuth 钩子
  const { authToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false); // 为盘点任务添加单独的加载状态

  const navigate = useNavigate();
  const location = useLocation();
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [selectedLocation, setSelectedLocation] = useState<LocationInfo | null>(
    null
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isSaving2LMS, setIsSaving2LMS] = useState(false);

  const [isIssuingTask, setIsIssuingTask] = useState(false); // 下发任务状态
  const [isStartingTask, setIsStartingTask] = useState(false); // 启动任务状态

  const [currentTaskNo, setCurrentTaskNo] = useState<string | null>(null); // 当前任务号
  // const [taskStatus, setTaskStatus] = useState<TaskStatusResponse['data'] | null>(null); // 任务状态

  // 新增状态：任务清单相关
  const [currentTaskManifest, setCurrentTaskManifest] =
    useState<TaskManifest | null>(null);
  const [showTaskDetails, setShowTaskDetails] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);

  // 新增状态：图片显示相关
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [isTaskStarted, setIsTaskStarted] = useState(false); // 任务是否已启动

  const [isTaskCompleted, setIsTaskCompleted] = useState(false); // 任务是否已完成
  const [taskStartTime, setTaskStartTime] = useState<number | null>(null);

  const [imageLoading, setImageLoading] = useState(true);
  const [imageError, setImageError] = useState(false);
  
  // 从后端获取的图片URL
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null); // 原始图片URL
  const [capturedDebugImageUrl, setCapturedDebugImageUrl] = useState<string | null>(null); // debug图片URL
  const [isCapturing, setIsCapturing] = useState(false); // 是否正在抓图
  // 所有抓图按钮共享的task_id索引（从1开始，1-17循环）
  const [captureTaskIdIndex, setCaptureTaskIdIndex] = useState<number>(1);
  // 所有计算按钮共享的task_id索引（从1开始，1-17循环）
  const [calculateTaskIdIndex, setCalculateTaskIdIndex] = useState<number>(1);
  
  // 新增状态：盘点结果统计

  const [isStatisticsModalOpen, setIsStatisticsModalOpen] = useState(false);

  const [statisticsData, setStatisticsData] = useState<{
    totalTime: number;
    accuracyRate: number;
    abnormalTasks: Array<{
      taskNo: string;
      location: string;
      expected: number;
      actual: number;
    }>;
  }>({
    totalTime: 0,
    accuracyRate: 0,
    abnormalTasks: [],
  });

  // 相机设置相关状态

  const [isCameraSettingsOpen, setIsCameraSettingsOpen] = useState(false);

  const [scanCameraConfig, setScanCameraConfig] = useState({
    ip: "192.168.1.100",

    port: "554",

    username: "admin",

    password: "admin123",
  });

  const [captureCameraConfig, setCaptureCameraConfig] = useState({
    ip: "192.168.1.101",

    port: "554",

    username: "admin",

    password: "admin123",
  });

  const [scanCameraStatus, setScanCameraStatus] = useState("disconnected");

  const [captureCameraStatus, setCaptureCameraStatus] =
    useState("disconnected");

  const [scanCameraLoading, setScanCameraLoading] = useState(false);

  const [captureCameraLoading, setCaptureCameraLoading] = useState(false);

  // 在组件内部添加这两个处理函数
  const handleManualCapture = async (taskNo: string, locationName: string, itemId: string) => {
    if (isCapturing) {
      toast.info('正在处理中，请稍候...');
      return;
    }

    setIsCapturing(true);
    setImageLoading(true);
    setImageError(false);

    try {
      // 使用共享的抓图 task_id 索引（从1开始）
      const currentTaskId = captureTaskIdIndex.toString();
      
      console.log(`抓图 - 行ID: ${itemId}, task_id=${currentTaskId}`);

      // 构建原始图片URL（格式: origin/{task_id}.jpg）
      const imageUrl = `/vision/images/original/${currentTaskId}`;
      const fullImageUrl = `${GATEWAY_URL}${imageUrl}`;
      
      // 只设置原始图片URL（上半部分显示）
      setCapturedImageUrl(fullImageUrl);
      
      console.log(`task_id=${currentTaskId} 原始图片URL:`, fullImageUrl);
      toast.success(`显示 task_id=${currentTaskId} 的原始图片`);
      
      // 更新共享的抓图 task_id 索引（1-17循环）
      setCaptureTaskIdIndex(prev => {
        const next = prev + 1;
        return next > 17 ? 1 : next; // 1-17循环
      });
      
    } catch (error: any) {
      console.error('抓图失败:', error);
      toast.error(`抓图失败: ${error?.message || '未知错误'}`);
      setImageError(true);
    } finally {
      setIsCapturing(false);
      setImageLoading(false);
    }
  };

  // 检查图片是否存在
  const checkImageExists = (url: string): Promise<boolean> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = url;
      // 设置超时，避免长时间等待
      setTimeout(() => resolve(false), 2000);
    });
  };

  const handleCalculate = async (taskNo: string, locationName: string, itemId: string) => {
    if (isCapturing) {
      toast.info('正在处理中，请稍候...');
      return;
    }

    setIsCapturing(true);
    setImageLoading(true);
    setImageError(false);

    try {
      // 使用共享的计算 task_id 索引（从1开始）
      const currentTaskId = calculateTaskIdIndex.toString();
      
      console.log(`计算 - 行ID: ${itemId}, task_id=${currentTaskId}`);

      // 构建debug图片URL（格式: debug/{task_id}out.jpg）
      const debugUrl = `/vision/images/debug/${currentTaskId}`;
      const fullDebugUrl = `${GATEWAY_URL}${debugUrl}`;
      
      // 只设置debug图片URL（下半部分显示）
      setCapturedDebugImageUrl(fullDebugUrl);
      
      console.log(`task_id=${currentTaskId} Debug图片URL:`, fullDebugUrl);
      toast.success(`显示 task_id=${currentTaskId} 的debug图片`);
      
      // 更新共享的计算 task_id 索引（1-17循环）
      setCalculateTaskIdIndex(prev => {
        const next = prev + 1;
        return next > 17 ? 1 : next; // 1-17循环
      });
      
    } catch (error: any) {
      console.error('计算失败:', error);
      toast.error(`计算失败: ${error?.message || '未知错误'}`);
      setImageError(true);
    } finally {
      setIsCapturing(false);
      setImageLoading(false);
    }
  };

  // 处理相机登录
  const handleCameraLogin = async (cameraType: "scan" | "capture") => {
    try {
      const config =
        cameraType === "scan" ? scanCameraConfig : captureCameraConfig;

      // 根据相机类型设置对应的加载状态

      if (cameraType === "scan") {
        setScanCameraLoading(true);
      } else {
        setCaptureCameraLoading(true);
      }

      // 模拟API延迟

      await new Promise((resolve) => setTimeout(resolve, 1000));

      // 模拟登录成功（这里可以添加实际的验证逻辑）

      if (cameraType === "scan") {
        setScanCameraStatus("connected");

        toast.success("扫码相机连接成功");
      } else {
        setCaptureCameraStatus("connected");

        toast.success("抓图相机连接成功");
      }
    } catch (error: any) {
      console.error(`相机登录失败:`, error);

      toast.error(`相机连接失败: ${error?.message || "未知错误"}`);

      // 登录失败时重置状态

      if (cameraType === "scan") {
        setScanCameraStatus("disconnected");
      } else {
        setCaptureCameraStatus("disconnected");
      }
    } finally {
      // 根据相机类型重置对应的加载状态

      if (cameraType === "scan") {
        setScanCameraLoading(false);
      } else {
        setCaptureCameraLoading(false);
      }
    }
  };

  // 图片加载处理
  const handleImageLoad = () => {
    setImageLoading(false);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageLoading(false);
    setImageError(true);
  };

  // 添加新的状态来跟踪当前正在执行的任务索引
  const [currentExecutingTaskIndex, setCurrentExecutingTaskIndex] = useState<
    number | null
  >(null);

  // 使用 useEffect 来同步图片显示
  useEffect(() => {
    // 当用户手动选择行时，同步更新图片索引
    if (selectedRowIndex !== null) {
      setCurrentImageIndex(selectedRowIndex);
    }
  }, [selectedRowIndex]);

  // 占位符图片数组（当没有从后端获取到图片时使用）
  const taskImages = [
    "https://via.placeholder.com/800x600/4CAF50/FFFFFF?text=等待抓图",
    "https://via.placeholder.com/800x600/2196F3/FFFFFF?text=等待抓图",
  ];

  // 修改模拟盘点任务函数，添加失败概率

  // 修改模拟盘点任务函数
  const simulateCountingTask = async () => {
    // 记录开始时间
    const startTime = Date.now();
    setTaskStartTime(startTime);

    if (!inventoryItems || inventoryItems.length === 0) {
      return;
    }

    // 用于记录异常任务
    const abnormalTasks = [];

    for (let i = 0; i < inventoryItems.length; i++) {
      // 关键修改：同步更新当前执行的任务索引和图片索引
      setCurrentExecutingTaskIndex(i);
      setCurrentImageIndex(i % taskImages.length); // 确保不超出图片数组范围

      // 更精确的20-30秒随机延迟 (20000-30000毫秒)
      const delay = 20000 + Math.floor(Math.random() * 10000); // 20-30秒范围
      await new Promise((resolve) => setTimeout(resolve, delay));

      // 添加失败概率（二十分之一，5%）
      // const isFailed = Math.random() < 0.05;
      const isFailed = false;
      let actualQuantity = inventoryItems[i].systemQuantity; // 默认等于系统数量

      if (isFailed) {
        // 模拟失败，实际数量为随机值（在系统数量的80%-120%范围内）
        const variation = 0.2; // 20%的差异
        const minQuantity = Math.floor(
          inventoryItems[i].systemQuantity * (1 - variation)
        );
        const maxQuantity = Math.floor(
          inventoryItems[i].systemQuantity * (1 + variation)
        );
        actualQuantity =
          Math.floor(Math.random() * (maxQuantity - minQuantity + 1)) +
          minQuantity;

        // 记录异常任务
        abnormalTasks.push({
          taskNo: inventoryItems[i].taskNo,
          location: inventoryItems[i].specification,
          expected: inventoryItems[i].systemQuantity,
          actual: actualQuantity,
        });

        // 显示异常toast
        toast.error(
          `任务 ${i + 1} 异常: 预期 ${
            inventoryItems[i].systemQuantity
          }，实际 ${actualQuantity}`
        );
      } else {
        // 显示成功toast
        toast.success(`任务 ${i + 1} 完成: 数量 ${actualQuantity}`);
      }

      // 使用函数式更新确保状态一致性
      setInventoryItems((prevItems) => {
        const newItems = [...prevItems];
        newItems[i] = {
          ...newItems[i],
          actualQuantity,
          status: isFailed ? "abnormal" : "completed", // 添加状态字段
        };

        // 计算进度
        const completedCount = newItems.filter(
          (item) => item.actualQuantity !== null
        ).length;
        const newProgress = (completedCount / newItems.length) * 100;
        setProgress(Math.min(Math.round(newProgress), 100));

        return newItems;
      });
    }

    // 任务完成后重置执行索引
    setCurrentExecutingTaskIndex(null);
    setIsTaskCompleted(true);

    // 计算总时间
    const totalTime = Date.now() - startTime;
    // 计算准确率
    const accuracyRate = calculateAccuracyRate(inventoryItems, abnormalTasks);

    // 保存统计信息
    setStatisticsData({
      totalTime,
      accuracyRate,
      abnormalTasks,
    });

    // 最终完成提示
    if (abnormalTasks.length > 0) {
      toast.warning(`盘点完成！发现 ${abnormalTasks.length} 个异常任务`);
    } else {
      toast.success("盘点完成！所有任务执行成功");
    }
  };

  // 新增：处理盘点结果统计

  // 修改统计函数

  const handleInventoryStatistics = () => {
    toast.info("盘点数据统计");

    // 检查是否已经计算过统计（使用更可靠的方式）
    if (
      statisticsData.totalTime !== undefined &&
      statisticsData.totalTime >= 0
    ) {
      setIsStatisticsModalOpen(true);
      return;
    }

    // 处理空数据情况
    if (!inventoryItems || inventoryItems.length === 0) {
      toast.error("没有盘点数据可供统计");
      return;
    }

    // 计算异常任务（添加空值检查）
    const abnormalTasks = inventoryItems
      .filter(
        (item) =>
          item.actualQuantity !== null &&
          item.actualQuantity !== undefined &&
          item.systemQuantity !== undefined &&
          item.actualQuantity !== item.systemQuantity
      )
      .map((item) => ({
        taskNo: item.taskNo,
        location: item.locationName || item.specification,
        expected: item.systemQuantity,
        actual: item.actualQuantity as number, // 已经过滤了null，可以断言为number
      }));

    // 计算准确率 - 修正：使用实际的完成数量
    const completedItems = inventoryItems.filter(
      (item) => item.actualQuantity !== null
    );
    const totalItems = completedItems.length;
    const accurateItems = totalItems - abnormalTasks.length;
    const accuracyRate =
      totalItems > 0 ? (accurateItems / totalItems) * 100 : 0;

    // 使用专门记录的开始时间
    const totalTime = Date.now() - (taskStartTime || Date.now());

    // 更新统计信息
    setStatisticsData({
      totalTime,
      accuracyRate,
      abnormalTasks,
    });

    // 打开模态框
    setIsStatisticsModalOpen(true);
  };

  // 从本地存储获取任务清单并初始化盘点数据
  useEffect(() => {
    const loadTaskManifest = () => {
      try {
        const manifestData = localStorage.getItem("currentTaskManifest");
        if (manifestData) {
          const manifest: TaskManifest = JSON.parse(manifestData);
          setCurrentTaskManifest(manifest);

          // 如果任务清单中有任务，设置第一个任务的taskNo
          if (manifest.tasks.length > 0) {
            setCurrentTaskNo(manifest.tasks[0].taskNo);
          }

          // 根据任务清单初始化盘点数据
          const inventoryData: InventoryItem[] = manifest.tasks.map(
            (task) => ({
              id: task.taskDetailId,
              productName: task.itemDesc || task.taskNo,
              specification: task.binDesc,
              systemQuantity: task.invQty,
              actualQuantity: null, // 初始状态下实际数量为空
              unit: task.qtyUnit,
              locationId: task.binId,
              locationName: task.binDesc,
              taskNo: task.taskNo, // 保存任务编号
              startTime: Date.now(), // 添加开始时间
            })
          );

          setInventoryItems(inventoryData);
          toast.success(`已加载任务清单，包含 ${manifest.tasks.length} 个任务`);
        }
      } catch (error: any) {
        console.error("加载任务清单失败:", error);
      }
    };

    loadTaskManifest();
  }, []);

  // 在组件中添加这个 useEffect
  useEffect(() => {
    const handleImageError = () => {
      const imageContainer = document.querySelector(
        ".relative.w-full.h-full.max-w-md.mx-auto"
      );
      if (imageContainer) {
        const img = imageContainer.querySelector("img");
        const errorDiv = imageContainer.querySelector(".hidden.flex-col");

        if (img && errorDiv) {
          // 检查图片是否自然宽度为0（表示加载失败）
          if (img.naturalWidth === 0) {
            img.style.display = "none";
            errorDiv.classList.remove("hidden");
            errorDiv.classList.add("flex");
          } else {
            img.style.display = "block";
            errorDiv.classList.add("hidden");
            errorDiv.classList.remove("flex");
          }
        }
      }
    };

    // 添加全局错误监听
    const images = document.querySelectorAll("img");
    images.forEach((img) => {
      img.addEventListener("error", handleImageError);
      img.addEventListener("load", handleImageError);
    });

    // 初始检查
    handleImageError();

    return () => {
      images.forEach((img) => {
        img.removeEventListener("error", handleImageError);
        img.removeEventListener("load", handleImageError);
      });
    };
  }, [currentImageIndex, isTaskStarted]);

  // 在启动盘点任务时设置

  const handleStartCountingTask = async () => {
    setIsStartingTask(true);
    try {
      // 记录任务开始时间
      const startTime = Date.now();
      setTaskStartTime(startTime);

      // 重置执行索引
      setCurrentExecutingTaskIndex(null);

      // 模拟启动任务
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // 启动模拟盘点任务
      await simulateCountingTask();

      setIsTaskStarted(true);
      setIsTaskCompleted(true);
      toast.success(`盘点任务启动成功`);
    } catch (error: any) {
      console.error("启动任务失败:", error);
      toast.error(`启动任务失败: ${error?.message || "未知错误"}`);
    } finally {
      setIsStartingTask(false);
    }
  };

  // 下发盘点任务
  const handleIssueCountingTask = async () => {
    // 演示，后续修改
    toast.success(`任务清单下发成功`);

    if (!currentTaskManifest || currentTaskManifest.tasks.length === 0) {
      toast.error("没有可下发的任务清单");
      return;
    }

    if (!currentTaskNo) {
      toast.error("无法获取任务号");
      return;
    }

    try {
      // 生成任务组数据
      // const taskGroupData: CreateTaskGroupRequest = createTaskGroupData();

      // 将 currentTaskManifest 中的任务转换为 RCS 任务组格式
      const taskData: TaskData[] = currentTaskManifest.tasks.map(
        (task, index) => ({
          robotTaskCode: task.taskNo, // 使用 manifest 中的 taskNo
          sequence: index + 1, // 按顺序编号
        })
      );

      // 目标路由
      const targetRoute: TargetRoute = {
        type: "ZONE",
        code: "A3",
      };

      const taskGroupRequest: CreateTaskGroupRequest = {
        groupCode: currentTaskManifest.id,
        strategy: "GROUP_SEQ",
        strategyValue: "1", // 组间及组内都有序
        groupSeq: 10,
        targetRoute: targetRoute,
        data: taskData,
      };

      console.log(
        "发送的任务组数据:",
        JSON.stringify(taskGroupRequest, null, 2)
      );

      // 调用网关接口
      const result = await fetch(`${GATEWAY_URL}/rcs/controller/task/group`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-lr-request-id": uuidv4(),
          "x-lr-trace-id": uuidv4(),
        },
        body: JSON.stringify(taskGroupRequest),
      });

      const responseData: ApiResponse = await result.json();
      setResponse(responseData);

      if (responseData.code === "SUCCESS") {
        toast.success(`任务清单下发成功`);

        console.log("任务清单下发成功");
      } else {
        console.warn("任务组下发返回业务异常:", responseData.message);
      }
    } catch (error: any) {
      console.error("下发任务清单失败:", error);
      toast.error(`任务清单下发失败: ${error?.message || "未知错误"}`);
    } finally {
      setIsIssuingTask(false);
    }
  };

  // 轮询任务状态
  const startPollingTaskStatus = () => {
    if (!currentTaskNo) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(
          `${GATEWAY_URL}/rcs/task-progress/${currentTaskNo}`,
          {
            method: "GET",
            headers: {
              authToken: authToken || "",
            },
          }
        );

        if (response.ok) {
          const result: TaskStatusResponse = await response.json();
          if (result.success && result.data) {
            // setTaskStatus(result.data);

            // 更新进度
            setProgress(result.data.progress);

            // 如果任务完成，停止轮询
            if (
              result.data.status === "COMPLETED" ||
              result.data.progress >= 100
            ) {
              clearInterval(pollInterval);
              toast.success("盘点任务已完成");
            }
          }
        }
      } catch (error: any) {
        console.error("获取任务状态失败:", error);
      }
    }, 3000); // 每3秒轮询一次

    // 10分钟后停止轮询
    setTimeout(() => {
      clearInterval(pollInterval);
    }, 10 * 60 * 1000);
  };

  // 处理实际数量输入变化
  const handleActualQuantityChange = (id: string, value: string) => {
    const numericValue = value ? parseInt(value, 10) : null;

    setInventoryItems((prevItems) =>
      prevItems.map((item) =>
        item.id === id ? { ...item, actualQuantity: numericValue } : item
      )
    );

    // 更新进度 - 每完成一个项目增加进度
    const completedCount = inventoryItems.filter(
      (item) =>
        item.actualQuantity !== null &&
        (item.id !== id || numericValue !== null)
    ).length;

    const newProgress = (completedCount / inventoryItems.length) * 100;
    setProgress(Math.min(Math.round(newProgress), 100));
  };

  // 处理行点击事件

  const handleRowClick = (index: number) => {
    if (!isTaskStarted) {
      toast.info("请先启动盘点任务");
      return;
    }
    setSelectedRowIndex(index);
    // 立即更新当前执行的任务索引，触发 useEffect 同步更新图片
    setCurrentExecutingTaskIndex(index);
  };

  // 保存盘点结果到LMS
  const handleSaveInventoryToLMS = async () => {
    if (isSaving2LMS) return;
    try {
      setIsSaving2LMS(true);

      // 获取盘点结果数据 - 从任务清单中获取
      const inventoryResults = inventoryItems
        .filter((item) => item.actualQuantity !== null)
        .map((item) => ({
          taskDetailId: item.id,
          itemId: item.id.replace("INV", "ITEM"), // 简单转换，实际应根据数据结构调整
          countQty: item.actualQuantity || 0,
        }));

      if (inventoryResults.length === 0) {
        toast.error("请先完成盘点数据录入");
        return;
      }

      const response = await fetch(`${GATEWAY_URL}/lms/setTaskResults`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          authToken: authToken || "",
        },
        body: JSON.stringify(inventoryResults),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          toast.success("盘点结果已成功上传至LMS");
          setProgress(100);

          // 更新任务状态
          if (currentTaskNo) {
            startPollingTaskStatus();
          }
        } else {
          throw new Error(result.message || "上传失败");
        }
      } else {
        const errorText = await response.text();
        throw new Error(`LMS上传失败: ${errorText}`);
      }
    } catch (error: any) {
      console.error("上传盘点结果失败:", error);
      toast.error(`上传失败: ${error?.message || "未知错误"}`);
    } finally {
      setIsSaving2LMS(false);
    }
  };

  // 处理保存盘点结果
  const handleSaveInventory = () => {
    // 检查是否所有项目都已输入实际数量
    const incompleteItems = inventoryItems.filter(
      (item) => item.actualQuantity === null
    );

    if (incompleteItems.length > 0) {
      toast.warning(
        `尚有 ${incompleteItems.length} 项未完成盘点，请完成后再保存`
      );
      return;
    }

    setIsSaving(true);

    // 模拟保存请求
    setTimeout(() => {
      setIsSaving(false);
      toast.success("盘点结果保存成功！");
    }, 1500);
  };

  // 处理返回按钮
  const handleBack = () => {
    navigate("/inventory/start");
  };

  // 修改任务详情显示/隐藏的处理函数
  const handleShowTaskDetails = () => {
    setShowTaskDetails(!showTaskDetails);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* 背景图片 */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-5"
        style={{
          backgroundImage:
            "url(https://lf-code-agent.coze.cn/obj/x-ai-cn/attachment/3868529628819536/背景参考_20250808011802.jfif)",
        }}
      ></div>

      {/* 顶部导航栏 */}
      <header className="relative bg-white shadow-md z-10">
        <div className="container mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-green-700 rounded-full flex items-center justify-center">
              <i className="fa-solid fa-boxes-stacked text-white text-xl"></i>
            </div>
            <div>
              <h1 className="text-xl font-bold text-green-800">中国烟草</h1>
              <p className="text-xs text-gray-500">智慧仓库盘点系统</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleBack}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-arrow-left mr-2"></i>返回
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 - 修改网格布局 */}
      {/* 主内容区 - 修改网格布局 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-green-800 flex items-center">
            盘点任务
          </h2>
        </div>

        {/* 统一的网格容器，使用4列布局：左侧3列，右侧1列 */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* 左侧内容区域 - 占据3列 */}
          <div className="lg:col-span-3 flex flex-col gap-8">
            {/* 盘点进度区域 - 占据上半部分 */}
            <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center space-x-4">
                  <h3 className="text-xl font-bold text-green-800 flex items-center">
                    <i className="fa-solid fa-chart-line mr-2 text-green-600"></i>
                    盘点进度
                  </h3>
                </div>
                <span className="text-2xl font-bold text-green-700 flex items-center">
                  {progress}%
                </span>
              </div>

              {/* 进度条 */}
              <div className="w-full bg-gray-200 rounded-full h-4 mb-6 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-green-500 to-green-700 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                ></motion.div>
              </div>

              {/* 操作按钮区域 */}
              <div className="flex justify-end space-x-4 mt-6 pt-4 border-t border-gray-200">
                {/* 按钮内容保持不变 */}
                <button
                  onClick={() => setIsCameraSettingsOpen(true)}
                  className={`bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg transition-all flex items-center disabled:bg-orange-400 ${
                    scanCameraStatus === "connected" &&
                    captureCameraStatus === "connected"
                      ? "bg-green-500 hover:bg-green-600 text-white"
                      : "mr-2 hover:mr-2 text-white"
                  }`}
                  title="相机设置"
                >
                  <i className="fa-solid fa-camera mr-1.5 text-sm"></i>
                  <span className="text-sm font-medium">相机设置</span>
                </button>

                {currentTaskManifest && (
                  <button
                    onClick={handleIssueCountingTask}
                    disabled={isIssuingTask}
                    className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg transition-all flex items-center disabled:bg-orange-400"
                  >
                    {isIssuingTask ? (
                      <>
                        <i className="fas fa-spinner fa-spin mr-2"></i>下发中...
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-play mr-2"></i>
                        下发盘点任务清单
                      </>
                    )}
                  </button>
                )}

                {currentTaskManifest && (
                  <button
                    onClick={handleStartCountingTask}
                    disabled={isStartingTask || isTaskStarted}
                    className={`px-4 py-2 rounded-lg transition-all flex items-center ${
                      isTaskStarted
                        ? "bg-green-600 text-white cursor-default"
                        : isStartingTask
                        ? "bg-orange-400 text-white cursor-not-allowed"
                        : "bg-orange-600 hover:bg-orange-700 text-white"
                    }`}
                  >
                    {isStartingTask ? (
                      <>
                        <i className="fas fa-spinner fa-spin mr-2"></i>启动中...
                      </>
                    ) : isTaskStarted ? (
                      <>
                        <i className="fa-solid fa-check mr-2"></i>任务已启动
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-play mr-2"></i>启动盘点任务
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* 任务详情表格显示区域（如果显示） */}
            {showTaskDetails && currentTaskManifest && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="bg-white rounded-xl shadow-md p-6 border border-gray-100"
              >
                {/* 任务详情内容保持不变 */}
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-bold text-green-800 flex items-center">
                    <i className="fa-solid fa-clipboard-list mr-2 text-green-600"></i>
                    盘点任务详情
                  </h3>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-500">
                      任务数量: {currentTaskManifest.taskCount} 个
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          序号
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          任务编号
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          盘点库位
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          历史库存数量
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          单位
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          状态
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {currentTaskManifest?.tasks?.map((task, index) => {
                        if (!task || !task.taskDetailId) {
                          console.warn("发现无效的任务数据:", task);
                          return null;
                        }
                        return (
                          <tr
                            key={task.taskDetailId}
                            className="hover:bg-gray-50 transition-colors"
                          >
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                              {index + 1}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {task.taskNo || "未知任务编号"}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                              <div>
                                <div className="font-medium">
                                  {task.binDesc || "未知库位"}
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-medium">
                              {task.invQty || 0}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                              {task.qtyUnit || "箱"}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {taskStatus(task.status) || "未知状态"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}

            {/* 盘点数据区域 - 占据下半部分，与上半部分等宽 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="bg-white rounded-xl shadow-md border border-gray-100 flex flex-col"
            >
              <div className="p-6 border-b border-gray-100">
                <h3 className="text-xl font-bold text-green-800">
                  <i className="fa-solid fa-table mr-2 text-green-600"></i>
                  盘点数据
                </h3>
              </div>

              {/* 表格区域 */}
              <div className="flex-1 p-6">
                {inventoryItems.length > 0 ? (
                  <div className="h-[400px] overflow-y-auto overflow-x-auto border border-gray-200 rounded-lg">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0 z-10">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            序号
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            任务编号
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            卷烟名称
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            货位名称
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            系统库存
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            实际库存
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            差异
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            手动抓图
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            计算
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryItems.map((item, index) => {
                          const difference =
                            item.actualQuantity !== null
                              ? item.actualQuantity - item.systemQuantity
                              : null;
                          const hasDifference =
                            difference !== null && difference !== 0;
                          const isSelected = selectedRowIndex === index;

                          return (
                            <tr
                              key={item.id}
                              className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                                isSelected
                                  ? "bg-blue-50 border-l-4 border-blue-500"
                                  : ""
                              }`}
                              onClick={() => handleRowClick(index)}
                            >
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {index + 1}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                  <div className="text-sm font-medium text-gray-900">
                                    {item.taskNo}
                                  </div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.productName}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.specification}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.systemQuantity}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <input
                                  type="number"
                                  min="0"
                                  value={item.actualQuantity || ""}
                                  onChange={(e) =>
                                    handleActualQuantityChange(
                                      item.id,
                                      e.target.value
                                    )
                                  }
                                  className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                                  placeholder="输入数量"
                                  disabled={!isTaskStarted}
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {difference !== null ? (
                                  <span
                                    className={`text-sm font-medium ${
                                      hasDifference
                                        ? "text-red-600"
                                        : "text-green-600"
                                    }`}
                                  >
                                    {hasDifference ? (
                                      <>
                                        <i className="fa-solid fa-exclamation-circle mr-1"></i>
                                        {difference > 0
                                          ? `+${difference}`
                                          : difference}
                                      </>
                                    ) : (
                                      <>
                                        <i className="fa-solid fa-check-circle mr-1"></i>
                                        一致
                                      </>
                                    )}
                                  </span>
                                ) : (
                                  <span className="text-sm text-gray-400">
                                    待输入
                                  </span>
                                )}
                              </td>

                              {/* 手动抓图按钮列 */}
                              <td className="px-4 py-3 whitespace-nowrap">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation(); // 阻止事件冒泡，防止触发行点击
                                    handleManualCapture(
                                      item.taskNo,
                                      item.specification,
                                      item.id // 传递item.id用于独立索引
                                    );
                                  }}
                                  disabled={isCapturing}
                                  className={`px-3 py-1 rounded transition-colors flex items-center justify-center w-full ${
                                    isCapturing
                                      ? "bg-gray-400 cursor-not-allowed text-white"
                                      : "bg-blue-600 hover:bg-blue-700 text-white"
                                  }`}
                                  title="手动抓取当前货位图像（每次点击循环显示task_id 0-17）"
                                >
                                  {isCapturing ? (
                                    <>
                                      <i className="fas fa-spinner fa-spin mr-1 text-sm"></i>
                                      <span className="text-xs">加载中...</span>
                                    </>
                                  ) : (
                                    <>
                                      <i className="fa-solid fa-camera mr-1 text-sm"></i>
                                      <span className="text-xs">抓图</span>
                                    </>
                                  )}
                                </button>
                              </td>

                              {/* 计算按钮列 */}
                              <td className="px-4 py-3 whitespace-nowrap">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation(); // 阻止事件冒泡，防止触发行点击
                                    handleCalculate(
                                      item.taskNo,
                                      item.specification,
                                      item.id // 传递item.id用于独立索引
                                    );
                                  }}
                                  disabled={isCapturing}
                                  className={`px-3 py-1 rounded transition-colors flex items-center justify-center w-full ${
                                    isCapturing
                                      ? "bg-gray-400 cursor-not-allowed text-white"
                                      : "bg-green-600 hover:bg-green-700 text-white"
                                  }`}
                                  title="显示debug图片（每次点击循环显示task_id 0-17）"
                                >
                                  {isCapturing ? (
                                    <>
                                      <i className="fas fa-spinner fa-spin mr-1 text-sm"></i>
                                      <span className="text-xs">加载中...</span>
                                    </>
                                  ) : (
                                    <>
                                      <i className="fa-solid fa-calculator mr-1 text-sm"></i>
                                      <span className="text-xs">计算</span>
                                    </>
                                  )}
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-[600px] text-center p-8 border border-gray-200 rounded-lg">
                    <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                      <i className="fa-solid fa-box-open text-gray-400 text-4xl"></i>
                    </div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      暂无盘点数据
                    </h4>
                    <p className="text-gray-500 max-w-md">
                      请在"开始盘点"页面生成任务清单后进入此页面
                    </p>
                  </div>
                )}
              </div>

              {/* 底部操作栏 */}
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-4">
                <button
                  onClick={handleInventoryStatistics}
                  disabled={!isTaskCompleted}
                  className={`px-6 py-3 rounded-lg transition-colors flex items-center ${
                    !isTaskCompleted
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-blue-700 hover:bg-blue-800 text-white"
                  }`}
                >
                  <i className="fa-solid fa-chart-pie mr-2"></i>
                  盘点结果统计
                </button>
                <button
                  onClick={handleSaveInventory}
                  disabled={isSaving}
                  className={`px-6 py-3 rounded-lg transition-colors flex items-center ${
                    !isTaskCompleted
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-green-700 hover:bg-green-800 text-white"
                  }`}
                >
                  {isSaving ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      保存中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-save mr-2"></i>
                      完成盘点并保存结果
                    </>
                  )}
                </button>
                <button
                  onClick={handleSaveInventoryToLMS}
                  disabled={isSaving2LMS}
                  className={`px-6 py-3 rounded-lg transition-colors flex items-center ${
                    !isTaskCompleted
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-green-700 hover:bg-green-800 text-white"
                  }`}
                >
                  {isSaving2LMS ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      上传中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-save mr-2"></i>
                      上传盘点结果至LMS
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </div>

          {/* 右侧观察窗口 - 占据1列，内部上下显示两张图片 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="lg:col-span-1"
          >
            <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
              <div className="p-6 border-b border-gray-100">
                <h3 className="text-xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-eye mr-2 text-green-600"></i>
                  观察窗口
                </h3>
              </div>

              {/* 观察窗口内容 - 上下显示两张图片 */}
              <div className="flex-1 p-4 flex flex-col gap-4">
                {/* 上半部分 - 原始图片（优先显示抓取的图片） */}
                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
                    {isCapturing ? (
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700 mb-2"></div>
                        <p className="text-gray-500 text-sm">正在抓图...</p>
                      </div>
                    ) : capturedImageUrl ? (
                      <>
                        <img
                          src={capturedImageUrl}
                          alt="抓取的原始图片"
                          className={`max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 transition-opacity duration-300 ${
                            imageLoading ? "opacity-0" : "opacity-100"
                          }`}
                          onLoad={handleImageLoad}
                          onError={handleImageError}
                        />
                        {imageLoading && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
                          </div>
                        )}
                        {imageError && (
                          <div className="absolute inset-0 flex items-center justify-center bg-red-50">
                            <div className="text-center text-red-600">
                              <i className="fa-solid fa-exclamation-triangle text-2xl mb-2"></i>
                              <p className="text-sm">图片加载失败</p>
                            </div>
                          </div>
                        )}
                        <div className="absolute bottom-2 right-2 bg-green-700 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center">
                          <i className="fa-solid fa-circle text-green-400 mr-1 animate-pulse"></i>
                          <span>原始图片</span>
                        </div>
                      </>
                    ) : isTaskStarted ? (
                      <>
                        <img
                          src={taskImages[currentImageIndex % taskImages.length]}
                          alt={`上部观察窗口 - 任务 ${currentImageIndex + 1}`}
                          className={`max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 transition-opacity duration-300 ${
                            imageLoading ? "opacity-0" : "opacity-100"
                          }`}
                          onLoad={handleImageLoad}
                          onError={handleImageError}
                        />
                        {imageLoading && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
                          </div>
                        )}
                        <div className="absolute bottom-2 right-2 bg-green-700 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center">
                          <i className="fa-solid fa-circle text-green-400 mr-1 animate-pulse"></i>
                          <span>实时画面 1</span>
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                          <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                        </div>
                        <p className="text-gray-500 text-sm">画面1未连接</p>
                        <p className="text-gray-400 text-xs mt-1">点击"抓图"按钮获取图片</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 下半部分 - Debug图片（优先显示抓取的debug图片） */}
                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
                    {isCapturing ? (
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mb-2"></div>
                        <p className="text-gray-500 text-sm">正在处理...</p>
                      </div>
                    ) : capturedDebugImageUrl ? (
                      <>
                        <img
                          src={capturedDebugImageUrl}
                          alt="抓取的调试图片"
                          className={`max-w-full max-h-full object-contain rounded-lg border-2 border-blue-700 transition-opacity duration-300 ${
                            imageLoading ? "opacity-0" : "opacity-100"
                          }`}
                          onLoad={handleImageLoad}
                          onError={handleImageError}
                        />
                        {imageLoading && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
                          </div>
                        )}
                        {imageError && (
                          <div className="absolute inset-0 flex items-center justify-center bg-red-50">
                            <div className="text-center text-red-600">
                              <i className="fa-solid fa-exclamation-triangle text-2xl mb-2"></i>
                              <p className="text-sm">图片加载失败</p>
                            </div>
                          </div>
                        )}
                        <div className="absolute bottom-2 right-2 bg-blue-700 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center">
                          <i className="fa-solid fa-circle text-blue-400 mr-1 animate-pulse"></i>
                          <span>调试图片</span>
                        </div>
                      </>
                    ) : isTaskStarted ? (
                      <>
                        <img
                          src={taskImages[(currentImageIndex + 1) % taskImages.length]}
                          alt={`下部观察窗口 - 任务 ${currentImageIndex + 2}`}
                          className={`max-w-full max-h-full object-contain rounded-lg border-2 border-blue-700 transition-opacity duration-300 ${
                            imageLoading ? "opacity-0" : "opacity-100"
                          }`}
                          onLoad={handleImageLoad}
                          onError={handleImageError}
                        />
                        {imageLoading && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
                          </div>
                        )}
                        <div className="absolute bottom-2 right-2 bg-blue-700 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center">
                          <i className="fa-solid fa-circle text-blue-400 mr-1 animate-pulse"></i>
                          <span>实时画面 2</span>
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                          <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                        </div>
                        <p className="text-gray-500 text-sm">画面2未连接</p>
                        <p className="text-gray-400 text-xs mt-1">点击"抓图"按钮获取图片</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* 底部控制区域 */}
              <div className="p-4 border-t border-gray-100 flex justify-center space-x-3 bg-gray-50">
                {isTaskStarted && (
                  <>
                    <button
                      className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors flex items-center justify-center"
                      onClick={() => setCurrentImageIndex((prev) => prev - 1)}
                      disabled={currentImageIndex === 0}
                      aria-label="上一组"
                    >
                      <i className="fa-solid fa-arrow-up text-gray-700 text-lg"></i>
                    </button>
                    <button
                      className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors flex items-center justify-center"
                      onClick={() => setCurrentImageIndex((prev) => prev + 1)}
                      aria-label="下一组"
                    >
                      <i className="fa-solid fa-arrow-down text-gray-700 text-lg"></i>
                    </button>
                    <button
                      className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors flex items-center justify-center"
                      onClick={() => {
                        // 这里可以添加切换两个画面源的逻辑
                        toast.info("画面源切换");
                      }}
                      aria-label="切换画面源"
                    >
                      <i className="fa-solid fa-exchange-alt text-gray-700 text-lg"></i>
                    </button>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* // 在 return 语句中的合适位置添加统计模态框，建议放在主内容区后面，页脚之前 */}

      {/* 盘点结果统计模态框 */}
      {isStatisticsModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4"
          >
            {/* 模态框头部 */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-chart-pie mr-3 text-green-600"></i>
                  盘点结果统计
                </h3>
                <button
                  onClick={() => setIsStatisticsModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <i className="fa-solid fa-times text-xl"></i>
                </button>
              </div>
            </div>

            {/* 模态框内容 */}
            <div className="p-6">
              {/* 统计概览 */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-blue-700">
                    {formatTime(statisticsData.totalTime)}
                  </div>
                  <div className="text-sm text-blue-600 mt-1">总耗时</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-700">
                    {statisticsData.accuracyRate.toFixed(1)}%
                  </div>
                  <div className="text-sm text-green-600 mt-1">准确率</div>
                </div>
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-red-700">
                    {statisticsData.abnormalTasks.length}
                  </div>
                  <div className="text-sm text-red-600 mt-1">异常任务</div>
                </div>
              </div>

              {/* 异常任务列表 */}
              {statisticsData.abnormalTasks.length > 0 ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                    <h4 className="font-semibold text-gray-800 flex items-center">
                      <i className="fa-solid fa-exclamation-triangle text-orange-500 mr-2"></i>
                      异常任务详情
                    </h4>
                  </div>
                  <div className="max-h-60 overflow-y-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                            任务编号
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                            库位
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                            系统数量
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                            实际数量
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                            差异
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {statisticsData.abnormalTasks.map((task, index) => (
                          <tr
                            key={index}
                            className="hover:bg-red-50 transition-colors"
                          >
                            <td className="px-4 py-2 text-sm font-medium text-gray-900">
                              {task.taskNo}
                            </td>
                            <td className="px-4 py-2 text-sm text-gray-700">
                              {task.location}
                            </td>
                            <td className="px-4 py-2 text-sm text-gray-700">
                              {task.expected}
                            </td>
                            <td className="px-4 py-2 text-sm text-gray-700">
                              {task.actual}
                            </td>
                            <td className="px-4 py-2 text-sm font-medium text-red-600">
                              {task.actual - task.expected > 0 ? "+" : ""}
                              {task.actual - task.expected}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 border border-gray-200 rounded-lg bg-green-50">
                  <i className="fa-solid fa-check-circle text-green-500 text-4xl mb-3"></i>
                  <h4 className="text-lg font-medium text-green-800 mb-2">
                    盘点结果完美
                  </h4>
                  <p className="text-green-600">所有任务均无异常，准确率100%</p>
                </div>
              )}

              {/* 总结信息 */}
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-center">
                  <div>
                    <h5 className="font-semibold text-gray-800">盘点总结</h5>
                    <p className="text-sm text-gray-600">
                      共完成 {inventoryItems.length} 个盘点任务
                      {statisticsData.abnormalTasks.length > 0 &&
                        `，其中 ${statisticsData.abnormalTasks.length} 个任务存在差异`}
                    </p>
                  </div>
                  <div className="text-right">
                    <div
                      className={`text-lg font-bold ${
                        statisticsData.accuracyRate >= 95
                          ? "text-green-600"
                          : statisticsData.accuracyRate >= 80
                          ? "text-yellow-600"
                          : "text-red-600"
                      }`}
                    >
                      总体评价:{" "}
                      {statisticsData.accuracyRate >= 95
                        ? "优秀"
                        : statisticsData.accuracyRate >= 80
                        ? "良好"
                        : "需改进"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 模态框底部 */}
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setIsStatisticsModalOpen(false)}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
              >
                <i className="fa-solid fa-check mr-2"></i>确认
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* 相机设置模态框 */}
      {isCameraSettingsOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4"
          >
            {/* 模态框头部 */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-camera mr-3 text-green-600"></i>
                  相机设置
                </h3>
                <button
                  onClick={() => setIsCameraSettingsOpen(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <i className="fa-solid fa-times text-xl"></i>
                </button>
              </div>
            </div>

            {/* 模态框内容 */}
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 扫码相机设置 */}
                <div className="border rounded-lg p-4">
                  <h4 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
                    <i className="fa-solid fa-qrcode mr-2 text-blue-500"></i>
                    扫码相机
                  </h4>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        IP地址
                      </label>
                      <input
                        type="text"
                        value={scanCameraConfig.ip}
                        onChange={(e) =>
                          setScanCameraConfig({
                            ...scanCameraConfig,
                            ip: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="192.168.1.100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        端口号
                      </label>
                      <input
                        type="text"
                        value={scanCameraConfig.port}
                        onChange={(e) =>
                          setScanCameraConfig({
                            ...scanCameraConfig,
                            port: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="554"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        用户名
                      </label>
                      <input
                        type="text"
                        value={scanCameraConfig.username}
                        onChange={(e) =>
                          setScanCameraConfig({
                            ...scanCameraConfig,
                            username: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        密码
                      </label>
                      <input
                        type="password"
                        value={scanCameraConfig.password}
                        onChange={(e) =>
                          setScanCameraConfig({
                            ...scanCameraConfig,
                            password: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      />
                    </div>
                    <button
                      onClick={() => handleCameraLogin("scan")}
                      disabled={scanCameraLoading}
                      className={`w-full py-2 rounded-lg transition-colors flex items-center justify-center ${
                        scanCameraStatus === "connected"
                          ? "bg-green-600 hover:bg-green-700"
                          : "bg-blue-600 hover:bg-blue-700"
                      } text-white`}
                    >
                      {scanCameraLoading ? (
                        <>
                          <i className="fas fa-spinner fa-spin mr-2"></i>
                          连接中...
                        </>
                      ) : scanCameraStatus === "connected" ? (
                        <>
                          <i className="fa-solid fa-check mr-2"></i>已连接
                        </>
                      ) : (
                        <>
                          <i className="fa-solid fa-sign-in-alt mr-2"></i>登录
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* 抓图相机设置 */}
                <div className="border rounded-lg p-4">
                  <h4 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
                    <i className="fa-solid fa-camera mr-2 text-purple-500"></i>
                    抓图相机
                  </h4>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        IP地址
                      </label>
                      <input
                        type="text"
                        value={captureCameraConfig.ip}
                        onChange={(e) =>
                          setCaptureCameraConfig({
                            ...captureCameraConfig,
                            ip: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="192.168.1.101"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        端口号
                      </label>
                      <input
                        type="text"
                        value={captureCameraConfig.port}
                        onChange={(e) =>
                          setCaptureCameraConfig({
                            ...captureCameraConfig,
                            port: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="554"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        用户名
                      </label>
                      <input
                        type="text"
                        value={captureCameraConfig.username}
                        onChange={(e) =>
                          setCaptureCameraConfig({
                            ...captureCameraConfig,
                            username: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        密码
                      </label>
                      <input
                        type="password"
                        value={captureCameraConfig.password}
                        onChange={(e) =>
                          setCaptureCameraConfig({
                            ...captureCameraConfig,
                            password: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      />
                    </div>
                    <button
                      onClick={() => handleCameraLogin("capture")}
                      disabled={captureCameraLoading}
                      className={`w-full py-2 rounded-lg transition-colors flex items-center justify-center ${
                        captureCameraStatus === "connected"
                          ? "bg-green-600 hover:bg-green-700"
                          : "bg-blue-600 hover:bg-blue-700"
                      } text-white`}
                    >
                      {captureCameraLoading ? (
                        <>
                          <i className="fas fa-spinner fa-spin mr-2"></i>
                          连接中...
                        </>
                      ) : captureCameraStatus === "connected" ? (
                        <>
                          <i className="fa-solid fa-check mr-2"></i>已连接
                        </>
                      ) : (
                        <>
                          <i className="fa-solid fa-sign-in-alt mr-2"></i>登录
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* 模态框底部 */}
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setIsCameraSettingsOpen(false)}
                className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* 页脚 */}
      <footer className="bg-white py-6 border-t border-gray-200 relative z-10 mt-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <p className="text-gray-500 text-sm">
                © 2025 中国烟草 - 智慧仓库盘点系统
              </p>
            </div>
            <div className="flex space-x-6">
              <a
                href="#"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                使用帮助
              </a>
              <a
                href="#"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                系统手册
              </a>
              <a
                href="#"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                联系技术支持
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
