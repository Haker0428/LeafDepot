/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-21 19:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-19 02:52:48
 * @FilePath: /LeafDepot/web/src/pages/InventoryProgress.tsx
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "@/config/ip_address";
import { useAuth } from "@/contexts/authContext";

import { v4 as uuidv4 } from "uuid";
import {
  CreateTaskGroupRequest,
  TaskData,
  TargetRoute,
  ApiResponse,
} from "../hooks/types";

import img1 from "@/public/original/1.jpg";
import img2 from "@/public/original/2.jpg";
import img3 from "@/public/original/3.jpg";
import img4 from "@/public/original/4.jpg";
import img5 from "@/public/original/5.jpg";
import img6 from "@/public/original/6.jpg";
import img7 from "@/public/original/7.jpg";
import img8 from "@/public/original/8.jpg";
import img9 from "@/public/original/9.jpg";
import img10 from "@/public/original/10.jpg";
import img11 from "@/public/original/11.jpg";
import img12 from "@/public/original/12.jpg";
import img13 from "@/public/original/13.jpg";
import img14 from "@/public/original/14.jpg";
import img15 from "@/public/original/15.jpg";
import img16 from "@/public/original/16.jpg";
import img17 from "@/public/original/17.jpg";

import img1out from "@/public/postprocess/1out.jpg";
import img2out from "@/public/postprocess/2out.jpg";
import img3out from "@/public/postprocess/3out.jpg";
import img4out from "@/public/postprocess/4out.jpg";
import img5out from "@/public/postprocess/5out.jpg";
import img6out from "@/public/postprocess/6out.jpg";
import img7out from "@/public/postprocess/7out.jpg";
import img8out from "@/public/postprocess/8out.jpg";
import img9out from "@/public/postprocess/9out.jpg";
import img10out from "@/public/postprocess/10out.jpg";
import img11out from "@/public/postprocess/11out.jpg";
import img12out from "@/public/postprocess/12out.jpg";
import img13out from "@/public/postprocess/13out.jpg";
import img14out from "@/public/postprocess/14out.jpg";
import img15out from "@/public/postprocess/15out.jpg";
import img16out from "@/public/postprocess/16out.jpg";
import img17out from "@/public/postprocess/17out.jpg";
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

// 新增：计算准确率函数
const calculateAccuracyRate = (
  items: InventoryItem[],
  abnormalTasks: any[]
) => {
  const totalItems = items.length;
  const accurateItems = totalItems - abnormalTasks.length;
  return (accurateItems / totalItems) * 100;
};

