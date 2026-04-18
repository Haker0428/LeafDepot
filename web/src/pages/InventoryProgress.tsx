/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2026-03-14 19:34:06
 * @FilePath: /Leafdepot/web/src/pages/InventoryProgress.tsx
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Modal } from "antd";
import { GATEWAY_URL } from "../config/ip_address";
import { useAuth } from "../contexts/authContext";
import { addOperationLog } from "../lib/operationLog";

import { v4 as uuidv4 } from "uuid";
import {
  CreateTaskGroupRequest,
  TaskData,
  TargetRoute,
  ApiResponse,
} from "../hooks/types";

// 创建模拟图片数据
const createMockImages = (count: number, type: "original" | "postprocess") => {
  return Array.from({ length: count }, (_, i) => {
    // 使用空间生成的图片作为占位符
    const prompt =
      type === "original"
        ? `warehouse%20storage%20bin%20${i + 1}`
        : `processed%20warehouse%20image%20${i + 1}`;
    return `https://space.coze.cn/api/coze_space/gen_image?image_size=landscape_4_3&prompt=${prompt}&sign=e3fcd7c68f88aefd012cae7899ef119a`;
  });
};

// 生成17张原始图片和17张处理后的图片
const originalImages = createMockImages(17, "original");
const postprocessImages = createMockImages(17, "postprocess");
import { int } from "zod/v4";

// 定义接口类型 - 根据InventoryStart.tsx中的InventoryTask接口
interface InventoryItem {
  id: string;
  productName: string;
  specification: string;
  systemQuantity: number;
  actualQuantity: number | null;
  unit: string;
  locationId: string;
  locationName: string;
  taskNo: string;
  startTime: number;
  whCode?: string;
  areaCode?: string;
  areaName?: string;
  binCode?: string;
  binDesc?: string;
  binStatus?: string;
  tobaccoCode?: string;
  rcsCode: string;
  // 照片路径
  photo3dPath?: string;
  photoDepthPath?: string;
  photoScan1Path?: string;
  photoScan2Path?: string;
  // 识别品规（区分于系统品规，用于判断是否未识别）
  actualSpec?: string;
}

// 从InventoryStart.tsx复制的InventoryTask接口
interface InventoryTask {
  taskID: string;
  whCode: string;
  areaCode: string;
  areaName: string;
  binCode: string;
  binDesc: string;
  maxQty: number;
  binStatus: string;
  tobaccoQty: number;
  tobaccoCode: string;
  tobaccoName: string;
  rcsCode: string;
}

// 定义任务清单接口 - 根据InventoryStart.tsx中的任务清单结构
interface TaskManifest {
  id: string;
  taskNo: string;
  createdAt: string;
  taskCount: number;
  tasks: InventoryTask[];
  status: string;
  totalItems: number;
  stats?: {
    totalBins: number;
    totalQuantity: number;
    uniqueItems: number;
    uniqueLocations: number;
  };
}

// 盘点任务状态函数 - 从InventoryStart.tsx复制
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

// 库位状态函数 - 从InventoryStart.tsx复制
const binStatus = (status: string) => {
  switch (status) {
    case "0":
      return "停用";
    case "1":
      return "正常";
    case "2":
      return "仅移入（禁出）";
    case "3":
      return "仅移出（禁入）";
    case "4":
      return "冻结";
    default:
      return "正常";
  }
};

