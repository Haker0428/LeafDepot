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
import { logger } from "../utils/logger";
import PhotoGallery from "../components/InventoryProgress/PhotoGallery";
import StatisticsModal from "../components/InventoryProgress/StatisticsModal";

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
const formatTime = (milliseconds: number) => {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds}秒`;
};

export default function InventoryProgress() {
  const { authToken, userName, userLevel } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingAndCreating, setIsSavingAndCreating] = useState(false);
  const [isStartingTask, setIsStartingTask] = useState(false);
  const [currentTaskNo, setCurrentTaskNo] = useState<string | null>(null);
  const [currentTaskManifest, setCurrentTaskManifest] =
    useState<TaskManifest | null>(null);


  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [isTaskStarted, setIsTaskStarted] = useState(false);
  const [isTaskCompleted, setIsTaskCompleted] = useState(false);
  const [taskStartTime, setTaskStartTime] = useState<number | null>(null);
  // useRef 保证闭包中始终能读到最新值（不受 async await + setInterval 闭包陷阱影响）
  const taskStartTimeRef = useRef<number | null>(null);
  const [imageLoading, setImageLoading] = useState(true);
  const [imageError, setImageError] = useState(false);
  const [isStatisticsModalOpen, setIsStatisticsModalOpen] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  // pendingSaveAction: 点击"保存并进行下次盘点"时传入的保存回调，弹窗确认后才执行
  const [pendingSaveAction, setPendingSaveAction] = useState<(() => void) | null>(null);
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

  // 盘点冲突弹窗状态（有其他任务正在运行）
  const [conflictModal, setConflictModal] = useState<{
    open: boolean;
    runningTaskNo: string;
    operatorName: string;
    operatorId: string;
    startTime: string;
    onWait: () => void;
    onTerminate: () => void;
  }>({
    open: false,
    runningTaskNo: "",
    operatorName: "",
    operatorId: "",
    startTime: "",
    onWait: () => {},
    onTerminate: () => {},
  });

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

  // 组件挂载时清空旧任务完成通知，防止收到上一个任务的延迟完成弹窗
  useEffect(() => {
    window.dispatchEvent(new Event("clear-task-notify"));
  }, []);


  // 在组件中添加 WebSocket 连接函数
  // const connectWebSocket = () => {
  // if (!currentTaskNo) {
  // toast.error("没有当前任务，无法连接 WebSocket");
  // return;
  // }

  // // 构建 WebSocket URL，根据你的网关地址调整
  // const wsUrl = `ws://localhost:8000/ws/inventory/${currentTaskNo}`;
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


  useEffect(() => {
    const completedCount = inventoryItems.filter(
      (item) => item.actualQuantity !== null,
    ).length;
    const newProgress = (completedCount / inventoryItems.length) * 100;
    setProgress(Math.min(Math.round(newProgress), 100));

    // 检查是否所有任务都已完成
    const allTasksCompleted = completedCount === inventoryItems.length;

    // 检查是否所有任务都已完成（排除空列表的误判）
    if (inventoryItems.length > 0 && allTasksCompleted) {
      setIsTaskCompleted(true);
      logger.info("[INVENTORY] 所有库位盘点完成", { taskNo: currentTaskNo, totalItems: inventoryItems.length }, "inventory");
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
    } else if (inventoryItems.length > 0) {
      // 有任务但未全部完成，重置为进行中
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
  }, [inventoryItems, taskStartTime]);

  // 在组件中添加调试效果
  useEffect(() => {
    console.log("🔍 inventoryItems 已更新:", inventoryItems);
    console.log(
      "📊 有实际数量的项目:",
      inventoryItems.filter((item) => item.actualQuantity !== null).length,
    );
  }, [inventoryItems]);

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
        const topUrl = group.top ? buildImageUrl(group.top) : "";
        const bottomUrl = group.bottom ? buildImageUrl(group.bottom) : "";

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

  const handleRowClick = (item: InventoryItem, index: number) => {
    setSelectedRowIndex(index);
    loadPhotoGroups(item.taskNo, item.binDesc || "", {
      photo3dPath: item.photo3dPath,
      photoDepthPath: item.photoDepthPath,
      photoScan1Path: item.photoScan1Path,
      photoScan2Path: item.photoScan2Path,
    });
  };

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


  // 辅助函数：构建图片URL（参考History.tsx的逻辑）
  const buildImageUrl = (photoPath: string) => {
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
      const isResumeMode = location.state?.resumeMode;

      // 继续盘点模式：从后端加载任务状态，同时从 localStorage 恢复清单数据
      if (isResumeMode) {
        const resumeTaskNo = location.state.taskNo;
        if (resumeTaskNo) {
          setCurrentTaskNo(resumeTaskNo);
          localStorage.setItem("currentTaskNo", resumeTaskNo);
          toast.info(`正在加载任务 ${resumeTaskNo} 的进度...`);
        }
        // 优先从 localStorage 恢复清单数据
        try {
          const manifestData = localStorage.getItem("currentTaskManifest");
          if (manifestData) {
            const manifest: any = JSON.parse(manifestData);
            setCurrentTaskManifest(manifest);
            const inventoryData: InventoryItem[] = manifest.tasks.map(
              (task: any, index: number) => ({
                id: `${task.taskID}_${task.binCode}_${index}`,
                productName: task.tobaccoName,
                specification: task.binDesc,
                systemQuantity: task.tobaccoQty,
                actualQuantity: null,
                unit: "件",
                locationId: task.binCode,
                locationName: task.binDesc,
                taskNo: task.taskID,
                startTime: Date.now(),
                whCode: task.whCode,
                areaCode: task.areaCode,
                areaName: task.areaName,
                binCode: task.binCode,
                binDesc: task.binDesc,
                binStatus: task.binStatus,
                tobaccoCode: task.tobaccoCode,
                rcsCode: task.rcsCode,
                photo3dPath: "",
                photoDepthPath: "",
                photoScan1Path: "",
                photoScan2Path: "",
              }),
            );
            setInventoryItems(inventoryData);
            setCalibrationRecords({});
            toast.success(`已加载任务清单，包含 ${manifest.tasks.length} 个储位`);
            return;
          }
        } catch {
          // localStorage 读取失败，继续尝试从后端获取
        }

        // localStorage 无 manifest，从后端 progress 接口获取（WebSocket 弹窗跳转场景）
        fetch(`${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(resumeTaskNo || "")}`)
          .then(res => res.json())
          .then(data => {
            const items: any[] = data.data?.inventoryItems || [];
            if (items.length === 0) return;
            const manifest: any = {
              taskNo: resumeTaskNo || "",
              stats: {
                totalBins: items.length,
                totalQuantity: 0,
                uniqueItems: 0,
                uniqueLocations: 0,
              },
              tasks: items,
            };
            setCurrentTaskManifest(manifest);
            localStorage.setItem("currentTaskManifest", JSON.stringify(manifest));
            const inventoryData: InventoryItem[] = items.map((task: any, index: number) => ({
              id: `${task.taskID || task.binCode}_${task.binCode}_${index}`,
              productName: task.tobaccoName,
              specification: task.binDesc,
              systemQuantity: task.tobaccoQty,
              actualQuantity: null,
              unit: "件",
              locationId: task.binCode,
              locationName: task.binDesc,
              taskNo: task.taskID || "",
              startTime: Date.now(),
              whCode: task.whCode,
              areaCode: task.areaCode,
              areaName: task.areaName,
              binCode: task.binCode,
              binDesc: task.binDesc,
              binStatus: task.binStatus,
              tobaccoCode: task.tobaccoCode,
              rcsCode: task.rcsCode,
              photo3dPath: "",
              photoDepthPath: "",
              photoScan1Path: "",
              photoScan2Path: "",
            }));
            setInventoryItems(inventoryData);
            setCalibrationRecords({});
            toast.success(`已从服务端加载任务清单，包含 ${items.length} 个储位`);
          })
          .catch((err) => {
            logger.error("[API] 加载任务清单失败", { error: String(err), taskNo: resumeTaskNo }, "api");
            toast.error("加载任务清单失败");
          });
        return;
      }

      // 正常模式：从本地存储加载任务清单
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

  // 页面加载时检测任务状态：取消/中断则提示；resume 模式则立即加载结果或启动轮询
  useEffect(() => {
    const checkTaskStatus = async () => {
      if (!currentTaskNo) return;
      try {
        const res = await fetch(
          `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(currentTaskNo)}`
        );
        if (!res.ok) {
          // resume 模式下任务不在内存中（如服务端重启），清除弹窗状态并提示
          if (location.state?.resumeMode) {
            window.dispatchEvent(new Event("clear-task-notify"));
            toast.error("任务已不存在于服务器内存中，请从历史记录页面查看");
          }
          return;
        }
        const data = await res.json();
        const status = data.data?.status;

        // resume 模式：立即加载已完成的结果或启动轮询
        if (location.state?.resumeMode) {
          // 从服务端恢复任务开始时间（用于计算耗时）
          const startTimeStr = data.data?.start_time;
          if (startTimeStr) {
            const t = new Date(startTimeStr).getTime();
            setTaskStartTime(t);
            taskStartTimeRef.current = t;
          }

          if (status === "completed" || status === "partial") {
            // 已完成，直接加载结果
            const resultsRes = await fetch(
              `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(currentTaskNo)}`
            );
            const resultsData = await resultsRes.json();
            const inventoryResults = resultsData.data?.inventoryResults || [];
            const newItems = inventoryItems.map((item) => {
              const ir = inventoryResults.find((r: any) => r.binLocation === item.locationName);
              if (!ir) return item;
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
            setIsTaskStarted(true);  // 标记为已启动，防止出现"下发"按钮和阻止编辑
            setProgress(100);
            toast.success("任务已完成，已加载盘点结果");
          } else if (status === "running") {
            // 进行中，设置已启动状态并启动轮询
            setIsTaskStarted(true);
            setIsStartingTask(false);
          }
          return;
        }

        if (status === "cancelled" || status === "interrupted") {
          localStorage.removeItem("currentTaskManifest");
          localStorage.removeItem("currentTaskNo");
          toast.warning("上一个任务已被中断，请重新下发");
          setCurrentTaskManifest(null);
        }

        if (status === "failed") {
          // resume 模式下检测到任务失败，弹出错误弹窗
          const errorMsg = data.data?.message || "盘点任务失败";
          const errorType: "rcs" | "camera" | "other" =
            (data.data?.error_type as "rcs" | "camera" | "other") || "other";
          localStorage.removeItem("currentTaskManifest");
          localStorage.removeItem("currentTaskNo");
          window.dispatchEvent(new Event("clear-task-notify"));
          window.dispatchEvent(new Event("resume-polling"));
          setTaskErrorModal({
            open: true,
            errorType,
            message: errorMsg,
            onOk: () => {
              setTaskErrorModal((prev) => ({ ...prev, open: false }));
              navigate("/inventory/start");
            },
          });
          setIsStartingTask(false);
          setCurrentTaskManifest(null);
        }
      } catch {}
    };
    checkTaskStatus();
  }, [currentTaskNo]);

  // resume 模式：启动轮询，实时更新进度和结果
  useEffect(() => {
    if (!currentTaskNo || !location.state?.resumeMode) return;
    if (location.state?.taskStatus === "completed" || location.state?.taskStatus === "partial") return; // 已在 checkTaskStatus 中处理

    const pollIntervalId = setInterval(async () => {
      try {
        const progressResponse = await fetch(
          `${GATEWAY_URL}/api/inventory/progress?taskNo=${encodeURIComponent(currentTaskNo)}`
        );
        if (!progressResponse.ok) return;
        const progressResult = await progressResponse.json();
        if (progressResult.code !== 200) return;

        const taskStatus = progressResult.data?.status;
        const currentStep = progressResult.data?.current_step || 0;
        const totalSteps = progressResult.data?.total_steps || inventoryItems.length || 1;
        setProgress(Math.round((currentStep / totalSteps) * 100));

        if (taskStatus === "completed" || taskStatus === "partial") {
          clearInterval(pollIntervalId);
          const resultsResponse = await fetch(
            `${GATEWAY_URL}/api/inventory/results?taskNo=${encodeURIComponent(currentTaskNo)}`
          );
          const resultsData = await resultsResponse.json();
          const inventoryResults = resultsData.data?.inventoryResults || [];
          const newItems = inventoryItems.map((item) => {
            const ir = inventoryResults.find((r: any) => r.binLocation === item.locationName);
            if (!ir) return item;
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
          setIsTaskStarted(true);
          setProgress(100);
          toast.success("任务已完成，已加载盘点结果");
        }
      } catch {}
    }, 3000);

    return () => clearInterval(pollIntervalId);
  }, [currentTaskNo]);

  // 组件卸载时通知 App 恢复轮询（用户离开进度页时）
  useEffect(() => {
    return () => {
      window.dispatchEvent(new Event("resume-polling"));
    };
  }, []);

  // 监听 WebSocket task_failed 事件：任务下发/执行失败时弹出错误弹窗
  // （用户可能在提交后切换到其他页面，此时轮询未启动，需要靠 WebSocket 事件触发弹窗）
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent).detail;
      if (msg.event !== "task_failed") return;
      // 只处理当前任务的失败
      if (!currentTaskNo || msg.taskNo !== currentTaskNo) return;
      const errorMsg = msg.data?.message || "盘点任务下发失败";
      const errorType: "rcs" | "camera" | "other" =
        (msg.data?.error_type as "rcs" | "camera" | "other") || "other";
      localStorage.removeItem("currentTaskManifest");
      localStorage.removeItem("currentTaskNo");
      window.dispatchEvent(new Event("clear-task-notify"));
      window.dispatchEvent(new Event("resume-polling"));
      setTaskErrorModal({
        open: true,
        errorType,
        message: errorMsg,
        onOk: () => {
          setTaskErrorModal((prev) => ({ ...prev, open: false }));
        },
      });
      setIsStartingTask(false);
    };
    window.addEventListener("remote-task-event", handler as EventListener);
    return () => window.removeEventListener("remote-task-event", handler as EventListener);
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

  // 计算功能 - 调用扫码+识别接口 + 保留模拟API调用
  // 启动盘点任务 - 与内部网关程序交互
  const handleStartCountingTask = async () => {
    const now = Date.now();
    setTaskStartTime(now);
    taskStartTimeRef.current = now;
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

          // 409 Conflict：有其他任务正在运行，弹出冲突弹窗
          if (taskResponse.status === 409) {
            setIsStartingTask(false);
            const runningInfo = errorData.data || {};
            setConflictModal({
              open: true,
              runningTaskNo: runningInfo.runningTaskNo || "",
              operatorName: runningInfo.operatorName || "未知",
              operatorId: runningInfo.operatorId || "",
              startTime: runningInfo.startTime || "",
              onWait: () => {
                setConflictModal((prev) => ({ ...prev, open: false }));
                // 切换到监控模式，跟随当前任务
                toast.info(`跟随任务 ${runningInfo.runningTaskNo}，实时监控中...`);
                setCurrentTaskNo(runningInfo.runningTaskNo);
                setIsStartingTask(false);
              },
              onTerminate: async () => {
                // 调用取消接口
                try {
                  await fetch(
                    `${GATEWAY_URL}/api/inventory/cancel-inventory?taskNo=${encodeURIComponent(runningInfo.runningTaskNo)}`,
                    { method: "POST" },
                  );
                  toast.success("已发送终止指令，任务结束后可重新下发");
                } catch {
                  toast.error("终止指令发送失败");
                }
                setConflictModal((prev) => ({ ...prev, open: false }));
                setIsStartingTask(false);
              },
            });
            return;
          }

          throw new Error(
            errorData.message || errorData.detail || "任务启动失败",
          );
        } catch (err) {
          // 已经是 Conflict 弹窗则不再抛出
          if (taskResponse.status === 409) return;
          throw err;
        }
      }

      // 解析成功的 JSON 响应
      const result = await taskResponse.json();

      // 根据你的 API 设计，result 可能包含以下结构
      // 示例1: { "code": 200, "message": "成功", "data": {...} }
      // 示例2: { "status": "success", "data": {...} }

      if (result.code === 200) {
        if (result.message === "盘点任务已启动") {
          // 任务号可能由网关自动生成，同步到状态和本地存储
          const returnedTaskNo = result.data?.taskNo;
          if (returnedTaskNo && returnedTaskNo !== currentTaskNo) {
            setCurrentTaskNo(returnedTaskNo);
            localStorage.setItem("currentTaskNo", returnedTaskNo);
          }
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
                  showStatisticsModal(newItems, taskStartTimeRef.current ? Date.now() - taskStartTimeRef.current : undefined);
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
                const errorMsg = progressResult.data?.message || "盘点任务下发失败";
                const errorType: "rcs" | "camera" | "other" =
                  (progressResult.data?.error_type as "rcs" | "camera" | "other") || "other";
                // 清理任务状态，允许重新下发
                localStorage.removeItem("currentTaskManifest");
                localStorage.removeItem("currentTaskNo");
                window.dispatchEvent(new Event("clear-task-notify"));
                window.dispatchEvent(new Event("resume-polling"));
                // 显示错误弹窗，点击确定后留在当前页面
                setTaskErrorModal({
                  open: true,
                  errorType,
                  message: errorMsg,
                  onOk: () => {
                    setTaskErrorModal((prev) => ({ ...prev, open: false }));
                  },
                });
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
                logger.info("[INVENTORY] 轮询检测到任务完成", { taskNo: currentTaskNo }, "inventory");
                setIsTaskCompleted(true);
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
                } else {
                  showStatisticsModal(newItems);
                }
                setProgress(100);
                return;
              }

              // 任务失败
              if (taskStatus === "failed") {
                clearInterval(pollIntervalId);
                const errorMsg2 = progressResult.data?.message || "盘点任务失败";
                const errorType2 = (progressResult.data?.error_type as "rcs" | "camera" | "other") || "other";
                localStorage.removeItem("currentTaskManifest");
                localStorage.removeItem("currentTaskNo");
                window.dispatchEvent(new Event("clear-task-notify"));
                window.dispatchEvent(new Event("resume-polling"));
                setTaskErrorModal({
                  open: true,
                  errorType: errorType2,
                  message: errorMsg2,
                  onOk: () => {
                    setTaskErrorModal((prev) => ({ ...prev, open: false }));
                  },
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

  // await new Promise((resolve) => setTimeout(resolve, 1000));

  // // 模拟盘点过程
  // for (let i = 0; i < inventoryItems.length; i++) {
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
        // 保存成功后立即清除弹窗状态，防止 30 秒轮询再次弹出
        window.dispatchEvent(new Event("clear-task-notify"));

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
      // 保存成功后立即清除弹窗状态
      window.dispatchEvent(new Event("clear-task-notify"));

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
          showStatisticsModal(newItems, taskStartTimeRef.current ? Date.now() - taskStartTimeRef.current : undefined);
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

  // 核心统计函数，直接接收 totalTimeMs，避免闭包捕获旧 state
  const showStatisticsModal = (items: InventoryItem[], totalTimeMs?: number) => {
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
    const totalTime = totalTimeMs ?? 0;

    setStatisticsData({ totalTime, diffRate, abnormalTasks });
    setPendingSaveAction(null);
    setIsStatisticsModalOpen(true);
  };

  // 带确认回调的统计（用于"保存并进行下次盘点"场景）
  const openStatisticsWithConfirm = (onConfirm: () => void) => {
    const ms = taskStartTime ? Date.now() - taskStartTime : undefined;
    showStatisticsModal(inventoryItems, ms);
    setPendingSaveAction(() => onConfirm);
  };
  // 处理返回
  const handleBack = () => {
    navigate("/inventory/start");
  };

  // 取消任务
  const handleCancelTask = async () => {
    if (isCancelling) return;
    setIsCancelling(true);
    try {
      const res = await fetch(
        `${GATEWAY_URL}/api/inventory/cancel-inventory?taskNo=${encodeURIComponent(currentTaskNo || "")}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.code === 200) {
        localStorage.removeItem("currentTaskManifest");
        localStorage.removeItem("currentTaskNo");
        window.dispatchEvent(new Event("clear-task-notify"));
        window.dispatchEvent(new Event("resume-polling"));
        logger.info("[INVENTORY] 取消盘点任务", { taskNo: currentTaskNo }, "inventory");
        toast.success("任务已取消");
        navigate("/inventory/start");
      }
    } catch (err) {
      toast.error("取消任务失败");
    } finally {
      setIsCancelling(false);
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

            {/* 取消任务按钮（有任务时一直显示） */}
            {currentTaskManifest && (
              <button
                onClick={handleCancelTask}
                disabled={isCancelling}
                className={`px-4 py-2 rounded-lg transition-all flex items-center ${
                  isCancelling
                    ? "bg-gray-400 text-gray-200 cursor-not-allowed"
                    : "bg-red-600 hover:bg-red-700 text-white"
                }`}
              >
                {isCancelling ? (
                  <>
                    <i className="fa-solid fa-spinner fa-spin mr-2"></i>正在取消...
                  </>
                ) : (
                  <>
                    <i className="fa-solid fa-stop mr-2"></i>取消任务
                  </>
                )}
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
                              onClick={() => handleRowClick(item, index)}
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

          <PhotoGallery
            photoGroups={photoGroups}
            currentGroupIndex={currentGroupIndex}
            setCurrentGroupIndex={setCurrentGroupIndex}
            imageLoading={imageLoading}
            imageError={imageError}
            handleImageLoad={handleImageLoad}
            handleImageError={handleImageError}
            setLightboxImage={setLightboxImage}
          />
        </div>
      </main>

      {isStatisticsModalOpen && (
        <StatisticsModal
          statisticsData={statisticsData}
          inventoryItemsLength={inventoryItems.length}
          setIsStatisticsModalOpen={setIsStatisticsModalOpen}
          pendingSaveAction={pendingSaveAction}
          setPendingSaveAction={setPendingSaveAction}
          formatTime={formatTime}
        />
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
        title="⚠️ 有其他盘点任务正在进行"
        open={conflictModal.open}
        onCancel={() => conflictModal.onWait()}
        footer={[
          <button
            key="wait"
            onClick={conflictModal.onWait}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            等待当前任务完成
          </button>,
          <button
            key="terminate"
            onClick={conflictModal.onTerminate}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            终止当前任务
          </button>,
        ]}
        width={520}
      >
        <div className="py-2">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-3">
            <p className="text-amber-800 font-medium">
              有其他盘点任务正在进行中，无法同时下发新任务。
            </p>
          </div>
          <div className="space-y-2 text-sm text-gray-700">
            <div className="flex gap-2">
              <span className="text-gray-500 w-20 flex-shrink-0">任务号：</span>
              <span className="font-mono font-medium">{conflictModal.runningTaskNo || "—"}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-500 w-20 flex-shrink-0">操作人：</span>
              <span>{conflictModal.operatorName || "未知"}{conflictModal.operatorId ? `（${conflictModal.operatorId}）` : ""}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-500 w-20 flex-shrink-0">开始时间：</span>
              <span>{conflictModal.startTime ? new Date(conflictModal.startTime).toLocaleString("zh-CN") : "—"}</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-200 text-xs text-gray-500">
            <p>
              选择「<strong>等待当前任务完成</strong>」将切换到该任务的监控视图；<br />
              选择「<strong>终止当前任务</strong>」将强制结束该任务，终止后请等待数秒再重新下发。
            </p>
          </div>
        </div>
      </Modal>

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
        onCancel={() => setTaskErrorModal((prev) => ({ ...prev, open: false }))}
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