export default function InventoryProgress() {
  const { authToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
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
  const [currentExecutingTaskIndex, setCurrentExecutingTaskIndex] = useState<
    number | null
  >(null);

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
  //   if (!currentTaskNo) {
  //     toast.error("没有当前任务，无法连接 WebSocket");
  //     return;
  //   }

  //   // 构建 WebSocket URL，根据你的网关地址调整
  //   const wsUrl = `ws://localhost:8000/ws/inventory/${currentTaskNo}`;
  //   console.log("尝试连接 WebSocket:", wsUrl);

  //   const ws = new WebSocket(wsUrl);

  //   ws.onopen = () => {
  //     console.log("WebSocket 连接成功");
  //     setIsWebSocketConnected(true);
  //     toast.success("已连接到盘点服务器");
  //   };

  //   ws.onmessage = (event) => {
  //     try {
  //       const data = JSON.parse(event.data);
  //       console.log("收到 WebSocket 消息:", data);

  //       if (data.type === "csv_data") {
  //         handleReceivedCSVData(data);
  //       }
  //     } catch (error) {
  //       console.error("解析 WebSocket 消息失败:", error);
  //     }
  //   };

  //   ws.onerror = (error) => {
  //     console.error("WebSocket 连接错误:", error);
  //     toast.error("WebSocket 连接错误");
  //   };

  //   ws.onclose = (event) => {
  //     console.log("WebSocket 连接关闭:", event.code, event.reason);
  //     setIsWebSocketConnected(false);

  //     // 如果不是正常关闭，尝试重新连接
  //     if (event.code !== 1000) {
  //       toast.warning("WebSocket 连接断开，正在重新连接...");
  //       setTimeout(() => {
  //         connectWebSocket();
  //       }, 3000);
  //     }
  //   };

  //   0;

  //   setWebSocket(ws);
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
            item.taskNo === data.taskNo && item.binLocation === data.binLocation
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
          data.binLocation
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
        `库位 ${data.binLocation} 数据更新成功: 数量=${data.number || 0}`
      );
    } else {
      toast.error(`库位 ${data.binLocation} 数据处理失败: ${data.message}`);
    }
  };

  useEffect(() => {
    const completedCount = inventoryItems.filter(
      (item) => item.actualQuantity !== null
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

        // 计算异常任务
        const abnormalTasks = inventoryItems
          .filter(
            (item) =>
              item.actualQuantity !== null &&
              item.actualQuantity !== item.systemQuantity
          )
          .map((item) => ({
            taskNo: item.taskNo,
            location: item.locationName,
            expected: item.systemQuantity,
            actual: item.actualQuantity,
          }));

        // 计算准确率
        const accurateItems = inventoryItems.length - abnormalTasks.length;
        const accuracyRate =
          inventoryItems.length > 0
            ? (accurateItems / inventoryItems.length) * 100
            : 0;

        // 更新统计数据
        setStatisticsData({
          totalTime,
          accuracyRate,
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
      "%"
    );
    console.log("任务完成状态:", allTasksCompleted ? "已完成" : "进行中");
  }, [inventoryItems, isTaskCompleted, taskStartTime]);

  // 在组件中添加调试效果
  useEffect(() => {
    console.log("🔍 inventoryItems 已更新:", inventoryItems);
    console.log(
      "📊 有实际数量的项目:",
      inventoryItems.filter((item) => item.actualQuantity !== null).length
    );
  }, [inventoryItems]);

  useEffect(() => {
    console.log("📥 receivedCSVData 已更新:", receivedCSVData);
  }, [receivedCSVData]);

  // // 在组件挂载时连接 WebSocket
  // useEffect(() => {
  //   if (currentTaskNo) {
  //     console.log("连接 WebSocket");
  //     connectWebSocket();
  //   }

  //   // 清理函数：组件卸载时关闭 WebSocket
  //   return () => {
  //     if (webSocket) {
  //       webSocket.close();
  //     }
  //   };
  // }, [currentTaskNo]);

  // 添加一个手动重连按钮的函数
  const handleReconnectWebSocket = () => {
    if (webSocket) {
      webSocket.close();
    }
    connectWebSocket();
  };

  const handleDisconnectWebSocket = () => {
    if (webSocket) {
      setIsWebSocketConnected(false);
      webSocket.close();
    }
  };

  const handleRowClick = async (taskNo: string, binDesc: string) => {
  if (!isTaskStarted) {
    toast.info("请先启动盘点任务");
    return;
  }
  
  const rowIndex = inventoryItems.findIndex(
    (item) => item.taskNo === taskNo && item.binDesc === binDesc
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


    toast.success(
      `成功加载 ${taskNo} - ${binDesc} 的原始图片`
    );
  } catch (error) {
    console.error("加载图片失败:", error);
    setImageError(true);
    toast.error(`未找到 ${taskNo} - ${binDesc} 的图片文件`);
    setCurrentImage(null);
  } finally {
    setImageLoading(false);
  }
};

  useEffect(() => {
    return () => {
      if (currentImage) {
        URL.revokeObjectURL(currentImage);
      }
    };
  }, [currentImage]);

  const handleRowClickPost = async (
    taskNo: string,
    binDesc: string
  ) => {
    if (!isTaskStarted) {
      toast.info("请先启动盘点任务");

      return;
    }

    const rowIndex = inventoryItems.findIndex(
      (item) => item.taskNo === taskNo && item.binDesc === binDesc
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

      toast.success(
        `成功加载 ${taskNo} - ${binDesc} 的计算后图片`
      );
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

  // 获取计算后的图片 - 调用gateway接口获取main_rotated.jpg和depth_color.jpg
  const fetchCalculateImages = async (taskNo: string, binDesc: string) => {
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
      // 获取 main_rotated.jpg - 用于上半部分显示
      const mainRotatedResponse = await fetch(
        `${GATEWAY_URL}/api/inventory/image?taskNo=${encodeURIComponent(
          taskNo
        )}&binLocation=${encodeURIComponent(
          binDesc
        )}&cameraType=3d_camera&filename=main_rotated.jpg&source=capture_img`
      );

      if (mainRotatedResponse.ok) {
        const mainRotatedBlob = await mainRotatedResponse.blob();
        const mainRotatedUrl = URL.createObjectURL(mainRotatedBlob);
        setCurrentImage(mainRotatedUrl);
      } else {
        console.warn("获取 main_rotated.jpg 失败:", mainRotatedResponse.status);
      }

      // 获取 depth_color.jpg - 用于下半部分显示
      const depthColorResponse = await fetch(
        `${GATEWAY_URL}/api/inventory/image?taskNo=${encodeURIComponent(
          taskNo
        )}&binLocation=${encodeURIComponent(
          binDesc
        )}&cameraType=3d_camera&filename=depth_color.jpg&source=capture_img`
      );

      if (depthColorResponse.ok) {
        const depthColorBlob = await depthColorResponse.blob();
        const depthColorUrl = URL.createObjectURL(depthColorBlob);
        setPostImage(depthColorUrl);
        toast.success(
          `成功加载 ${taskNo} - ${binDesc} 的计算后图片`
        );
      } else {
        console.warn("获取 depth_color.jpg 失败:", depthColorResponse.status);
        toast.warning(
          `部分图片加载失败: ${taskNo} - ${binDesc}`
        );
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
    accuracyRate: 0,
    abnormalTasks: [] as any[],
  });

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
    interval: number = 1000
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

  const originalImages = [
    img1,
    img2,
    img3,
    img4,
    img5,
    img6,
    img7,
    img8,
    img9,
    img10,
    img11,
    img12,
    img13,
    img14,
    img15,
    img16,
    img17,
  ];

  const postprocessImages = [
    img1out,
    img2out,
    img3out,
    img4out,
    img5out,
    img6out,
    img7out,
    img8out,
    img9out,
    img10out,
    img11out,
    img12out,
    img13out,
    img14out,
    img15out,
    img16out,
    img17out,
  ];

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
            })
          );

          setInventoryItems(inventoryData);

          // 如果有通过state传递的数据，也进行合并
          if (location.state?.inventoryTasks) {
            console.log(
              "通过state传递的任务数据:",
              location.state.inventoryTasks
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
    rowIndex: number
  ) => {
    console.log(
      `手动抓图 - 任务号: ${taskNo}, 货位名称: ${locationName}, 行号: ${
        rowIndex + 1
      }`
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
    rowIndex: number
  ) => {
    console.log(
      `计算 - 任务号: ${taskNo}, 储位编号: ${binDesc}, 行号: ${rowIndex + 1}`
    );

    if (!isTaskStarted) {
      toast.error("请先启动盘点任务");
      return;
    }

    toast.info(`开始计算: 任务 ${taskNo} - 储位 ${binDesc}`);

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
            taskNo: taskNo,
            binLocation: binDesc,
            pile_id: 1, // 默认堆垛ID为1
            code_type: "ucc128", // 默认条码类型
          }),
        }
      );

      // 检查响应状态
      if (!response.ok) {
        // 尝试解析错误信息
        try {
          const errorData = await response.json();
          console.error("扫码+识别接口调用失败:", errorData);
          // 即使真实接口失败，也继续执行模拟逻辑
        } catch {
          console.error(`计算请求发送失败，状态码: ${response.status}`);
        }
      } else {
        // 接口调用成功，记录日志但不处理返回结果
        const result = await response.json();
        console.log("扫码+识别接口调用成功，结果:", result);
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

    // 调用gateway接口获取两个图片：main_rotated.jpg 和 depth_color.jpg
    await fetchCalculateImages(taskNo, String(binDesc));
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

      // 发送任务到网关
      const taskResponse = await fetch(
        `${GATEWAY_URL}/api/inventory/start-inventory`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            taskNo: currentTaskNo,
            binLocations: binLocations,
            tobaccoCode: tobaccoCode,
            rcsCode: rcsCode,
          }),
        }
      );

      // 检查响应状态
      if (!taskResponse.ok) {
        // 尝试解析错误信息
        try {
          const errorData = await taskResponse.json();
          throw new Error(
            errorData.message || errorData.detail || "任务启动失败"
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
          toast.success(`任务启动成功`);
        } else if (result.message === "任务已在执行中") {
          toast.success(`任务已在执行中`);
        }
      } else {
        // API 返回了业务逻辑错误
        toast.error(`任务启动失败: ${result.message || "未知错误"}`);
        throw new Error(result.message || "任务启动失败");
      }
    } catch (error) {
      console.error("任务启动失败:", error);
      toast.error(`任务启动失败`);
    } finally {
      setIsStartingTask(false);
    }
  };
  // // 启动盘点任务
  // const handleStartCountingTask = async () => {
  //   setIsStartingTask(true);
  //   try {
  //     const startTime = Date.now();
  //     setTaskStartTime(startTime);
  //     setCurrentExecutingTaskIndex(null);

  //     await new Promise((resolve) => setTimeout(resolve, 1000));

  //     // 模拟盘点过程
  //     for (let i = 0; i < inventoryItems.length; i++) {
  //       setCurrentExecutingTaskIndex(i);
  //       setCurrentImageIndex(i % originalImages.length);

  //       const delay = 2000 + Math.floor(Math.random() * 1000);
  //       await new Promise((resolve) => setTimeout(resolve, delay));

  //       // 模拟实际数量（90%概率与系统数量一致，10%概率有差异）
  //       const isAccurate = Math.random() < 0.9;
  //       let actualQuantity = inventoryItems[i].systemQuantity;

  //       if (!isAccurate) {
  //         // 模拟差异：在系统数量的80%-120%范围内随机
  //         const variation = 0.2;
  //         const minQuantity = Math.floor(
  //           inventoryItems[i].systemQuantity * (1 - variation)
  //         );
  //         const maxQuantity = Math.floor(
  //           inventoryItems[i].systemQuantity * (1 + variation)
  //         );
  //         actualQuantity =
  //           Math.floor(Math.random() * (maxQuantity - minQuantity + 1)) +
  //           minQuantity;

  //         // 记录异常任务
  //         setStatisticsData((prev) => ({
  //           ...prev,
  //           abnormalTasks: [
  //             ...prev.abnormalTasks,
  //             {
  //               taskNo: inventoryItems[i].taskNo,
  //               location: inventoryItems[i].locationName,
  //               expected: inventoryItems[i].systemQuantity,
  //               actual: actualQuantity,
  //             },
  //           ],
  //         }));

  //         toast.error(
  //           `任务 ${i + 1} 异常: 预期 ${
  //             inventoryItems[i].systemQuantity
  //           }，实际 ${actualQuantity}`
  //         );
  //       } else {
  //         toast.success(`任务 ${i + 1} 完成: 数量 ${actualQuantity}`);
  //       }

  //       // 更新实际数量
  //       setInventoryItems((prevItems) => {
  //         const newItems = [...prevItems];
  //         newItems[i] = {
  //           ...newItems[i],
  //           actualQuantity,
  //         };

  //         // 计算进度
  //         const completedCount = newItems.filter(
  //           (item) => item.actualQuantity !== null
  //         ).length;
  //         const newProgress = (completedCount / newItems.length) * 100;
  //         setProgress(Math.min(Math.round(newProgress), 100));

  //         return newItems;
  //       });
  //     }

  //     setCurrentExecutingTaskIndex(null);
  //     setIsTaskStarted(true);
  //     setIsTaskCompleted(true);

  //     // 计算统计信息
  //     const totalTime = Date.now() - startTime;
  //     const completedItems = inventoryItems.filter(
  //       (item) => item.actualQuantity !== null
  //     );
  //     const totalItems = completedItems.length;
  //     const accurateItems = totalItems - statisticsData.abnormalTasks.length;
  //     const accuracyRate =
  //       totalItems > 0 ? (accurateItems / totalItems) * 100 : 0;

  //     setStatisticsData((prev) => ({
  //       ...prev,
  //       totalTime,
  //       accuracyRate,
  //     }));

  //     toast.success("盘点任务完成！");
  //   } catch (error) {
  //     console.error("启动任务失败:", error);
  //     toast.error("启动任务失败");
  //   } finally {
  //     setIsStartingTask(false);
  //   }
  // };

  // 处理实际数量输入变化
  // 处理实际数量输入变化
  const handleActualQuantityChange = (id: string, value: string) => {
    const numericValue = value ? parseInt(value, 10) : null;

    // 检查是否已有接收的 CSV 数据
    const item = inventoryItems.find((item) => item.id === id);
    if (item) {
      const csvData = receivedCSVData.find(
        (data) =>
          data.taskNo === item.taskNo && data.binLocation === item.binCode
      );

      // 如果有接收的数据，提示用户
      if (csvData && csvData.number !== null) {
        const confirmed = window.confirm(
          `此库位已有自动识别的数量 ${csvData.number}，确定要手动修改为 ${numericValue} 吗？`
        );

        if (!confirmed) {
          return;
        }
      }
    }

    // 更新数量
    setInventoryItems((prevItems) =>
      prevItems.map((item) =>
        item.id === id ? { ...item, actualQuantity: numericValue } : item
      )
    );

    // 更新进度
    const completedCount = inventoryItems.filter(
      (item) => item.actualQuantity !== null
    ).length;
    const newProgress = (completedCount / inventoryItems.length) * 100;
    setProgress(Math.min(Math.round(newProgress), 100));
  };

  // 处理行点击事件
  // const handleRowClick = (index: number) => {
  //   if (!isTaskStarted) {
  //     toast.info("请先启动盘点任务");
  //     return;
  //   }
  //   setSelectedRowIndex(index);
  //   setCurrentExecutingTaskIndex(index);
  // };

  // 保存盘点结果
  const handleSaveInventory = () => {
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

    setTimeout(() => {
      setIsSaving(false);
      toast.success("盘点结果保存成功！");
    }, 1500);
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

  // 盘点结果统计
  const handleInventoryStatistics = () => {
    if (inventoryItems.length === 0) {
      toast.error("没有盘点数据可供统计");

      return;
    }

    const completedItems = inventoryItems.filter(
      (item) => item.actualQuantity !== null
    );

    const totalItems = completedItems.length;

    if (totalItems === 0) {
      toast.error("请先完成盘点任务");

      return;
    }

    // 计算异常任务

    const abnormalTasks = inventoryItems

      .filter(
        (item) =>
          item.actualQuantity !== null &&
          item.actualQuantity !== item.systemQuantity
      )

      .map((item) => ({
        taskNo: item.taskNo,

        location: item.locationName,

        expected: item.systemQuantity,

        actual: item.actualQuantity,
      }));

    const accurateItems = totalItems - abnormalTasks.length;

    const accuracyRate =
      totalItems > 0 ? (accurateItems / totalItems) * 100 : 0;

    // 计算总耗时 - 如果任务已完成，使用已记录的时间；否则计算到当前

    let totalTime = statisticsData.totalTime;

    if (!isTaskCompleted && taskStartTime) {
      totalTime = Date.now() - taskStartTime;
    }

    setStatisticsData({
      totalTime,

      accuracyRate,

      abnormalTasks,
    });

    setIsStatisticsModalOpen(true);
  };
  // 处理返回
  const handleBack = () => {
    navigate("/inventory/start");
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
                          <th className="px-8 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            序号
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            任务编号
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
                            库存数量（件）
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            实际数量（件）
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            差异
                          </th>

                          {/* <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            手动抓图
                          </th>*/}
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            计算
                          </th>
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

                          // 检查是否有接收到的 CSV 数据
                          const csvData = receivedCSVData.find(
                            (data) =>
                              data.taskNo === item.taskNo &&
                              data.binLocation === item.binCode
                          );

                          // 确定要显示的品规名称
                          const displayProductName =
                            csvData?.text && csvData.text.trim() !== ""
                              ? csvData.text
                              : item.productName;

                          return (
                            <tr
                              key={item.id}
                              className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                                isSelected
                                  ? "bg-blue-50 border-l-4 border-blue-500"
                                  : ""
                              }`}
                              // onClick={() =>
                              //   handleRowClick(
                              //     item.taskNo,
                              //     String(item.binDesc),
                              //   )
                              // }
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
                                {displayProductName ||
                                  item.productName ||
                                  "未知品规"}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {item.locationName}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {actualQuantity !== null ? (
                                  <div className="flex items-center">
                                    <span className="text-green-600 font-medium">
                                      {displayProductName || "已识别"}
                                    </span>
                                    <i className="fa-solid fa-check-circle ml-2 text-green-500"></i>
                                  </div>
                                ) : (
                                  <span className="text-gray-400">待识别</span>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {systemQuantity !== null ? systemQuantity : 0}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                {actualQuantity !== null ? (
                                  <div className="flex items-center">
                                    <span className="text-green-600 font-medium">
                                      {actualQuantity}
                                    </span>
                                    <i className="fa-solid fa-check-circle ml-2 text-green-500"></i>
                                  </div>
                                ) : (
                                  <span className="text-gray-400">待计算</span>
                                )}
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
                                    待计算
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation(); // 阻止事件冒泡，避免触发行点击事件

                                    handleCalculate(
                                      item.taskNo,
                                      String(item.binDesc),
                                      index
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
                {/* 上半部分 - 原始图片 */}

                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
  {isCapture ? (
    <>
      {imageLoading ? (
        // 加载状态
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
        </div>
      ) : currentImage ? (
        // 成功加载图片
        <>

                        <img
                          src={String(currentImage)}
                          alt={``}
                          className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700"
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
            <span>原始图像</span>
          </div>
        </>
      ) : (
        // 无图片状态
        <div className="flex flex-col items-center justify-center h-full text-center p-4">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
            <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
          </div>
          <p className="text-gray-500 text-sm">点击任务行加载图片</p>
        </div>
      )}
    </>
  ) : (
    // 未连接状态
    <div className="flex flex-col items-center justify-center h-full text-center p-4">
      <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
        <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
      </div>
      <p className="text-gray-500 text-sm">画面1未连接</p>
    </div>
  )}
</div>
                </div>

                {/* 下半部分 - 处理后的图片 */}
                <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
                  <div className="relative w-full h-full max-w-md mx-auto">
                    {isCalculate ? (
                      <>
                        <img
                          src={String(postImage)}
                          alt={``}
                          className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700"
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
                          <span>计算后图像</span>
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                          <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                        </div>
                        <p className="text-gray-500 text-sm">画面2未连接</p>
                      </div>
                    )}
                  </div>
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