// 新增：格式化时间函数
const formatTime = (milliseconds: number) => {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds}秒`;
};

// 新增：计算差异率函数
const calculateDiffRate = (
  items: InventoryItem[],
  abnormalTasks: any[],
) => {
  const totalItems = items.length;
  return totalItems > 0 ? (abnormalTasks.length / totalItems) * 100 : 0;
};

export default function InventoryProgress() {
  const { authToken, userName, userLevel } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingAndCreating, setIsSavingAndCreating] = useState(false);
  const [isSaving2LMS, setIsSaving2LMS] = useState(false);
  const [isIssuingTask, setIsIssuingTask] = useState(false);
  const [isStartingTask, setIsStartingTask] = useState(false);
  const [currentTaskNo, setCurrentTaskNo] = useState<string | null>(null);
  const [currentTaskManifest, setCurrentTaskManifest] =
    useState<TaskManifest | null>(null);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  const [currentImage, setCurrentImage] = useState<string | null>(null);
  const [postImage, setPostImage] = useState<string | null>(null);

  const [currentCaptureImageIndex, setCaptureCurrentImageIndex] = useState(0);
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [selectedCaptureRowIndex, setSelectedCaptureRowIndex] = useState<
    number | null
  >(null);
  const [isTaskStarted, setIsTaskStarted] = useState(false);
  const [isCapture, setIsCapture] = useState(false);
  const [isCalculate, setIsCalculate] = useState(false);
  const [isTaskCompleted, setIsTaskCompleted] = useState(false);
  const [taskStartTime, setTaskStartTime] = useState<number | null>(null);
  const [imageLoading, setImageLoading] = useState(true);
  const [imageError, setImageError] = useState(false);
  const [isStatisticsModalOpen, setIsStatisticsModalOpen] = useState(false);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  // pendingSaveAction: 点击"保存并进行下次盘点"时传入的保存回调，弹窗确认后才执行
  const [pendingSaveAction, setPendingSaveAction] = useState<(() => void) | null>(null);
  const [currentExecutingTaskIndex, setCurrentExecutingTaskIndex] = useState<
    number | null
  >(null);

  // 盘点失败的库位弹窗状态
  const [failedBinsModal, setFailedBinsModal] = useState<{
    open: boolean;
    bins: Array<{ binLocation: string; error: string }>;
    onOk: () => void;
  }>({ open: false, bins: [], onOk: () => {} });

  // 系统离线弹窗状态
  const [systemOfflineModal, setSystemOfflineModal] = useState<{
    open: boolean;
    message: string;
    onOk: () => void;
  }>({ open: false, message: "", onOk: () => {} });

  // 任务下发失败弹窗状态
  const [taskErrorModal, setTaskErrorModal] = useState<{
    open: boolean;
    errorType: "rcs" | "camera" | "other";
    message: string;
    onOk: () => void;
  }>({ open: false, errorType: "other", message: "", onOk: () => {} });

  // 照片组状态：2组，每组2张（上、下）
  // 组0: 3D相机 (上: main, 下: depth)
  // 组1: 扫码相机 (上: scan1, 下: scan2)
  const [photoGroups, setPhotoGroups] = useState<
    Array<{ top: string; bottom: string }>
  >([
    { top: "", bottom: "" },
    { top: "", bottom: "" },
  ]);
  const [currentGroupIndex, setCurrentGroupIndex] = useState(0); // 0=3D相机, 1=扫码相机

  // 用于跟踪是否已经加载过照片，避免重复加载
  const loadedPhotoKeysRef = useRef<Set<string>>(new Set());

  // 跟踪每个储位的照片路径，用于检测新照片
  const photoPathsRef = useRef<
    Map<
      string,
      {
        photo3dPath: string;
        photoDepthPath: string;
        photoScan1Path: string;
        photoScan2Path: string;
      }
    >
  >(new Map());

  // 防止并发加载照片的竞态问题：记录当前正在加载的 photoKey
  const photoLoadingKeyRef = useRef<string | null>(null);

  // 记录最新完成（获得新照片）的 bin，用于解决多 bin 同时完成时的行选择问题
  const latestCompletedBinRef = useRef<{ index: number; key: string } | null>(null);

  // 在已有的状态后面添加 WebSocket 相关状态
  const [webSocket, setWebSocket] = useState<WebSocket | null>(null);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);
  const [receivedCSVData, setReceivedCSVData] = useState<
    Array<{
      taskNo: string;
      binLocation: string;
      number: number | null;
      text: string | null;
      success: boolean;
      message: string;
      timestamp: string;
    }>
  >([]);

  // 在组件中添加 WebSocket 连接函数
  // const connectWebSocket = () => {
  // if (!currentTaskNo) {
  // toast.error("没有当前任务，无法连接 WebSocket");
  // return;
  // }

  // // 构建 WebSocket URL，根据你的网关地址调整
  // const wsUrl = `ws://10.16.82.95:8000/ws/inventory/${currentTaskNo}`;
  // console.log("尝试连接 WebSocket:", wsUrl);

  // const ws = new WebSocket(wsUrl);

  // ws.onopen = () => {
  // console.log("WebSocket 连接成功");
  // setIsWebSocketConnected(true);
  // toast.success("已连接到盘点服务器");
  // };

  // ws.onmessage = (event) => {
  // try {
  // const data = JSON.parse(event.data);
  // console.log("收到 WebSocket 消息:", data);

  // if (data.type === "csv_data") {
  // handleReceivedCSVData(data);
  // }
  // } catch (error) {
  // console.error("解析 WebSocket 消息失败:", error);
  // }
  // };

  // ws.onerror = (error) => {
  // console.error("WebSocket 连接错误:", error);
  // toast.error("WebSocket 连接错误");
  // };

  // ws.onclose = (event) => {
  // console.log("WebSocket 连接关闭:", event.code, event.reason);
  // setIsWebSocketConnected(false);

  // // 如果不是正常关闭，尝试重新连接
  // if (event.code !== 1000) {
  // toast.warning("WebSocket 连接断开，正在重新连接...");
  // setTimeout(() => {
  // connectWebSocket();
  // }, 3000);
  // }
  // };

  // 0;

  // setWebSocket(ws);
  // };

  // 处理接收到的 CSV 数据
  // 修改 handleReceivedCSVData 函数
  const handleReceivedCSVData = (data: any) => {
    console.log("处理 CSV 数据:", data);
    console.log("处理 success 数据:", data.success);
    console.log("处理 number 数据:", data.number);
    console.log("处理 text 数据:", data.text);

    if (data.success) {
      // 1. 更新 receivedCSVData
      setReceivedCSVData((prev) => {
        const existingIndex = prev.findIndex(
          (item) =>
            item.taskNo === data.taskNo &&
            item.binLocation === data.binLocation,
        );

        if (existingIndex >= 0) {
          const newData = [...prev];
          newData[existingIndex] = data;
          return newData;
        } else {
          return [...prev, data];
        }
      });

      // 2. 同步更新 inventoryItems - 修复参数名冲突
      setInventoryItems((prevItems) => {
        console.log("当前 inventoryItems:", prevItems);
        console.log(
          "匹配条件: taskNo=",
          data.taskNo,
          "binLocation=",
          data.binLocation,
        );

        const updatedItems = prevItems.map((item) => {
          // 根据任务号和库位代码匹配
          console.log("检查项目:", item.taskNo, item.binDesc);

          if (
            item.taskNo === data.taskNo &&
            item.binDesc === data.binLocation
          ) {
            console.log("找到匹配项，开始更新:", item);

            // 解析 number 值，确保是数字或 null
            let actualQuantity = null;
            if (
              data.number !== undefined &&
              data.number !== null &&
              data.number !== ""
            ) {
              const num = Number(data.number);
              actualQuantity = isNaN(num) ? null : num;
              console.log("转换后的数量:", actualQuantity);
            }

            const updatedItem = {
              ...item,
              actualQuantity: actualQuantity,
            };

            // 如果有文本识别结果且不是空字符串，更新实际品规
            if (
              data.text !== undefined &&
              data.text !== null &&
              data.text.trim() !== ""
            ) {
              updatedItem.productName = data.text;
              console.log("更新品规名称:", data.text);
            }

            console.log("更新后的项目:", updatedItem);
            return updatedItem;
          }
          return item;
        });

        console.log("更新后的 inventoryItems:", updatedItems);
        return updatedItems;
      });

      // 显示成功消息
      toast.success(
        `库位 ${data.binLocation} 数据更新成功: 数量=${data.number || 0}`,
      );
    } else {
      toast.error(`库位 ${data.binLocation} 数据处理失败: ${data.message}`);
    }
  };

  useEffect(() => {
    const completedCount = inventoryItems.filter(
      (item) => item.actualQuantity !== null,
    ).length;
    const newProgress = (completedCount / inventoryItems.length) * 100;
    setProgress(Math.min(Math.round(newProgress), 100));

    // 检查是否所有任务都已完成
    const allTasksCompleted = completedCount === inventoryItems.length;

    // 如果全部完成且当前状态不是已完成，则设置为已完成
    if (allTasksCompleted && !isTaskCompleted) {
      setIsTaskCompleted(true);
      toast.success("所有盘点任务已完成！");

      // 计算总耗时（从开始到现在的差值）
      if (taskStartTime) {
        const totalTime = Date.now() - taskStartTime;

        // 计算异常任务（数量不一致 或 品规未识别/不匹配）
        const abnormalTasks = inventoryItems
          .filter(
            (item) => {
              if (item.actualQuantity === null) return false;
              const qtyWrong = item.actualQuantity !== item.systemQuantity;
              const specUnrecognized = item.actualSpec === "未识别";
              const specMismatch = !!item.actualSpec && item.actualSpec !== item.productName;
              const specWrong = specUnrecognized || specMismatch;
              return qtyWrong || specWrong;
            },
          )
          .map((item) => ({
            taskNo: item.taskNo,
            location: item.locationName,
            expected: item.systemQuantity,
            actual: item.actualQuantity,
          }));

        // 计算差异率
        const diffRate =
          inventoryItems.length > 0
            ? (abnormalTasks.length / inventoryItems.length) * 100
            : 0;

        // 更新统计数据
        setStatisticsData({
          totalTime,
          diffRate,
          abnormalTasks,
        });
      }
    }
    // 如果有未完成任务但状态是已完成，重置状态
    else if (!allTasksCompleted && isTaskCompleted) {
      setIsTaskCompleted(false);
    }

    console.log(
      "进度已更新:",
      completedCount,
      "/",
      inventoryItems.length,
      "=",
      newProgress,
      "%",
    );
    console.log("任务完成状态:", allTasksCompleted ? "已完成" : "进行中");
  }, [inventoryItems, isTaskCompleted, taskStartTime]);

  // 在组件中添加调试效果
  useEffect(() => {
    console.log("🔍 inventoryItems 已更新:", inventoryItems);
    console.log(
      "📊 有实际数量的项目:",
      inventoryItems.filter((item) => item.actualQuantity !== null).length,
    );
  }, [inventoryItems]);

  useEffect(() => {
    console.log("📥 receivedCSVData 已更新:", receivedCSVData);
  }, [receivedCSVData]);

  // // 在组件挂载时连接 WebSocket
  // useEffect(() => {
  // if (currentTaskNo) {
  // console.log("连接 WebSocket");
  // connectWebSocket();
  // }

  // // 清理函数：组件卸载时关闭 WebSocket
  // return () => {
  // if (webSocket) {
  // webSocket.close();
  // }
  // };
  // }, [currentTaskNo]);

  // 添加一个手动重连按钮的函数
  // 由于connectWebSocket函数已被注释，这里也注释掉相关功能
  // const handleReconnectWebSocket = () => {
  // if (webSocket) {
  // webSocket.close();
  // }
  // connectWebSocket();
  // };

  const handleDisconnectWebSocket = () => {
    if (webSocket) {
      setIsWebSocketConnected(false);
      webSocket.close();
    }
  };

  // 加载2组照片对（每组2张：上、下）
  const loadPhotoGroups = async (
    taskNo: string,
    binLocation: string,
    photoPaths: {
      photo3dPath?: string;
      photoDepthPath?: string;
      photoScan1Path?: string;
      photoScan2Path?: string;
    },
  ) => {
    console.log("📸 loadPhotoGroups 开始:", {
      taskNo,
      binLocation,
      photoPaths,
    });
    setImageLoading(true);
    setImageError(false);

    try {
      // 定义2组图片对
      const groups = [
        {
          top: photoPaths.photo3dPath,
          bottom: photoPaths.photoDepthPath,
        },
        {
          top: photoPaths.photoScan1Path,
          bottom: photoPaths.photoScan2Path,
        },
      ];

      const loadedGroups: Array<{ top: string; bottom: string }> = [];

      for (let groupIndex = 0; groupIndex < groups.length; groupIndex++) {
        const group = groups[groupIndex];
        const topUrl = group.top
          ? buildImageUrl(group.top, taskNo, binLocation)
          : "";
        const bottomUrl = group.bottom
          ? buildImageUrl(group.bottom, taskNo, binLocation)
          : "";

        let loadedTop = "";
        let loadedBottom = "";

        // 加载上方图片
        if (topUrl) {
          try {
            const response = await fetch(topUrl);
            if (response.ok) {
              const blob = await response.blob();
              loadedTop = URL.createObjectURL(blob);
              console.log(`✅ 组${groupIndex + 1} 上方图片加载成功`);
            } else {
              console.warn(
                `❌ 组${groupIndex + 1} 上方图片加载失败: ${response.status}`,
              );
            }
          } catch (error) {
            console.error(`❌ 组${groupIndex + 1} 上方图片加载异常:`, error);
          }
        }

        // 加载下方图片
        if (bottomUrl) {
          try {
            const response = await fetch(bottomUrl);
            if (response.ok) {
              const blob = await response.blob();
              loadedBottom = URL.createObjectURL(blob);
              console.log(`✅ 组${groupIndex + 1} 下方图片加载成功`);
            } else {
              console.warn(
                `❌ 组${groupIndex + 1} 下方图片加载失败: ${response.status}`,
              );
            }
          } catch (error) {
            console.error(`❌ 组${groupIndex + 1} 下方图片加载异常:`, error);
          }
        }

        loadedGroups.push({ top: loadedTop, bottom: loadedBottom });
      }

      console.log("📸 所有图片组加载完成:", loadedGroups);
      setPhotoGroups(loadedGroups);
      setCurrentGroupIndex(0); // 默认显示第一组

      // 统计有图片的组数
      const validGroups = loadedGroups.filter((g) => g.top || g.bottom).length;
      if (validGroups > 0) {
        toast.success(`成功加载 ${validGroups} 组照片`);
      } else {
        toast.warning("该储位暂无照片");
      }
    } catch (error) {
      console.error("加载照片组失败:", error);
      setImageError(true);
      toast.error("加载照片失败");
    } finally {
      setImageLoading(false);
    }
  };

  const handleRowClick = async (taskNo: string, binDesc: string) => {
    console.log("🖱️ handleRowClick 被调用:", { taskNo, binDesc });

    if (!isTaskStarted) {
      console.log("⚠️ 任务未启动，无法加载照片");
      toast.info("请先启动盘点任务");
      return;
    }

    const rowIndex = inventoryItems.findIndex(
      (item) => item.taskNo === taskNo && item.binDesc === binDesc,
    );

    if (rowIndex === -1) {
      console.error("❌ 未找到对应的任务和储位");
      toast.error("未找到对应的任务和储位");
      return;
    }

    const item = inventoryItems[rowIndex];
    console.log("✅ 找到对应的item:", item);

    setSelectedRowIndex(rowIndex);
    setCurrentExecutingTaskIndex(rowIndex);
    setIsCapture(true);

    // 清除该储位的已加载记录，允许重新加载
    const photoKey = `${taskNo}-${binDesc}`;
    loadedPhotoKeysRef.current.delete(photoKey);
    photoPathsRef.current.delete(photoKey);
    // 标记为正在加载，防止自动加载 effect 与手动点击竞态
    photoLoadingKeyRef.current = photoKey;

    console.log("🔄 开始加载照片组...");

    // 加载照片组
    await loadPhotoGroups(taskNo, binDesc, {
      photo3dPath: item.photo3dPath,
      photoDepthPath: item.photoDepthPath,
      photoScan1Path: item.photoScan1Path,
      photoScan2Path: item.photoScan2Path,
    });
  };

  // 保留原有的handleRowClickPost函数，但标记为废弃
  /*
  const handleRowClick = async (taskNo: string, binDesc: string) => {
    if (!isTaskStarted) {
      toast.info("请先启动盘点任务");
      return;
    }

    const rowIndex = inventoryItems.findIndex(
      (item) => item.taskNo === taskNo && item.binDesc === binDesc,
    );

    if (rowIndex === -1) {
      toast.error("未找到对应的任务和储位");
      return;
    }

    setSelectedRowIndex(rowIndex);
    setCurrentExecutingTaskIndex(rowIndex);
    setIsCapture(true);

    // 确保每次点击前重置状态
    setImageLoading(true);
    setImageError(false);

    // 清除之前的图片URL（如果存在）
    if (currentImage) {
      URL.revokeObjectURL(currentImage);
      setCurrentImage(null);
    }

    try {
      const response = await fetch(`${GATEWAY_URL}/api/get-image-original`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ taskNo, binDesc }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch image: ${response.statusText}`);
      }

      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);

      setCurrentImage(imageUrl);
      setPostImage(null);

      toast.success(`成功加载 ${taskNo} - ${binDesc} 的原始图片`);
    } catch (error) {
      console.error("加载图片失败:", error);
      setImageError(true);
      toast.error(`未找到 ${taskNo} - ${binDesc} 的图片文件`);
      setCurrentImage(null);
    } finally {
      setImageLoading(false);
    }
  };
  */

  useEffect(() => {
    return () => {
      if (currentImage) {
        URL.revokeObjectURL(currentImage);
      }
    };
  }, [currentImage]);

  // 监听inventoryItems变化，自动加载新照片（不依赖selectedRowIndex）
  useEffect(() => {
    if (!currentTaskNo || inventoryItems.length === 0 || !isTaskStarted) {
      console.log("⚠️ 自动加载条件不满足:", {
        hasTaskNo: !!currentTaskNo,
        hasItems: inventoryItems.length > 0,
        isTaskStarted,
      });
      return;
    }

    console.log("🔍 检查是否有新照片...");

    // 遍历所有储位，检查是否有新照片
    // 记录最新发现新照片的 bin（解决多 bin 同时完成时的竞态问题）
    let latestNewBin: {
      index: number;
      binLocation: string;
      photoPaths: {
        photo3dPath: string;
        photoDepthPath: string;
        photoScan1Path: string;
        photoScan2Path: string;
      };
    } | null = null as any;

    inventoryItems.forEach((item, index) => {
      // 统一使用 binDesc 作为储位标识符，与 handleRowClick 保持一致
      const binLocation = item.binDesc || "";
      const photoKey = `${currentTaskNo}-${binLocation}`;

      // 获取当前照片路径
      const currentPhotoPaths = {
        photo3dPath: item.photo3dPath || "",
        photoDepthPath: item.photoDepthPath || "",
        photoScan1Path: item.photoScan1Path || "",
        photoScan2Path: item.photoScan2Path || "",
      };

      // 获取之前记录的照片路径
      const previousPhotoPaths = photoPathsRef.current.get(photoKey);

      // 检查是否有照片路径（至少有一个不为空）
      const hasPhotos =
        currentPhotoPaths.photo3dPath ||
        currentPhotoPaths.photoDepthPath ||
        currentPhotoPaths.photoScan1Path ||
        currentPhotoPaths.photoScan2Path;

      if (hasPhotos) {
        // 检查照片路径是否发生变化
        let hasNewPhotos = false;

        if (!previousPhotoPaths) {
          // 之前没有照片记录，说明是新照片
          hasNewPhotos = true;
          console.log(`📸 检测到新照片（之前无记录）: ${binLocation}`);
        } else {
          // 检查每个照片路径是否变化
          if (
            currentPhotoPaths.photo3dPath !== previousPhotoPaths.photo3dPath ||
            currentPhotoPaths.photoDepthPath !==
              previousPhotoPaths.photoDepthPath ||
            currentPhotoPaths.photoScan1Path !==
              previousPhotoPaths.photoScan1Path ||
            currentPhotoPaths.photoScan2Path !==
              previousPhotoPaths.photoScan2Path
          ) {
            hasNewPhotos = true;
            console.log(`📸 检测到新照片（路径变化）: ${binLocation}`, {
              previous: previousPhotoPaths,
              current: currentPhotoPaths,
            });
          }
        }

        if (hasNewPhotos) {
          // 记录最新发现新照片的 bin（每次循环覆盖，最终保留最后一个）
          latestNewBin = {
            index,
            binLocation,
            photoPaths: currentPhotoPaths,
          };

          // 标记为已加载
          loadedPhotoKeysRef.current.add(photoKey);
        }

        // 更新照片路径记录
        photoPathsRef.current.set(photoKey, currentPhotoPaths);
      }
    });

    // 只对最新发现新照片的 bin 执行加载（避免多个 bin 同时完成时的竞态覆盖）
    if (latestNewBin) {
      const loadingKey = `${currentTaskNo}-${latestNewBin.binLocation}`;

      // 防止重复加载：只有当前没有正在加载这个 bin 时才加载
      if (photoLoadingKeyRef.current !== loadingKey) {
        photoLoadingKeyRef.current = loadingKey;
        console.log(
          `📸 自动加载照片: 储位 ${latestNewBin.binLocation}`,
        );
        console.log(`📸 照片路径:`, latestNewBin.photoPaths);

        // 自动选中该行
        setSelectedRowIndex(latestNewBin.index);

        // 加载照片
        loadPhotoGroups(
          currentTaskNo,
          latestNewBin.binLocation,
          latestNewBin.photoPaths,
        );
      }
    }
  }, [inventoryItems, currentTaskNo, isTaskStarted]);

  // 任务启动或切换时，清除之前的照片记录
  useEffect(() => {
    if (isTaskStarted || currentTaskNo) {
      console.log("🧹 任务/任务编号变化，清除照片记录");
      loadedPhotoKeysRef.current.clear();
      photoPathsRef.current.clear();
      photoLoadingKeyRef.current = null;
    }
  }, [isTaskStarted, currentTaskNo]);

  const handleRowClickPost = async (taskNo: string, binDesc: string) => {
    if (!isTaskStarted) {
      toast.info("请先启动盘点任务");

      return;
    }

    const rowIndex = inventoryItems.findIndex(
      (item) => item.taskNo === taskNo && item.binDesc === binDesc,
    );

    if (rowIndex === -1) {
      toast.error("未找到对应的任务和储位");

      return;
    }

    // setSelectedRowIndex(rowIndex);

    // setCurrentExecutingTaskIndex(rowIndex);

    // setImageLoading(true);

    // setImageError(false);

    try {
      const response = await fetch(`${GATEWAY_URL}/api/get-image-postprocess`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({ taskNo, binDesc }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch image: ${response.statusText}`);
      }

      const blob = await response.blob();

      const imageUrl = URL.createObjectURL(blob);

      console.info("imageUrl:", { imageUrl });

      setIsCapture(true);

      setPostImage(imageUrl); // 设置当前图片

      toast.success(`成功加载 ${taskNo} - ${binDesc} 的计算后图片`);
    } catch (error) {
      console.error("加载图片失败:", error);

      setImageError(true);

      toast.error(`未找到 ${taskNo} - ${binDesc} 的图片文件`);

      setPostImage(null);
    } finally {
      setImageLoading(false);
    }
  };
  useEffect(() => {
    return () => {
      if (postImage) {
        URL.revokeObjectURL(postImage);
      }
    };
  }, [postImage]);

  // 辅助函数：构建图片URL（参考History.tsx的逻辑）
  const buildImageUrl = (
    photoPath: string,
    taskNo: string,
    binLocation: string,
  ) => {
    if (!photoPath || photoPath.trim() === "") {
      return "";
    }

    try {
      // 解析照片路径，格式如：/{taskNo}/{binLocation}/{cameraType}/{filename}
      // 例如：/HS2026031445/A区001储位/3d_camera/main.jpg
      const normalizedPath = photoPath.startsWith("/")
        ? photoPath.substring(1)
        : photoPath;

      const parts = normalizedPath.split("/");

      // 确保路径至少有4部分：taskNo, binLocation, cameraType, filename
      if (parts.length < 4) {
        console.warn(`无效的照片路径格式: ${photoPath}`);
        return "";
      }

      // 从路径中提取所有参数
      const pathTaskNo = parts[0]; // 任务编号
      const pathBinLocation = parts[1]; // 储位名称
      const cameraType = parts[2].toLowerCase(); // 相机类型
      const fullFilename = parts[3]; // 完整文件名
      const filename = fullFilename.split(".")[0]; // 去掉扩展名，只保留文件名

      // 使用 /api/history/image 接口，该接口会自动尝试不同扩展名
      // 添加 source=capture_img 参数指定从 capture_img 目录读取
      return `${GATEWAY_URL}/api/history/image?taskNo=${pathTaskNo}&binLocation=${pathBinLocation}&cameraType=${cameraType}&filename=${filename}&source=capture_img`;
    } catch (error) {
      console.error(`解析照片路径失败: ${photoPath}`, error);
      return "";
    }
  };

  // 获取计算后的图片 - 调用gateway接口获取图片
  const fetchCalculateImages = async (
    taskNo: string,
    binDesc: string,
    photo3dPath?: string, // 3d_camera 图片路径
    photoDepthPath?: string, // depth 图片路径
  ) => {
    if (!isTaskStarted) {
      toast.info("请先启动盘点任务");
      return;
    }

    setImageLoading(true);
    setImageError(false);
    setIsCapture(true);
    setIsCalculate(true);

    // 清除之前的图片URL（如果存在）
    if (currentImage) {
      URL.revokeObjectURL(currentImage);
      setCurrentImage(null);
    }
    if (postImage) {
      URL.revokeObjectURL(postImage);
      setPostImage(null);
    }

    try {
      // 如果提供了图片路径，使用构建的URL
      if (photo3dPath && photoDepthPath) {
        const imageUrl3d = buildImageUrl(photo3dPath, taskNo, binDesc);
        const imageUrlDepth = buildImageUrl(photoDepthPath, taskNo, binDesc);

        if (imageUrl3d) {
          const response3d = await fetch(imageUrl3d);
          if (response3d.ok) {
            const blob = await response3d.blob();
            setCurrentImage(URL.createObjectURL(blob));
          }
        }

        if (imageUrlDepth) {
          const responseDepth = await fetch(imageUrlDepth);
          if (responseDepth.ok) {
            const blob = await responseDepth.blob();
            setPostImage(URL.createObjectURL(blob));
            toast.success(`成功加载 ${taskNo} - ${binDesc} 的计算后图片`);
          } else {
            toast.warning(`部分图片加载失败: ${taskNo} - ${binDesc}`);
          }
        }
      } else {
        // 如果没有提供图片路径，使用默认的图片路径（兼容原有逻辑）
        // 获取 main.jpg - 用于上半部分显示
        const mainRotatedResponse = await fetch(
          `${GATEWAY_URL}/api/inventory/image?taskNo=${encodeURIComponent(
            taskNo,
          )}&binLocation=${encodeURIComponent(
            binDesc,
          )}&cameraType=3d_camera&filename=main.jpg&source=capture_img`,
        );

        if (mainRotatedResponse.ok) {
          const mainRotatedBlob = await mainRotatedResponse.blob();
          const mainRotatedUrl = URL.createObjectURL(mainRotatedBlob);
          setCurrentImage(mainRotatedUrl);
        } else {
          console.warn(
            "获取 main_rotated.jpg 失败:",
            mainRotatedResponse.status,
          );
        }

        // 获取 depth.jpg - 用于下半部分显示
        const depthColorResponse = await fetch(
          `${GATEWAY_URL}/api/inventory/image?taskNo=${encodeURIComponent(
            taskNo,
          )}&binLocation=${encodeURIComponent(
            binDesc,
          )}&cameraType=3d_camera&filename=depth.jpg&source=capture_img`,
        );

        if (depthColorResponse.ok) {
          const depthColorBlob = await depthColorResponse.blob();
          const depthColorUrl = URL.createObjectURL(depthColorBlob);
          setPostImage(depthColorUrl);
          toast.success(`成功加载 ${taskNo} - ${binDesc} 的计算后图片`);
        } else {
          console.warn("获取 depth_color.jpg 失败:", depthColorResponse.status);
          toast.warning(`部分图片加载失败: ${taskNo} - ${binDesc}`);
        }
      }
    } catch (error) {
      console.error("加载图片失败:", error);
      setImageError(true);
      toast.error(`未找到 ${taskNo} - ${binDesc} 的图片文件`);
    } finally {
      setImageLoading(false);
    }
  };

  const [statisticsData, setStatisticsData] = useState({
    totalTime: 0,
    diffRate: 0,
    abnormalTasks: [] as any[],
  });

  // 编辑品规状态
  const [editingSpecId, setEditingSpecId] = useState<string | null>(null);
  const [editSpecValue, setEditSpecValue] = useState<string>("");

  // 编辑差异状态
  const [editingDiffId, setEditingDiffId] = useState<string | null>(null);
  const [editDiffValue, setEditDiffValue] = useState<string>("");

  // 校准记录：key 为 binLocation，value 包含是否修改了品规/数量
  type CalibrationRecord = { specModified: boolean; quantityModified: boolean };

  // 记录哪些储位有人工校准（点击对勾才记录，与品规检测结果无关）
  const [manualCalibratedLocations, setManualCalibratedLocations] = useState<Set<string>>(new Set());
  // 记录哪些储位被勾选为重新盘点
  const [selectedRecountItems, setSelectedRecountItems] = useState<Set<string>>(new Set());
  const [calibrationRecords, setCalibrationRecords] = useState<
    Record<string, CalibrationRecord>
  >({});

  // 在已有的状态后面添加
  const [gatewayStatus, setGatewayStatus] = useState<string>("disconnected");
  const [robotStatus, setRobotStatus] = useState<string>("idle");
  const [captureStatus, setCaptureStatus] = useState<string>("idle");
  const [calculationStatus, setCalculationStatus] = useState<string>("idle");

  // 添加状态来存储从网关接收的图片
  const [originalImagesFromGateway, setOriginalImagesFromGateway] = useState<
    string[]
  >([]);
  const [processedImagesFromGateway, setProcessedImagesFromGateway] = useState<
    string[]
  >([]);

  // 添加一个通用的轮询函数
  const pollUntilCondition = async (
    conditionFn: () => Promise<boolean>,
    timeout: number = 30000,
    interval: number = 1000,
  ): Promise<boolean> => {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const conditionMet = await conditionFn();

      if (conditionMet) {
        return true;
      }

      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    return false;
  };

  // 注释掉不存在的图片变量引用，使用之前创建的mock图片数组
  // const originalImages = [
  //   img1,
  //   img2,
  //   img3,
  //   img4,
  //   img5,
  //   img6,
  //   img7,
  //   img8,
  //   img9,
  //   img10,
  //   img11,
  //   img12,
  //   img13,
  //   img14,
  //   img15,
  //   img16,
  //   img17,
  // ];

  // const postprocessImages = [
  //   img1out,
  //   img2out,
  //   img3out,
  //   img4out,
  //   img5out,
  //   img6out,
  //   img7out,
  //   img8out,
  //   img9out,
  //   img10out,
  //   img11out,
  //   img12out,
  //   img13out,
  //   img14out,
  //   img15out,
  //   img16out,
  //   img17out,
  // ];

  // 监听 currentTaskNo 变化，清空校准记录，避免跨任务数据残留
  useEffect(() => {
    if (currentTaskNo) {
      setCalibrationRecords({});
      setManualCalibratedLocations(new Set());
    }
  }, [currentTaskNo]);

  // 从本地存储获取任务清单并初始化盘点数据
  useEffect(() => {
    const loadTaskManifest = () => {
      try {
        const manifestData = localStorage.getItem("currentTaskManifest");
        const taskNo = localStorage.getItem("currentTaskNo");

        if (manifestData) {
          const manifest: TaskManifest = JSON.parse(manifestData);
          setCurrentTaskManifest(manifest);

          if (manifest.tasks.length > 0) {
            setCurrentTaskNo(taskNo || manifest.tasks[0].taskID);
          }

          // 根据任务清单中的任务初始化盘点数据
          const inventoryData: InventoryItem[] = manifest.tasks.map(
            (task, index) => ({
              id: `${task.taskID}_${task.binCode}_${index}`,
              productName: task.tobaccoName,
              specification: task.binDesc,
              systemQuantity: task.tobaccoQty,
              actualQuantity: null,
              unit: "件", // 默认单位
              locationId: task.binCode,
              locationName: task.binDesc,
              taskNo: task.taskID,
              startTime: Date.now(),
              // 保留原始任务数据
              whCode: task.whCode,
              areaCode: task.areaCode,
              areaName: task.areaName,
              binCode: task.binCode,
              binDesc: task.binDesc,
              binStatus: task.binStatus,
              tobaccoCode: task.tobaccoCode,
              rcsCode: task.rcsCode,
              // 初始化照片路径为空字符串
              photo3dPath: "",
              photoDepthPath: "",
              photoScan1Path: "",
              photoScan2Path: "",
            }),
          );

          setInventoryItems(inventoryData);
          // 清空校准记录，避免残留上一任务的数据
          setCalibrationRecords({});

          // 如果有通过state传递的数据，也进行合并
          if (location.state?.inventoryTasks) {
            console.log(
              "通过state传递的任务数据:",
              location.state.inventoryTasks,
            );
          }

          toast.success(`已加载任务清单，包含 ${manifest.tasks.length} 个任务`);
        }
      } catch (error) {
        console.error("加载任务清单失败:", error);
        toast.error("加载任务清单失败");
      }
    };

    loadTaskManifest();
  }, [location]);

  // 页面加载时检测任务是否已被取消或中断
  useEffect(() => {
    const checkTaskStatus = async () => {
      if (!currentTaskNo) return;
      try {
        const res = await fetch(
          `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(currentTaskNo)}`
        );
        if (!res.ok) return;
        const data = await res.json();
        const status = data.data?.status;
        if (status === "cancelled" || status === "interrupted") {
          localStorage.removeItem("currentTaskManifest");
          localStorage.removeItem("currentTaskNo");
          toast.warning("上一个任务已被中断，请重新下发");
          setCurrentTaskManifest(null);
        }
      } catch {}
    };
    checkTaskStatus();
  }, [currentTaskNo]);

  // 图片加载处理
  const handleImageLoad = () => {
    setImageLoading(false);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageLoading(false);
    setImageError(true);
  };

  // 手动抓图功能
  const handleManualCapture = (
    taskNo: string,
    locationName: string,
    rowIndex: number,
  ) => {
    console.log(
      `手动抓图 - 任务号: ${taskNo}, 货位名称: ${locationName}, 行号: ${
        rowIndex + 1
      }`,
    );

    if (rowIndex >= 0 && rowIndex < originalImages.length) {
      setCurrentImageIndex(rowIndex);
      setSelectedRowIndex(rowIndex);
      toast.success(`已加载 ${locationName} 的图像（${rowIndex + 1}.jpg）`);
    } else {
      toast.error(`没有找到行号 ${rowIndex + 1} 对应的图片`);
    }

    setIsCapture(true);
  };

  // 计算功能 - 调用扫码+识别接口 + 保留模拟API调用
  const handleCalculate = async (
    taskNo: string,
    binDesc: string,
    rowIndex: number,
  ) => {
    console.log(
      `计算 - 任务号: ${taskNo}, 储位编号: ${binDesc}, 行号: ${rowIndex + 1}`,
    );

    if (!isTaskStarted) {
      toast.error("请先启动盘点任务");
      return;
    }

    toast.info(`开始计算: 任务 ${taskNo} - 储位 ${binDesc}`);

    // 从完整任务编号中提取基础任务编号（去掉下划线后的部分）
    // 例如：HS2026013151_1769870025644_0 -> HS2026013151
    const baseTaskNo = taskNo.split("_")[0];
    console.log(`基础任务编号: ${baseTaskNo} (完整任务编号: ${taskNo})`);

    let photo3dPath: string | undefined = undefined;
    let photoDepthPath: string | undefined = undefined;

    // 调用扫码+识别接口（真实接口）
    try {
      const response = await fetch(
        `${GATEWAY_URL}/api/inventory/scan-and-recognize`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            taskNo: baseTaskNo, // 使用基础任务编号
            binLocation: binDesc,
            pile_id: 1, // 默认堆垛ID为1
            code_type: "ucc128", // 默认条码类型
          }),
        },
      );

      // 检查响应状态
      if (response.ok) {
        // 接口调用成功，处理返回结果
        const result = await response.json();
        console.log("扫码+识别接口调用成功，结果:", result);

        // 从返回结果中提取图片路径
        if (result.data && result.data.photos) {
          // 假设返回格式为：{ data: { photos: ["/3D_CAMERA/MAIN.JPEG", "/DEPTH/COLOR.JPEG"] } }
          if (result.data.photos.length >= 1) {
            photo3dPath = result.data.photos[0];
          }
          if (result.data.photos.length >= 2) {
            photoDepthPath = result.data.photos[1];
          }
        } else if (result.photo1_path && result.photo2_path) {
          // 假设返回格式为：{ photo1_path: "/3D_CAMERA/MAIN.JPEG", photo2_path: "/DEPTH/COLOR.JPEG" }
          photo3dPath = result.photo1_path;
          photoDepthPath = result.photo2_path;
        }
      } else {
        // 尝试解析错误信息
        try {
          const errorData = await response.json();
          console.error("扫码+识别接口调用失败:", errorData);
          // 即使真实接口失败，也继续执行模拟逻辑
        } catch {
          console.error(`计算请求发送失败，状态码: ${response.status}`);
        }
      }
    } catch (error) {
      console.error("调用扫码+识别接口失败:", error);
      // 即使真实接口失败，也继续执行模拟逻辑
    }

    // 保留原有的模拟API调用逻辑
    setIsCalculate(true);

    // 模拟API调用
    setTimeout(() => {
      // 更新该行的实际数量（示例数据 - 无误差，实际数量等于系统数量）
      setInventoryItems((prevItems) => {
        const newItems = [...prevItems];

        // 模拟数据无误差：实际数量等于系统数量
        const calculatedQuantity = newItems[rowIndex].systemQuantity;

        newItems[rowIndex] = {
          ...newItems[rowIndex],
          actualQuantity: calculatedQuantity,
        };

        return newItems;
      });

      toast.success(`计算完成: 任务 ${taskNo} - 储位 ${binDesc}`);
    }, 1500);

    // 调用gateway接口获取图片：传入从后端获取的图片路径，使用基础任务编号
    await fetchCalculateImages(
      baseTaskNo,
      String(binDesc),
      photo3dPath,
      photoDepthPath,
    );
  };

  // 启动盘点任务 - 与内部网关程序交互
  const handleStartCountingTask = async () => {
    setTaskStartTime(Date.now());
    setIsStartingTask(true);
    setIsTaskStarted(true);

    try {
      // 1. 调用fastapi接口，向内部网关程序发送任务编号以及全部的储位名称
      if (!currentTaskNo) {
        toast.error("任务编号不存在");
        return;
      }

      // 获取所有储位名称
      //使用RCS站点
      const binLocations = inventoryItems.map((item) => item.locationName);

      const tobaccoCode = inventoryItems.map((item) => item.tobaccoCode);

      const rcsCode = inventoryItems.map((item) => item.rcsCode);

      toast.info("发送任务到网关...");

      // 从 sessionStorage 获取 authToken
      const authToken = sessionStorage.getItem('authToken');

      // 发送任务到网关
      const taskResponse = await fetch(
        `${GATEWAY_URL}/api/inventory/start-inventory`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(authToken ? { 'authToken': authToken } : {}),
          },
          body: JSON.stringify({
            taskNo: currentTaskNo,
            binLocations: binLocations,
            tobaccoCode: tobaccoCode,
            rcsCode: rcsCode,
            inventoryItems: inventoryItems, // 发送完整盘点项，用于条码失败时的品规备用
          }),
        },
      );

      // 检查响应状态
      if (!taskResponse.ok) {
        // 尝试解析错误信息
        try {
          const errorData = await taskResponse.json();
          throw new Error(
            errorData.message || errorData.detail || "任务启动失败",
          );
        } catch {
          throw new Error(`任务启动失败，状态码: ${taskResponse.status}`);
        }
      }

      // 解析成功的 JSON 响应
      const result = await taskResponse.json();

      // 根据你的 API 设计，result 可能包含以下结构
      // 示例1: { "code": 200, "message": "成功", "data": {...} }
      // 示例2: { "status": "success", "data": {...} }

      if (result.code === 200) {
        if (result.message === "盘点任务已启动") {
          toast.success(`任务启动成功，正在执行盘点...`);

          const pollIntervalId = setInterval(async () => {
            try {
              const progressResponse = await fetch(
                `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(currentTaskNo)}`,
              );

              if (!progressResponse.ok) {
                console.error("获取盘点进度失败");
                return;
              }

              const progressResult = await progressResponse.json();

              if (progressResult.code !== 200) {
                return;
              }

              const taskStatus = progressResult.data?.status;

              // 进度 = 已下发库位数 / 总库位数
              const currentStep = progressResult.data?.current_step || 0;
              const totalSteps = progressResult.data?.total_steps || 1;
              setProgress(Math.round((currentStep / totalSteps) * 100));

              // 任务完成或部分完成 → 切换到 /results 获取完整结果
              if (taskStatus === "completed" || taskStatus === "partial") {
                clearInterval(pollIntervalId);

                const resultsResponse = await fetch(
                  `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(currentTaskNo)}`,
                );
                const resultsData = await resultsResponse.json();
                const inventoryResults = resultsData.data?.inventoryResults || [];

                const successCount = inventoryResults.filter((r: any) => r.status !== "异常").length;
                toast.success(
                  taskStatus === "partial"
                    ? `盘点完成（部分），成功 ${successCount}/${inventoryResults.length} 个库位`
                    : "盘点任务完成",
                );

                // 收集失败的库位并计算新的 items（先在外部计算，避免闭包陷阱）
                const failedBins: Array<{ binLocation: string; error: string }> = [];
                const newItems = inventoryItems.map((item) => {
                  const ir = inventoryResults.find((r: any) => r.binLocation === item.locationName);
                  if (!ir) return item;
                  if (ir.status === "异常") {
                    failedBins.push({ binLocation: ir.binLocation, error: ir.error || "未知错误" });
                  }
                  return {
                    ...item,
                    actualQuantity: ir.status === "异常" ? -1 : (ir.actualQuantity ?? item.actualQuantity),
                    actualSpec: ir.actualSpec || "未识别",
                    photo3dPath: ir.photo3dPath,
                    photoDepthPath: ir.photoDepthPath,
                    photoScan1Path: ir.photoScan1Path,
                    photoScan2Path: ir.photoScan2Path,
                  };
                });

                setInventoryItems(newItems);
                setIsTaskCompleted(true);

                if (failedBins.length > 0) {
                  setFailedBinsModal({
                    open: true,
                    bins: failedBins,
                    onOk: () => setFailedBinsModal((prev) => ({ ...prev, open: false })),
                  });
                  toast.error(`${failedBins.length} 个库位盘点失败：${failedBins.map((b) => b.binLocation).join("、")}`);
                } else {
                  // 无失败库位，自动弹出统计窗口
                  showStatisticsModal(newItems);
                }

                loadedPhotoKeysRef.current.clear();
                photoPathsRef.current.clear();
                photoLoadingKeyRef.current = null;

                if (selectedRowIndex === null) {
                  const firstItemWithPhotos = inventoryItems.find(
                    (item) => item.photo3dPath || item.photoDepthPath || item.photoScan1Path || item.photoScan2Path,
                  );
                  if (firstItemWithPhotos) {
                    setSelectedRowIndex(inventoryItems.indexOf(firstItemWithPhotos));
                  }
                }

                return;
              }

              // 任务失败
              if (taskStatus === "failed") {
                clearInterval(pollIntervalId);
                const errorType: "rcs" | "camera" | "other" =
                  (progressResult.data?.error_type as "rcs" | "camera" | "other") || "other";
                if (errorType === "rcs") {
                  setTaskErrorModal({
                    open: true,
                    errorType: "rcs",
                    message: progressResult.data?.message || "RCS 连接失败",
                    onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
                  });
                } else if (errorType === "camera") {
                  setTaskErrorModal({
                    open: true,
                    errorType: "camera",
                    message: progressResult.data?.message || "相机连接失败",
                    onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
                  });
                } else {
                  setTaskErrorModal({
                    open: true,
                    errorType: "other",
                    message: progressResult.data?.message || "盘点任务下发失败",
                    onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
                  });
                }
                setIsStartingTask(false);
                return;
              }
            } catch (error) {
              console.error("轮询盘点进度失败:", error);
            }
          }, 1000);
        } else if (result.message === "任务已在执行中") {
          toast.success(`任务已在执行中，实时监控中...`);

          const pollIntervalId = setInterval(async () => {
            try {
              const progressResponse = await fetch(
                `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(currentTaskNo)}`,
              );
              if (!progressResponse.ok) return;

              const progressResult = await progressResponse.json();
              if (progressResult.code !== 200) return;

              const taskStatus = progressResult.data?.status;

              // 进度 = 已下发库位数 / 总库位数
              const currentStep = progressResult.data?.current_step || 0;
              const totalSteps = progressResult.data?.total_steps || 1;
              setProgress(Math.round((currentStep / totalSteps) * 100));

              if (taskStatus === "completed" || taskStatus === "partial") {
                clearInterval(pollIntervalId);
                const resultsResponse = await fetch(
                  `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(currentTaskNo)}`,
                );
                const resultsData = await resultsResponse.json();
                const inventoryResults = resultsData.data?.inventoryResults || [];

                toast.success("盘点任务完成");
                setIsTaskCompleted(true);

                // 先在外部计算失败库位和 newItems，避免闭包陷阱
                const failedBins: Array<{ binLocation: string; error: string }> = [];
                const newItems = inventoryItems.map((item) => {
                  const ir = inventoryResults.find((r: any) => r.binLocation === item.locationName);
                  if (!ir) return item;
                  if (ir.status === "异常") {
                    failedBins.push({ binLocation: ir.binLocation, error: ir.error || "未知错误" });
                  }
                  return {
                    ...item,
                    actualQuantity: ir.status === "异常" ? -1 : (ir.actualQuantity ?? item.actualQuantity),
                    actualSpec: ir.actualSpec || "未识别",
                    photo3dPath: ir.photo3dPath,
                    photoDepthPath: ir.photoDepthPath,
                    photoScan1Path: ir.photoScan1Path,
                    photoScan2Path: ir.photoScan2Path,
                  };
                });

                setInventoryItems(newItems);

                if (failedBins.length > 0) {
                  setFailedBinsModal({
                    open: true,
                    bins: failedBins,
                    onOk: () => setFailedBinsModal((prev) => ({ ...prev, open: false })),
                  });
                  toast.error(`${failedBins.length} 个库位盘点失败：${failedBins.map((b) => b.binLocation).join("、")}`);
                } else {
                  showStatisticsModal(newItems);
                }
                return;
              }

              if (taskStatus === "failed") {
                clearInterval(pollIntervalId);
                setTaskErrorModal({
                  open: true,
                  errorType: (progressResult.data?.error_type as "rcs" | "camera" | "other") || "other",
                  message: progressResult.data?.message || "盘点任务失败",
                  onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
                });
                setIsStartingTask(false);
                return;
              }
            } catch (error) {
              console.error("轮询盘点进度失败:", error);
            }
          }, 1000);
        }
      } else {
        // API 返回了业务逻辑错误（未进入轮询，直接失败）
        if (result.message && result.message.startsWith("系统离线")) {
          setSystemOfflineModal({
            open: true,
            message: result.message,
            onOk: () => setSystemOfflineModal((prev) => ({ ...prev, open: false })),
          });
          setIsStartingTask(false);
          return;
        } else {
          const errorType: "rcs" | "camera" | "other" =
            result.errorType || "other";
          setTaskErrorModal({
            open: true,
            errorType,
            message: result.message || "未知错误",
            onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
          });
          setIsStartingTask(false);
          return;
        }
      }
    } catch (error) {
      console.error("任务启动失败:", error);
      toast.error(`任务启动失败`);
      setIsStartingTask(false);
    }
  };
  // // 启动盘点任务
  // const handleStartCountingTask = async () => {
  // setIsStartingTask(true);
  // try {
  // const startTime = Date.now();
  // setTaskStartTime(startTime);
  // setCurrentExecutingTaskIndex(null);

  // await new Promise((resolve) => setTimeout(resolve, 1000));

  // // 模拟盘点过程
  // for (let i = 0; i < inventoryItems.length; i++) {
  // setCurrentExecutingTaskIndex(i);
  // setCurrentImageIndex(i % originalImages.length);

  // const delay = 2000 + Math.floor(Math.random() * 1000);
  // await new Promise((resolve) => setTimeout(resolve, delay));

  // // 模拟实际数量（90%概率与系统数量一致，10%概率有差异）
  // const isAccurate = Math.random() < 0.9;
  // let actualQuantity = inventoryItems[i].systemQuantity;

  // if (!isAccurate) {
  // // 模拟差异：在系统数量的80%-120%范围内随机
  // const variation = 0.2;
  // const minQuantity = Math.floor(
  // inventoryItems[i].systemQuantity * (1 - variation)
  // );
  // const maxQuantity = Math.floor(
  // inventoryItems[i].systemQuantity * (1 + variation)
  // );
  // actualQuantity =
  // Math.floor(Math.random() * (maxQuantity - minQuantity + 1)) +
  // minQuantity;

  // // 记录异常任务
  // setStatisticsData((prev) => ({
  // ...prev,
  // abnormalTasks: [
  // ...prev.abnormalTasks,
  // {
  // taskNo: inventoryItems[i].taskNo,
  // location: inventoryItems[i].locationName,
  // expected: inventoryItems[i].systemQuantity,
  // actual: actualQuantity,
  // },
  // ],
  // }));

  // toast.error(
  // `任务 ${i + 1} 异常: 预期 ${
  // inventoryItems[i].systemQuantity
  // }，实际 ${actualQuantity}`
  // );
  // } else {
  // toast.success(`任务 ${i + 1} 完成: 数量 ${actualQuantity}`);
  // }

  // // 更新实际数量
  // setInventoryItems((prevItems) => {
  // const newItems = [...prevItems];
  // newItems[i] = {
  // ...newItems[i],
  // actualQuantity,
  // };

  // // 计算进度
  // const completedCount = newItems.filter(
  // (item) => item.actualQuantity !== null
  // ).length;
  // const newProgress = (completedCount / newItems.length) * 100;
  // setProgress(Math.min(Math.round(newProgress), 100));

  // return newItems;
  // });
  // }

  // setCurrentExecutingTaskIndex(null);
  // setIsTaskStarted(true);
  // setIsTaskCompleted(true);

  // // 计算统计信息
  // const totalTime = Date.now() - startTime;
  // const completedItems = inventoryItems.filter(
  // (item) => item.actualQuantity !== null
  // );
  // const totalItems = completedItems.length;
  // const accurateItems = totalItems - statisticsData.abnormalTasks.length;
  // const accuracyRate =
  // totalItems > 0 ? (accurateItems / totalItems) * 100 : 0;

  // setStatisticsData((prev) => ({
  // ...prev,
  // totalTime,
  // accuracyRate,
  // }));

  // toast.success("盘点任务完成！");
  // } catch (error) {
  // console.error("启动任务失败:", error);
  // toast.error("启动任务失败");
  // } finally {
  // setIsStartingTask(false);
  // }
  // };

  // 处理实际数量输入变化
  const handleActualQuantityChange = (id: string, value: string) => {
    const numericValue = value ? parseInt(value, 10) : null;

    // 检查是否已有接收的 CSV 数据
    const item = inventoryItems.find((item) => item.id === id);
    if (item) {
      const csvData = receivedCSVData.find(
        (data) =>
          data.taskNo === item.taskNo && data.binLocation === item.binCode,
      );

      // 如果有接收的数据，提示用户
      if (csvData && csvData.number !== null) {
        const confirmed = window.confirm(
          `此库位已有自动识别的数量 ${csvData.number}，确定要手动修改为 ${numericValue} 吗？`,
        );

        if (!confirmed) {
          return;
        }
      }
    }

    // 更新数量
    setInventoryItems((prevItems) =>
      prevItems.map((item) => {
        if (item.id === id) {
          const newItem = { ...item, actualQuantity: numericValue };
          return newItem;
        }
        return item;
      }),
    );

    // 更新进度
    const completedCount = inventoryItems.filter(
      (item) => item.actualQuantity !== null,
    ).length;
    const newProgress = (completedCount / inventoryItems.length) * 100;
    setProgress(Math.min(Math.round(newProgress), 100));
  };

  // 处理行点击事件
  // const handleRowClick = (index: number) => {
  // if (!isTaskStarted) {
  // toast.info("请先启动盘点任务");
  // return;
  // }
  // setSelectedRowIndex(index);
  // setCurrentExecutingTaskIndex(index);
  // };

  // 保存盘点结果
  const handleSaveInventory = async () => {
    const incompleteItems = inventoryItems.filter(
      (item) => item.actualQuantity === null,
    );

    if (incompleteItems.length > 0) {
      toast.warning(
        `尚有 ${incompleteItems.length} 项未完成盘点，请完成后再保存`,
      );
      return;
    }

    if (!currentTaskNo) {
      toast.error("任务编号不存在");
      return;
    }

    if (!userName) {
      toast.error("用户未登录，请重新登录");
      return;
    }

    setIsSaving(true);

    try {
      // 准备盘点结果数据，包含品规名称和库存数量
      const inventoryResults = inventoryItems.map((item) => ({
        binLocation: item.locationName,
        status: item.actualQuantity !== null ? "成功" : "异常",
        actualQuantity: item.actualQuantity,
        actualSpec: item.actualSpec || item.productName, // 实际品规（优先用校准值）
        specName: item.productName, // 系统品规名称
        systemQuantity: item.systemQuantity, // 库存数量
        difference:
          item.actualQuantity !== null
            ? item.actualQuantity - item.systemQuantity
            : 0,
        // 品规不匹配（检测到但与系统品规不一致）时标记为异常
        specMismatch: item.actualSpec && item.actualSpec !== item.productName,
        photo3dPath: item.photo3dPath || "",
        photoDepthPath: item.photoDepthPath || "",
        photoScan1Path: item.photoScan1Path || "",
        photoScan2Path: item.photoScan2Path || "",
      }));

      // 调用后端接口保存盘点结果
      const response = await fetch(
        `${GATEWAY_URL}/api/inventory/save-results`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            taskNo: currentTaskNo,
            inventoryResults: inventoryResults,
            userInfo: { userName, userLevel },
            calibrationRecords,
            manualCalibratedLocations: Array.from(manualCalibratedLocations),
          }),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "保存盘点结果失败");
      }

      const result = await response.json();

      if (result.code === 200) {
        toast.success("盘点结果保存成功！");

        // 下载Excel文件
        if (result.data.xlsxUrl) {
          const link = document.createElement("a");
          link.href = `${GATEWAY_URL}${result.data.xlsxUrl}`;
          link.download = `${currentTaskNo}.xlsx`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }

        // 记录完成盘点任务的操作日志
        const completedCount = inventoryItems.length;
        const abnormalCount = inventoryItems.filter(
          (item) => item.actualQuantity !== item.systemQuantity,
        ).length;

        await addOperationLog({
          operation_type: "inventory",
          user_id: authToken || undefined,
          user_name: userName || undefined,
          action: "完成盘点任务",
          target: currentTaskNo || "未知任务",
          status: "success",
          details: {
            task_no: currentTaskNo,
            completed_count: completedCount,
            abnormal_count: abnormalCount,
            completion_time: new Date().toISOString(),
            xlsx_file: result.data.xlsxFile,
          },
        });
      } else {
        throw new Error(result.message || "保存盘点结果失败");
      }
    } catch (error) {
      console.error("保存盘点结果失败:", error);
      toast.error(`保存盘点结果失败`);
    } finally {
      setIsSaving(false);
    }
  };

  // 完成盘点并创建下个盘点（先显示统计窗口，确认后执行保存）
  const handleSaveInventoryAndCreateNext = () => {
    // 检查是否有未识别的品规
    const unrecognizedItems = inventoryItems.filter(
      (item) => item.actualSpec === "未识别" || !item.actualSpec
    );

    if (unrecognizedItems.length > 0) {
      const unrecognizedLocations = unrecognizedItems
        .map((item) => item.locationName || item.binDesc)
        .join("、");
      toast.error(
        `以下储位品规未识别，请先校准：${unrecognizedLocations}`,
        { duration: 5000 }
      );
      return;
    }

    openStatisticsWithConfirm(doSaveInventoryAndCreateNext);
  };

  const doSaveInventoryAndCreateNext = async () => {
    if (!currentTaskNo) {
      toast.error("任务编号不存在");
      return;
    }

    if (!userName) {
      toast.error("用户未登录，请重新登录");
      return;
    }

    // 检查是否有未识别的品规
    const unrecognizedItems = inventoryItems.filter(
      (item) => item.actualSpec === "未识别" || !item.actualSpec
    );

    if (unrecognizedItems.length > 0) {
      const unrecognizedLocations = unrecognizedItems
        .map((item) => item.locationName || item.binDesc)
        .join("、");
      toast.error(
        `以下储位品规未识别，请先校准：${unrecognizedLocations}`,
        { duration: 5000 }
      );
      return;
    }

    setIsSavingAndCreating(true);

    try {
      // 1. 先保存盘点结果到历史记录
      const inventoryResults = inventoryItems.map((item) => ({
        binLocation: item.locationName,
        status: item.actualQuantity !== null ? "成功" : "异常",
        actualQuantity: item.actualQuantity,
        actualSpec: item.actualSpec || item.productName, // 实际品规（优先用校准值）
        specName: item.productName, // 系统品规名称
        systemQuantity: item.systemQuantity,
        difference:
          item.actualQuantity !== null
            ? item.actualQuantity - item.systemQuantity
            : 0,
        photo3dPath: item.photo3dPath || "",
        photoDepthPath: item.photoDepthPath || "",
        photoScan1Path: item.photoScan1Path || "",
        photoScan2Path: item.photoScan2Path || "",
      }));

      const saveResponse = await fetch(`${GATEWAY_URL}/api/inventory/save-results`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          taskNo: currentTaskNo,
          inventoryResults: inventoryResults,
          userInfo: { userName, userLevel },
          calibrationRecords,
          manualCalibratedLocations: Array.from(manualCalibratedLocations),
        }),
      });

      if (!saveResponse.ok) {
        const errorData = await saveResponse.json();
        throw new Error(errorData.detail || "保存盘点结果失败");
      }

      const saveResult = await saveResponse.json();
      if (saveResult.code !== 200) {
        throw new Error(saveResult.message || "保存盘点结果失败");
      }
      console.log("盘点结果已保存到历史记录:", saveResult.data?.xlsxFile);

      // 2. 更新 bins_data.xlsx 中的数量和品规
      const updateResponse = await fetch(`${GATEWAY_URL}/api/inventory/update-bins-data`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          inventoryItems: inventoryItems.map((item) => ({
            ...item,
            actualSpec: item.actualSpec || item.productName,
          })),
        }),
      });

      const updateResult = await updateResponse.json();
      if (updateResult.code === 200) {
        toast.success(updateResult.message);
      } else {
        console.warn("更新 bins_data.xlsx 失败:", updateResult.message);
        toast.error(updateResult.message || "更新失败");
        return;
      }

      // 跳转到创建下一个盘点页面
      toast.success("盘点结果已保存，即将跳转到创建盘点页面...");
      setTimeout(() => {
        navigate("/inventory/start");
      }, 1500);
    } catch (error) {
      console.error("保存或更新失败:", error);
      toast.error(`操作失败`);
    } finally {
      setIsSavingAndCreating(false);
    }
  };

  // 保存盘点结果到LMS
  const handleSaveInventoryToLMS = async () => {
    if (isSaving2LMS) return;

    try {
      setIsSaving2LMS(true);

      const inventoryResults = inventoryItems
        .filter((item) => item.actualQuantity !== null)
        .map((item) => ({
          taskDetailId: item.id,
          itemId: item.tobaccoCode || item.id.replace("INV", "ITEM"),
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
        } else {
          throw new Error(result.message || "上传失败");
        }
      } else {
        const errorText = await response.text();
        throw new Error(`LMS上传失败: ${errorText}`);
      }
    } catch (error) {
      console.error("上传盘点结果失败:", error);
      toast.error(`上传失败`);
    } finally {
      setIsSaving2LMS(false);
    }
  };

  // 盘点结果统计（使用当前 state 中的 inventoryItems）
  const handleInventoryStatistics = () => {
    if (inventoryItems.length === 0) {
      toast.error("没有盘点数据可供统计");
      return;
    }
    showStatisticsModal(inventoryItems);
  };

  // 一键重新盘点
  const [isRecounting, setIsRecounting] = useState(false);
  const handleRecountSelected = async () => {
    const selectedIds = Array.from(selectedRecountItems);
    if (selectedIds.length === 0) {
      toast.error("请先勾选需要重新盘点的库位");
      return;
    }

    const selectedItems = inventoryItems.filter((item) => selectedRecountItems.has(item.id));
    const binLocations = selectedItems.map((item) => item.locationName);
    const tobaccoCodes = selectedItems.map((item) => item.tobaccoCode);
    const rcsCodes = selectedItems.map((item) => item.rcsCode);

    // 生成独立的重新盘点任务号（避免与原任务状态冲突）
    const recountTaskId = `${currentTaskNo}_recount_${Date.now()}`;

    setIsRecounting(true);
    toast.info(`正在重新盘点 ${selectedIds.length} 个库位...`);

    // 清空选中项的盘点结果，以便重新显示
    const clearedItems = inventoryItems.map((item) =>
      selectedRecountItems.has(item.id)
        ? { ...item, actualQuantity: null as number | null, actualSpec: undefined as string | undefined }
        : item,
    );
    setInventoryItems(clearedItems);

    try {
      const authToken = sessionStorage.getItem('authToken');
      const taskResponse = await fetch(`${GATEWAY_URL}/api/inventory/start-inventory`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { 'authToken': authToken } : {}),
        },
        body: JSON.stringify({
          taskNo: currentTaskNo,
          recountTaskId,
          binLocations,
          tobaccoCode: tobaccoCodes,
          rcsCode: rcsCodes,
          inventoryItems: selectedItems,
        }),
      });

      if (!taskResponse.ok) {
        const errorData = await taskResponse.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || "重新盘点任务启动失败");
      }

      const taskData = await taskResponse.json();
      // 使用后端返回的 actualTaskNo 进行轮询
      const pollTaskNo = taskData.data?.actualTaskNo || recountTaskId;
      const taskStatus = taskData.data?.status;

      const recountBinSet = new Set(binLocations);

      const onRecountComplete = (allResults: any[]) => {
        // 过滤出本次重新盘点的库位结果
        const recountResults = allResults.filter((r: any) => recountBinSet.has(r.binLocation));

        const failedBins: Array<{ binLocation: string; error: string }> = [];
        const newItems = clearedItems.map((item) => {
          if (!recountBinSet.has(item.locationName)) return item;
          const ir = recountResults.find((r: any) => r.binLocation === item.locationName);
          if (!ir) return item;
          if (ir.status === "异常") {
            failedBins.push({ binLocation: ir.binLocation, error: ir.error || "未知错误" });
          }
          return {
            ...item,
            actualQuantity: ir.status === "异常" ? -1 : (ir.actualQuantity ?? item.actualQuantity),
            actualSpec: ir.actualSpec || item.actualSpec,
            photo3dPath: ir.photo3dPath || item.photo3dPath,
            photoDepthPath: ir.photoDepthPath || item.photoDepthPath,
            photoScan1Path: ir.photoScan1Path || item.photoScan1Path,
            photoScan2Path: ir.photoScan2Path || item.photoScan2Path,
          };
        });

        setInventoryItems(newItems);
        setIsRecounting(false);
        setSelectedRecountItems(new Set());

        if (failedBins.length > 0) {
          setFailedBinsModal({
            open: true,
            bins: failedBins,
            onOk: () => setFailedBinsModal((prev) => ({ ...prev, open: false })),
          });
          toast.error(`${failedBins.length} 个库位盘点失败`);
        } else {
          toast.success(`重新盘点完成，已更新 ${selectedIds.length} 个库位`);
          showStatisticsModal(newItems);
        }

        // 合并保存到原任务号的 Excel 文件
        saveInventoryMerge(recountResults);
      };

      if (taskStatus === "completed" || taskStatus === "partial") {
        const resultsResponse = await fetch(
          `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(pollTaskNo)}`,
        );
        const resultsData = await resultsResponse.json();
        onRecountComplete(resultsData.data?.inventoryResults || []);
      } else {
        // 轮询等待任务完成
        const pollIntervalId = setInterval(async () => {
          try {
            const progressResponse = await fetch(
              `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(pollTaskNo)}`,
            );
            if (!progressResponse.ok) return;
            const progressResult = await progressResponse.json();
            if (progressResult.code !== 200) return;
            const status = progressResult.data?.status;

            const currentStep = progressResult.data?.current_step || 0;
            const totalSteps = progressResult.data?.total_steps || 1;
            setProgress(Math.round((currentStep / totalSteps) * 100));

            if (status === "completed" || status === "partial") {
              clearInterval(pollIntervalId);
              const resultsResponse = await fetch(
                `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(pollTaskNo)}`,
              );
              const resultsData = await resultsResponse.json();
              onRecountComplete(resultsData.data?.inventoryResults || []);
              return;
            }

            if (status === "failed") {
              clearInterval(pollIntervalId);
              setIsRecounting(false);
              setSelectedRecountItems(new Set());
              setTaskErrorModal({
                open: true,
                errorType: (progressResult.data?.error_type as "rcs" | "camera" | "other") || "other",
                message: progressResult.data?.message || "盘点任务失败",
                onOk: () => setTaskErrorModal((prev) => ({ ...prev, open: false })),
              });
              return;
            }
          } catch (err) {
            console.error("轮询进度出错:", err);
          }
        }, 2000);
      }
    } catch (error) {
      console.error("重新盘点失败:", error);
      toast.error(`重新盘点失败: ${error instanceof Error ? error.message : "未知错误"}`);
      setIsRecounting(false);
      setSelectedRecountItems(new Set());
    }
  };

  // 合并保存（更新现有文件中的指定储位）
  const saveInventoryMerge = async (recountResults: any[]) => {
    try {
      const saveResponse = await fetch(`${GATEWAY_URL}/api/inventory/save-results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          taskNo: currentTaskNo,
          inventoryResults: recountResults.map((ir) => ({
            binLocation: ir.binLocation,
            status: ir.status,
            actualQuantity: ir.actualQuantity,
            actualSpec: ir.actualSpec,
            specName: ir.specName || ir.binLocation,
            systemQuantity: ir.systemQuantity,
            difference: ir.actualQuantity != null && ir.systemQuantity != null
              ? Number(ir.actualQuantity) - Number(ir.systemQuantity) : 0,
            photo3dPath: ir.photo3dPath || "",
            photoDepthPath: ir.photoDepthPath || "",
            photoScan1Path: ir.photoScan1Path || "",
            photoScan2Path: ir.photoScan2Path || "",
          })),
          userInfo: { userName, userLevel },
          calibrationRecords,
          manualCalibratedLocations: Array.from(manualCalibratedLocations),
          merge: true,
        }),
      });
      if (!saveResponse.ok) {
        const errData = await saveResponse.json().catch(() => ({}));
        toast.error(errData.detail || "合并保存失败");
      }
    } catch (err) {
      console.error("合并保存失败:", err);
    }
  };

  // 核心统计函数，接受 items 作为参数，避免闭包陷阱
  const showStatisticsModal = (items: InventoryItem[]) => {
    if (items.length === 0) {
      toast.error("没有盘点数据可供统计");
      return;
    }

    const abnormalTasks = items
      .filter((item) => {
        if (item.actualQuantity === null) return false;
        // 人工校准过的不计入差异（视为已处理）
        if (manualCalibratedLocations.has(item.locationName)) return false;
        const qtyWrong = item.actualQuantity !== item.systemQuantity;
        const specUnrecognized = item.actualSpec === "未识别";
        const specMismatch = !!item.actualSpec && item.actualSpec !== item.productName;
        return qtyWrong || specUnrecognized || specMismatch;
      })
      .map((item) => ({
        taskNo: item.taskNo,
        location: item.locationName,
        expected: item.systemQuantity,
        actual: item.actualQuantity,
      }));

    const totalItems = items.length;
    const diffRate = totalItems > 0 ? (abnormalTasks.length / totalItems) * 100 : 0;
    let totalTime = statisticsData.totalTime;
    if (!isTaskCompleted && taskStartTime) {
      totalTime = Date.now() - taskStartTime;
    }

    setStatisticsData({ totalTime, diffRate, abnormalTasks });
    setPendingSaveAction(null);
    setIsStatisticsModalOpen(true);
  };

  // 带确认回调的统计（用于"保存并进行下次盘点"场景）
  const openStatisticsWithConfirm = (onConfirm: () => void) => {
    showStatisticsModal(inventoryItems);
    setPendingSaveAction(() => onConfirm);
  };
  // 处理返回
  const handleBack = () => {
    navigate("/inventory/start");
  };

  // 取消任务
  const handleCancelTask = async () => {
    try {
      const res = await fetch(
        `${GATEWAY_URL}/api/inventory/cancel-inventory?taskNo=${encodeURIComponent(currentTaskNo)}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.code === 200) {
        localStorage.removeItem("currentTaskManifest");
        localStorage.removeItem("currentTaskNo");
        toast.success("任务已取消");
        navigate("/inventory/start");
      }
    } catch (err) {
      toast.error("取消任务失败");
    }
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
            <div className="text-right hidden md:block">
              <p className="text-sm font-medium text-gray-700">
                欢迎，{userName || "用户"}
              </p>
              <p className="text-xs text-gray-500">
                权限：{userLevel === "admin" ? "管理员" : "操作员"}
              </p>
            </div>

            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                userLevel === "admin"
                  ? "bg-purple-100 text-purple-600"
                  : "bg-blue-100 text-blue-600"
              }`}
            >
              <i
                className={`fa-solid ${
                  userLevel === "admin" ? "fa-user-shield" : "fa-user"
                }`}
              ></i>
            </div>

            <button
              onClick={handleBack}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-arrow-left mr-2"></i>返回
            </button>

            {/* 取消任务按钮（任务进行中时显示） */}
            {!isTaskCompleted && currentTaskManifest && (
              <button
                onClick={handleCancelTask}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-all flex items-center"
              >
                <i className="fa-solid fa-stop mr-2"></i>取消任务
              </button>
            )}
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-green-800 flex items-center">
            盘点任务
          </h2>
        </div>

        {/* 网格布局 */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* 左侧内容区域 - 占据3列 */}
          <div className="lg:col-span-3 flex flex-col gap-8">
            {/* 盘点进度区域 */}
            <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center space-x-4">
                  <h3 className="text-xl font-bold text-green-800 flex items-center">
                    <i className="fa-solid fa-chart-line mr-2 text-green-600"></i>
                    盘点进度
                  </h3>
                  {currentTaskNo && (
                    <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                      任务编号: {currentTaskNo}
                    </span>
                  )}
                </div>

                {/* 在顶部导航栏或进度区域添加 WebSocket 状态指示器 */}
                <div className="flex items-center space-x-4">
                  <div className="flex items-center">
                    {/* <div
className={`w-3 h-3 rounded-full mr-2 ${
isWebSocketConnected
? "bg-green-500 animate-pulse"
: "bg-red-500"
}`}
></div>
<span className="text-sm">
{isWebSocketConnected ? "服务器已连接" : "服务器未连接"}
</span> */}
                  </div>

                  {/*{!isWebSocketConnected && (
<button
onClick={handleReconnectWebSocket}
className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
>
重新连接
</button>
)}*/}
                </div>

                {/* <div className="flex items-center space-x-4">
<button
onClick={handleDisconnectWebSocket}
className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
>
取消连接
</button>
</div> */}

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
                {currentTaskManifest && (
                  <button
                    onClick={handleStartCountingTask}
                    disabled={isStartingTask || isTaskCompleted}
                    className={`px-4 py-2 rounded-lg transition-all flex items-center ${
                      isTaskCompleted
                        ? "bg-green-600 text-white cursor-default"
                        : isStartingTask
                          ? "bg-orange-400 text-white cursor-not-allowed"
                          : "bg-orange-600 hover:bg-orange-700 text-white"
                    }`}
                  >
                    {isStartingTask ? (
                      <>
                        <i className="fas fa-spinner fa-spin mr-2"></i>进行中...
                      </>
                    ) : isTaskCompleted ? (
                      <>
                        <i className="fa-solid fa-check mr-2"></i>任务已完成
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-play mr-2"></i>下发盘点任务
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* 盘点数据区域 */}
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
              <div className="flex-1 p-1">
                {inventoryItems.length > 0 ? (
                  <div className="h-[400px] overflow-y-auto overflow-x-auto border border-gray-200 rounded-lg">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0 z-10">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <input
                              type="checkbox"
                              checked={selectedRecountItems.size === inventoryItems.length && inventoryItems.length > 0}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedRecountItems(new Set(inventoryItems.map((item) => item.id)));
                                } else {
                                  setSelectedRecountItems(new Set());
                                }
                              }}
                              className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                            />
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            品规名称
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            储位名称
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            实际品规
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            校准
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            库存数量（件）
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            实际数量（件）
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            差异
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            校准
                          </th>

                          {/* <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
手动抓图
</th>*/}
                          {/* <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            计算
                          </th> */}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryItems.map((item, index) => {
                          // 安全地获取实际数量
                          const actualQuantity =
                            item.actualQuantity !== undefined &&
                            item.actualQuantity !== null
                              ? Number(item.actualQuantity)
                              : null;

                          const systemQuantity =
                            item.systemQuantity !== undefined &&
                            item.systemQuantity !== null
                              ? Number(item.systemQuantity)
                              : null;

                          // 计算差异
                          const difference =
                            actualQuantity !== null && systemQuantity !== null
                              ? actualQuantity - systemQuantity
                              : null;

                          const hasDifference =
                            difference !== null && difference !== 0;
                          const isSelected = selectedRowIndex === index;

                          const isSpecUnrecognized =
                            item.actualSpec === "未识别";
                          // 品规检测出不匹配（但不是"未识别"），说明检测到了但与系统品规不一致
                          const isSpecMismatch =
                            item.actualSpec &&
                            item.actualSpec !== item.productName &&
                            !isSpecUnrecognized;
                          const hasSpecIssue = isSpecUnrecognized || isSpecMismatch;
                          const isManuallyCalibrated = manualCalibratedLocations.has(item.locationName);

                          return (
                            <tr
                              key={item.id}
                              className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                                isSelected
                                  ? "bg-blue-50 border-l-4 border-blue-500"
                                  : ""
                              }`}
                              onClick={() => handleRowClick(item.taskNo, String(item.binDesc))}
                            >
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                <input
                                  type="checkbox"
                                  checked={selectedRecountItems.has(item.id)}
                                  onChange={(e) => {
                                    e.stopPropagation();
                                    setSelectedRecountItems((prev) => {
                                      const next = new Set(prev);
                                      if (e.target.checked) {
                                        next.add(item.id);
                                      } else {
                                        next.delete(item.id);
                                      }
                                      return next;
                                    });
                                  }}
                                  className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.productName || "未知品规"}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.locationName}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {actualQuantity !== null ? (
                                  <div className="flex items-center">
                                    <span className={`font-medium ${hasSpecIssue ? "text-red-600" : "text-green-600"}`}>
                                      {item.actualSpec || item.productName}
                                    </span>
                                    {hasSpecIssue ? (
                                      <i className="fa-solid fa-circle-xmark ml-2 text-red-500"></i>
                                    ) : (
                                      <i className="fa-solid fa-check-circle ml-2 text-green-500"></i>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">待识别</span>
                                )}
                              </td>
                              {/* 校准列 - 只修改实际品规 */}
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {editingSpecId === item.id ? (
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="text"
                                      value={editSpecValue}
                                      onChange={(e) => setEditSpecValue(e.target.value)}
                                      className="w-32 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                      placeholder="输入实际品规"
                                      onClick={(e) => e.stopPropagation()}
                                      autoFocus
                                    />
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (editSpecValue.trim()) {
                                          setInventoryItems((prevItems) =>
                                            prevItems.map((i) =>
                                              i.id === item.id
                                                ? { ...i, actualSpec: editSpecValue.trim() }
                                                : i
                                            )
                                          );
                                          toast.success("实际品规已校准");
                                        }
                                        setCalibrationRecords((prev) => ({
                                          ...prev,
                                          [item.locationName]: {
                                            ...prev[item.locationName],
                                            specModified: true,
                                          },
                                        }));
                                        setManualCalibratedLocations((prev) => new Set([...prev, item.locationName]));
                                        setEditingSpecId(null);
                                        setEditSpecValue("");
                                      }}
                                      className="p-1.5 text-green-600 hover:bg-green-50 rounded-md transition-colors"
                                      title="确认"
                                    >
                                      <i className="fa-solid fa-check"></i>
                                    </button>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setEditingSpecId(null);
                                        setEditSpecValue("");
                                      }}
                                      className="p-1.5 text-red-500 hover:bg-red-50 rounded-md transition-colors"
                                      title="取消"
                                    >
                                      <i className="fa-solid fa-times"></i>
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingSpecId(item.id);
                                      setEditSpecValue(item.actualSpec || item.productName || "");
                                    }}
                                    className="px-3 py-1.5 text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-md transition-colors flex items-center gap-1.5 border border-blue-200"
                                    title="校准实际品规"
                                  >
                                    <i className="fa-solid fa-pen-to-square"></i>
                                    校准
                                  </button>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {systemQuantity !== null ? systemQuantity : 0}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {actualQuantity !== null ? (
                                  <div className="flex items-center">
                                    <span className={`font-medium ${hasDifference ? "text-red-600" : "text-green-600"}`}>
                                      {actualQuantity}
                                    </span>
                                    {hasDifference ? (
                                      <i className="fa-solid fa-circle-xmark ml-2 text-red-500"></i>
                                    ) : (
                                      <i className="fa-solid fa-check-circle ml-2 text-green-500"></i>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">待计算</span>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {(() => {
                                  const hasDiff = difference !== null && difference !== 0;

                                  return difference !== null ? (
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`text-sm font-medium ${
                                          isManuallyCalibrated
                                            ? "text-yellow-600"
                                            : (hasSpecIssue || hasDiff)
                                              ? "text-red-600"
                                              : "text-green-600"
                                        }`}
                                      >
                                        {isManuallyCalibrated ? (
                                          <>
                                            <i className="fa-solid fa-pen-to-square mr-1"></i>
                                            已校准
                                          </>
                                        ) : hasSpecIssue ? (
                                          <>
                                            <i className="fa-solid fa-exclamation-circle mr-1"></i>
                                            品规不一致
                                          </>
                                        ) : hasDiff ? (
                                          <>
                                            <i className="fa-solid fa-exclamation-circle mr-1"></i>
                                            {difference > 0 ? `+${difference}` : difference}
                                            <span className="text-xs text-gray-400 ml-1">件</span>
                                          </>
                                        ) : (
                                          <>
                                            <i className="fa-solid fa-check-circle mr-1"></i>
                                            一致
                                          </>
                                        )}
                                      </span>
                                    </div>
                                  ) : (
                                    <span className="text-sm text-gray-400">待计算</span>
                                  );
                                })()}
                              </td>
                              {/* 差异校准列 */}
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {editingDiffId === item.id ? (
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="number"
                                      value={editDiffValue}
                                      onChange={(e) => setEditDiffValue(e.target.value)}
                                      className="w-20 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                      placeholder="校准数量"
                                      onClick={(e) => e.stopPropagation()}
                                      autoFocus
                                    />
                                    <span className="text-xs text-gray-500">件</span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        const val = editDiffValue ? parseInt(editDiffValue, 10) : 0;
                                        // 直接更新 actualQuantity，差异会自动重新计算
                                        setInventoryItems((prevItems) =>
                                          prevItems.map((i) =>
                                            i.id === item.id
                                              ? { ...i, actualQuantity: val }
                                              : i
                                          )
                                        );
                                        setEditingDiffId(null);
                                        setEditDiffValue("");
                                        toast.success("实际数量已校准，差异已重新计算");
                                        setCalibrationRecords((prev) => ({
                                          ...prev,
                                          [item.locationName]: {
                                            ...prev[item.locationName],
                                            quantityModified: true,
                                          },
                                        }));
                                        setManualCalibratedLocations((prev) => new Set([...prev, item.locationName]));
                                      }}
                                      className="p-1.5 text-green-600 hover:bg-green-50 rounded-md transition-colors"
                                      title="确认"
                                    >
                                      <i className="fa-solid fa-check"></i>
                                    </button>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setEditingDiffId(null);
                                        setEditDiffValue("");
                                      }}
                                      className="p-1.5 text-red-500 hover:bg-red-50 rounded-md transition-colors"
                                      title="取消"
                                    >
                                      <i className="fa-solid fa-times"></i>
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingDiffId(item.id);
                                      // 默认显示当前实际数量
                                      setEditDiffValue(String(actualQuantity ?? systemQuantity ?? 0));
                                    }}
                                    className="px-3 py-1.5 text-xs bg-orange-50 hover:bg-orange-100 text-orange-600 rounded-md transition-colors flex items-center gap-1.5 border border-orange-200"
                                    title="校准实际数量"
                                  >
                                    <i className="fa-solid fa-pen-to-square"></i>
                                    校准
                                  </button>
                                )}
                              </td>
                              {/* <td className="px-6 py-4 whitespace-nowrap">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation(); // 阻止事件冒泡，避免触发行点击事件

                                    handleCalculate(
                                      item.taskNo,
                                      String(item.binDesc),
                                      index,
                                    );
                                  }}
                                  disabled={!isTaskStarted}
                                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center justify-center ${
                                    isTaskStarted
                                      ? "bg-blue-600 hover:bg-blue-700 text-white"
                                      : "bg-gray-300 text-gray-500 cursor-not-allowed"
                                  }`}
                                >
                                  <i
                                    className={`fa-solid ${
                                      isTaskStarted ? "fa-calculator" : "fa-ban"
                                    } mr-1`}
                                  ></i>
                                  计算
                                </button>
                              </td> */}
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
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
                <span className="text-sm text-gray-500">
                  已选择 <span className="font-bold text-green-700">{selectedRecountItems.size}</span> 个库位待重新盘点
                </span>
                <div className="flex gap-4">
                  <button
                    onClick={handleRecountSelected}
                    disabled={isRecounting || selectedRecountItems.size === 0}
                    className={`px-6 py-3 rounded-lg transition-colors flex items-center ${
                      isRecounting || selectedRecountItems.size === 0
                        ? "bg-gray-400 cursor-not-allowed text-white"
                        : "bg-orange-600 hover:bg-orange-700 text-white"
                    }`}
                  >
                    {isRecounting ? (
                      <>
                        <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                        重新盘点中...
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-rotate mr-2"></i>
                        一键重新盘点
                      </>
                    )}
                  </button>
                </div>
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
                  onClick={handleSaveInventoryAndCreateNext}
                  disabled={isSavingAndCreating}
                  className={`px-6 py-3 rounded-lg transition-colors flex items-center ${
                    !isTaskCompleted
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700 text-white"
                  }`}
                >
                  {isSavingAndCreating ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      处理中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-plus mr-2"></i>
                      完成并创建下个盘点
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </div>

          {/* 右侧观察窗口 - 占据1列 */}
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

              {/* 观察窗口内容 */}

              <div className="flex-1 p-4 flex flex-col gap-4">
                {/* 上半部分 - 显示当前组的上方图片 */}
                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
                    {isCapture ? (
                      <>
                        {imageLoading ? (
                          // 加载状态
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
                          </div>
                        ) : photoGroups[currentGroupIndex]?.top ? (
                          // 成功加载图片
                          <>
                            <img
                              src={photoGroups[currentGroupIndex].top}
                              alt={currentGroupIndex === 0 ? "3D相机-主图" : "扫码相机-扫码图1"}
                              className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 cursor-zoom-in"
                              onLoad={handleImageLoad}
                              onError={handleImageError}
                              onClick={() => setLightboxImage(photoGroups[currentGroupIndex].top)}
                            />
                            <div className="absolute top-2 left-2 bg-green-700 text-white text-xs font-bold px-2 py-1 rounded-full">
                              {currentGroupIndex === 0 ? "主图" : "扫码图1"}
                            </div>
                          </>
                        ) : (
                          // 无图片状态
                          <div className="flex flex-col items-center justify-center h-full text-center p-4">
                            <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                              <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                            </div>
                            <p className="text-gray-500 text-sm">
                              等待照片加载...
                            </p>
                          </div>
                        )}
                      </>
                    ) : (
                      // 未连接状态
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                          <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                        </div>
                        <p className="text-gray-500 text-sm">画面未连接</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 下半部分 - 显示当前组的下方图片 */}
                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
                    {isCapture && photoGroups[currentGroupIndex]?.bottom ? (
                      <>
                        <img
                          src={photoGroups[currentGroupIndex].bottom}
                          alt={currentGroupIndex === 0 ? "3D相机-深度图" : "扫码相机-扫码图2"}
                          className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 cursor-zoom-in"
                          onLoad={handleImageLoad}
                          onError={handleImageError}
                          onClick={() => setLightboxImage(photoGroups[currentGroupIndex].bottom)}
                        />
                        <div className="absolute top-2 left-2 bg-blue-700 text-white text-xs font-bold px-2 py-1 rounded-full">
                          {currentGroupIndex === 0 ? "深度图" : "扫码图2"}
                        </div>
                      </>
                    ) : (
                      // 无图片状态
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                          <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                        </div>
                        <p className="text-gray-500 text-sm">等待照片加载...</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 照片组切换按钮 */}
                <div className="flex justify-center gap-2">
                  {[
                    { index: 0, label: "3D相机", subLabel: "主图/深度图" },
                    { index: 1, label: "扫码相机", subLabel: "扫码图1/图2" },
                  ].map(({ index, label, subLabel }) => {
                    const group = photoGroups[index];
                    const hasPhoto = group.top || group.bottom;
                    return (
                      <button
                        key={index}
                        onClick={() => setCurrentGroupIndex(index)}
                        disabled={!hasPhoto}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          currentGroupIndex === index
                            ? "bg-green-700 text-white"
                            : hasPhoto
                              ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
                              : "bg-gray-100 text-gray-400 cursor-not-allowed"
                        }`}
                      >
                        <span>{label}</span>
                        {hasPhoto && (
                          <span className="block text-xs opacity-75 font-normal">
                            {subLabel}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

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
                <div className={`rounded-lg p-4 text-center ${statisticsData.diffRate <= 10 ? "bg-green-50" : statisticsData.diffRate <= 50 ? "bg-yellow-50" : "bg-red-50"}`}>
                  <div className={`text-2xl font-bold ${statisticsData.diffRate <= 10 ? "text-green-700" : statisticsData.diffRate <= 50 ? "text-yellow-700" : "text-red-700"}`}>
                    {statisticsData.diffRate.toFixed(1)}%
                  </div>
                  <div className={`text-sm mt-1 ${statisticsData.diffRate <= 10 ? "text-green-600" : statisticsData.diffRate <= 50 ? "text-yellow-600" : "text-red-600"}`}>差异率</div>
                </div>
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-red-700">
                    {statisticsData.abnormalTasks.length}
                  </div>
                  <div className="text-sm text-red-600 mt-1">差异任务</div>
                </div>
              </div>

              {/* 差异任务列表 */}
              {statisticsData.abnormalTasks.length > 0 ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                    <h4 className="font-semibold text-gray-800 flex items-center">
                      <i className="fa-solid fa-exclamation-triangle text-orange-500 mr-2"></i>
                      差异任务详情
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
                  <p className="text-green-600">所有任务均无差异</p>
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
                        statisticsData.diffRate <= 10
                          ? "text-green-600"
                          : statisticsData.diffRate <= 50
                            ? "text-yellow-600"
                            : "text-red-600"
                      }`}
                    >
                      总体评价:{" "}
                      {statisticsData.diffRate <= 10
                        ? "正常"
                        : statisticsData.diffRate <= 50
                          ? "偏差较大"
                          : "严重异常"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 模态框底部 */}
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
              {pendingSaveAction ? (
                <>
                  <button
                    onClick={() => {
                      setIsStatisticsModalOpen(false);
                      setPendingSaveAction(null);
                    }}
                    className="bg-gray-400 hover:bg-gray-500 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
                  >
                    <i className="fa-solid fa-arrow-left mr-2"></i>返回
                  </button>
                  <button
                    onClick={() => {
                      setIsStatisticsModalOpen(false);
                      setPendingSaveAction(null);
                      pendingSaveAction();
                    }}
                    className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
                  >
                    <i className="fa-solid fa-check mr-2"></i>确认
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setIsStatisticsModalOpen(false)}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
                >
                  <i className="fa-solid fa-check mr-2"></i>确认
                </button>
              )}
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

      {/* 盘点失败库位提示弹窗 */}
      <Modal
        title="⚠️ 盘点失败库位"
        open={failedBinsModal.open}
        onOk={failedBinsModal.onOk}
        onCancel={failedBinsModal.onOk}
        okText="确认"
        cancelText=""
        width={500}
        footer={[
          <button
            key="ok"
            onClick={failedBinsModal.onOk}
            className="px-4 py-2 bg-green-700 text-white rounded hover:bg-green-800 transition-colors"
          >
            确认
          </button>,
        ]}
      >
        <div className="py-2">
          <p className="mb-3 text-gray-600">
            以下 {failedBinsModal.bins.length} 个库位盘点失败，已记录为盘点失败：
          </p>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 max-h-64 overflow-y-auto">
            {failedBinsModal.bins.map((bin, index) => (
              <div key={index} className="py-1 border-b border-red-100 last:border-0">
                <span className="font-medium text-red-700">{bin.binLocation}</span>
                <span className="text-gray-500 text-sm ml-2">— {bin.error}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-gray-500 text-sm">
            点击确认后，失败库位将以"盘点失败"记录，实际数量记为0，品规记为"未识别"。
          </p>
        </div>
      </Modal>

      {/* 系统离线提示弹窗 */}
      <Modal
        title={
          systemOfflineModal.message?.includes("RCS")
            ? "⚠️ RCS 离线"
            : "⚠️ 相机离线"
        }
        open={systemOfflineModal.open}
        onCancel={systemOfflineModal.onOk}
        footer={[
          <button
            key="ok"
            onClick={systemOfflineModal.onOk}
            className="px-4 py-2 bg-blue-700 text-white rounded hover:bg-blue-800 transition-colors"
          >
            确认
          </button>,
        ]}
        width={500}
      >
        <div className="py-2">
          <p className="mb-3 text-gray-700">无法发起盘点任务，以下系统不在线：</p>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 font-medium whitespace-pre-line">
              {systemOfflineModal.message.replace("系统离线，无法发起盘点：", "")}
            </p>
          </div>
          {systemOfflineModal.message?.includes("RCS") && (
            <div className="mt-3 text-gray-600 text-sm">
              <p className="mb-1 font-medium">排查步骤：</p>
              <ul className="list-disc list-inside space-y-1 text-gray-500">
                <li>检查 RCS 服务（端口 4001）是否正常运行</li>
                <li>检查网络连接是否正常</li>
                <li>重启 RCS 服务后重试</li>
              </ul>
            </div>
          )}
          {systemOfflineModal.message?.includes("RCS") === false && (
            <div className="mt-3 text-gray-600 text-sm">
              <p className="mb-1 font-medium">排查步骤：</p>
              <ul className="list-disc list-inside space-y-1 text-gray-500">
                <li>检查相机 IP（10.16.82.180/181/182）是否可达</li>
                <li>检查相机网线连接是否正常</li>
                <li>确认相机已通电且指示灯正常</li>
              </ul>
            </div>
          )}
        </div>
      </Modal>

      {/* 图片放大镜模态框 */}
      {lightboxImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={() => setLightboxImage(null)}
        >
          <button
            className="absolute top-4 right-4 text-white text-3xl hover:text-gray-300 z-10 w-10 h-10 flex items-center justify-center"
            onClick={() => setLightboxImage(null)}
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
          <img
            src={lightboxImage}
            alt="放大图片"
            className="max-w-[95vw] max-h-[95vh] object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* 下发失败提示弹窗 */}
      <Modal
        title={
          taskErrorModal.errorType === "rcs"
            ? "⚠️ RCS 连接失败"
            : taskErrorModal.errorType === "camera"
            ? "⚠️ 相机连接失败"
            : "⚠️ 盘点任务下发失败"
        }
        open={taskErrorModal.open}
        onCancel={taskErrorModal.onOk}
        footer={[
          <button
            key="ok"
            onClick={taskErrorModal.onOk}
            className="px-4 py-2 bg-red-700 text-white rounded hover:bg-red-800 transition-colors"
          >
            确认
          </button>,
        ]}
        width={500}
      >
        <div className="py-2">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 font-medium whitespace-pre-line">
              {taskErrorModal.message}
            </p>
          </div>
          {taskErrorModal.errorType === "rcs" && (
            <div className="mt-3 text-gray-600 text-sm">
              <p className="mb-1 font-medium">排查步骤：</p>
              <ul className="list-disc list-inside space-y-1 text-gray-500">
                <li>检查 RCS 服务（端口 4001）是否正常运行</li>
                <li>检查网络连接是否正常</li>
                <li>重启 RCS 服务后重试</li>
              </ul>
            </div>
          )}
          {taskErrorModal.errorType === "camera" && (
            <div className="mt-3 text-gray-600 text-sm">
              <p className="mb-1 font-medium">排查步骤：</p>
              <ul className="list-disc list-inside space-y-1 text-gray-500">
                <li>检查相机 IP（10.16.82.180/181/182）是否可达</li>
                <li>检查相机网线连接是否正常</li>
                <li>确认相机已通电且指示灯正常</li>
              </ul>
            </div>
          )}
          {taskErrorModal.errorType === "other" && (
            <p className="mt-3 text-gray-500 text-sm">
              请检查上述错误信息，或联系技术支持。
            </p>
          )}
        </div>
      </Modal>
    </div>
  );
}
