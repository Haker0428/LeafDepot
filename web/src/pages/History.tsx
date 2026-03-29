import { useState, useEffect, useRef } from "react";
import { useAuth } from "../contexts/authContext";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "../config/ip_address";
import * as XLSX from "xlsx";
import { useNavigate } from "react-router-dom";
import { addOperationLog } from "../lib/operationLog";

// 历史任务类型定义
interface HistoryTask {
  taskId: string;
  taskDate: Date;
  fileName: string;
  isExpired: boolean;
  createdAt?: string;
}

// 盘点详情类型定义
interface InventoryDetail {
  序号: number;
  品规名称: string;
  储位名称: string;
  实际品规: string;
  库存数量: number;
  实际数量: number;
  差异: string;
  照片1路径: string;
  照片2路径: string;
  照片3路径: string;
  照片4路径: string;
}

export default function History() {
  const { userLevel, userName, authToken, logout } = useAuth();
  const [tasks, setTasks] = useState<HistoryTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<HistoryTask | null>(null);
  const [taskDetails, setTaskDetails] = useState<InventoryDetail[]>([]);
  const [selectedPosition, setSelectedPosition] = useState<string>("");
  const [currentImages, setCurrentImages] = useState<string[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // 新增状态：清理历史数据
  const [showCleanupDialog, setShowCleanupDialog] = useState(false);
  const [showPermissionDialog, setShowPermissionDialog] = useState(false); // 权限不足提示弹窗
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]); // 选中的任务ID列表
  const [cleanupMode, setCleanupMode] = useState<"selected" | "beforeSelected">(
    "selected",
  ); // 清理模式

  // 处理返回按钮点击
  const handleBack = () => {
    navigate("/dashboard");
  };

  // 切换任务选中状态
  const toggleTaskSelection = (taskId: string) => {
    setSelectedTaskIds((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId],
    );
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedTaskIds.length === tasks.length) {
      setSelectedTaskIds([]);
    } else {
      setSelectedTaskIds(tasks.map((task) => task.taskId));
    }
  };

  // 点击清理历史按钮
  const handleCleanupClick = () => {
    if (userLevel !== "admin") {
      setShowPermissionDialog(true);
      return;
    }
    setShowCleanupDialog(true);
  };

  useEffect(() => {
    console.log("History - Current authentication state:", {
      userLevel,
      userName,
      authToken: authToken ? authToken.substring(0, 10) + "..." : "null",
    });
  }, [userLevel, userName, authToken]);

  // 从任务ID解析日期
  const parseTaskDate = (taskId: string): Date | null => {
    try {
      // 去除前面的英文字母
      const numberPart = taskId.replace(/^[A-Za-z]+/, "");

      // 提取日期部分（假设日期是连续的8位数字）
      const dateMatch = numberPart.match(/(\d{8})/);

      if (dateMatch && dateMatch[1]) {
        const dateStr = dateMatch[1];
        const year = parseInt(dateStr.substring(0, 4));
        const month = parseInt(dateStr.substring(4, 6)) - 1; // 月份从0开始
        const day = parseInt(dateStr.substring(6, 8));

        return new Date(year, month, day);
      }

      return null;
    } catch (error) {
      console.error("解析任务日期失败:", error);
      return null;
    }
  };

  // 检查任务是否过期（超过6个月）
  const isTaskExpired = (taskDate: Date): boolean => {
    const now = new Date();
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(now.getMonth() - 6);

    return taskDate < sixMonthsAgo;
  };

  // 1. 修改 loadHistoryTasks 函数：
  const loadHistoryTasks = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${GATEWAY_URL}/api/history/tasks`);
      const result = await response.json();

      if (result.code === 200) {
        // 过滤掉过期任务和隐藏文件（以.开头的文件）
        const validTasks = result.data.tasks
          .filter(
            (task: any) => !task.isExpired && !task.fileName.startsWith("."),
          )
          .map((task: any) => ({
            taskId: task.taskId,
            taskDate: task.taskDate
              ? new Date(task.taskDate)
              : parseTaskDate(task.taskId) || new Date(),
            fileName: task.fileName,
            isExpired: task.isExpired,
            createdAt:
              task.createdAt || task.taskDate || new Date().toISOString(),
          }));

        console.log("加载的历史任务:", validTasks);
        setTasks(validTasks);

        // 默认选中第一个任务
        if (validTasks.length > 0) {
          setSelectedTask(validTasks[0]);
          await loadTaskDetails(validTasks[0]);
        }
      } else {
        toast.error("加载历史任务失败: " + result.message);
      }
    } catch (error) {
      toast.error("加载历史任务失败");
      console.error("加载历史任务失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 2. 修改 loadTaskDetails 函数：
  const loadTaskDetails = async (task: HistoryTask) => {
    try {
      const response = await fetch(
        `${GATEWAY_URL}/api/history/task/${task.taskId}`,
      );
      const result = await response.json();

      if (result.code === 200) {
        const details: InventoryDetail[] = result.data.details.map(
          (item: any) => ({
            序号: item.序号,
            品规名称: item.品规名称,
            储位名称: item.储位名称,
            实际品规: item.实际品规,
            库存数量: item.库存数量,
            实际数量: item.实际数量,
            差异: item.差异,
            照片1路径: item.照片1路径,
            照片2路径: item.照片2路径,
            照片3路径: item.照片3路径,
            照片4路径: item.照片4路径,
          }),
        );

        setTaskDetails(details);

        // 默认选中第一个储位
        if (details.length > 0) {
          setSelectedPosition(details[0].储位名称);
          // 传入当前任务的taskId
          updateImagesForPosition(task.taskId, details[0]);
        }
      } else {
        toast.error(`加载任务 ${task.taskId} 详情失败: ${result.message}`);
      }
    } catch (error) {
      toast.error(`加载任务 ${task.taskId} 详情失败`);
      console.error("加载任务详情失败:", error);
    }
  };

  // 3. 修改 updateImagesForPosition 函数中的图片路径构建：
  const updateImagesForPosition = async (
    taskId: string,
    detail: InventoryDetail,
  ) => {
    // 从detail中获取照片路径数组
    const photoPaths = [
      detail.照片1路径,
      detail.照片2路径,
      detail.照片3路径,
      detail.照片4路径,
    ];

    // 构建图片URL数组
    const images = photoPaths.map((photoPath) => {
      // 默认值
      if (!photoPath || photoPath.trim() === "") {
        return "";
      }

      try {
        // 解析照片路径，格式如：/3D_CAMERA/MAIN.JPEG
        // 去除开头的斜杠并分割路径
        const normalizedPath = photoPath.startsWith("/")
          ? photoPath.substring(1)
          : photoPath;

        const parts = normalizedPath.split("/");

        // 确保路径至少有两部分
        if (parts.length < 2) {
          console.warn(`无效的照片路径格式: ${photoPath}`);
          return "";
        }

        // cameraType是第一部分，转为小写（例如：3D_CAMERA -> 3d_camera）
        const cameraType = parts[0].toLowerCase();

        // filename是第二部分，去除文件扩展名（例如：MAIN.JPEG -> MAIN）
        const fullFilename = parts[1];
        const filename = fullFilename.split(".")[0]; // 移除扩展名

        // 构建URL - 使用传入的taskId
        return `${GATEWAY_URL}/api/history/image?taskNo=${taskId}&binLocation=${detail.储位名称}&cameraType=${cameraType}&filename=${filename}`;
      } catch (error) {
        console.error(`解析照片路径失败: ${photoPath}`, error);
        return "";
      }
    });

    // 过滤掉空URL
    const validImages = images.filter((img) => img !== "");
    console.log("生成的图片URLs:", validImages); // 添加调试日志

    // 设置加载状态
    setImagesLoading(true);
    setImagesLoaded(false);

    // 设置图片URL
    setCurrentImages(validImages);

    // 预加载所有图片
    if (validImages.length > 0) {
      try {
        await Promise.all(
          validImages.map((url) => {
            return new Promise<void>((resolve, reject) => {
              const img = new Image();
              img.onload = () => {
                console.log(`图片加载成功: ${url}`);
                resolve();
              };
              img.onerror = () => {
                console.error(`图片加载失败: ${url}`);
                // 即使加载失败，也继续
                resolve();
              };
              img.src = url;
            });
          }),
        );
        setImagesLoaded(true);
      } catch (error) {
        console.error("预加载图片失败:", error);
      } finally {
        setImagesLoading(false);
      }
    } else {
      setImagesLoading(false);
      setImagesLoaded(true);
    }
  };

  // 处理选择任务
  const handleSelectTask = async (task: HistoryTask) => {
    setSelectedTask(task);
    await loadTaskDetails(task);
  };

  // 处理选择储位
  const handleSelectPosition = (position: string) => {
    setSelectedPosition(position);
    const detail = taskDetails.find((d) => d.储位名称 === position);
    if (detail && selectedTask) {
      // 传入当前任务的taskId
      updateImagesForPosition(selectedTask.taskId, detail);
    }
  };

  // 处理文件上传（模拟读取本地文件）
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const reader = new FileReader();
      reader.onload = (e) => {
        const data = e.target?.result;
        if (data) {
          const workbook = XLSX.read(data, { type: "binary" });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const jsonData = XLSX.utils.sheet_to_json(firstSheet);

          console.log("解析的Excel数据:", jsonData);
          toast.success(`成功解析文件: ${file.name}`);

          // 这里可以根据需要处理解析后的数据
        }
      };
      reader.readAsBinaryString(file);
    } catch (error) {
      toast.error("解析Excel文件失败");
      console.error("解析Excel失败:", error);
    }
  };

  // 格式化日期显示
  const formatDate = (date: Date): string => {
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
  };

  // 组件加载时获取历史任务
  useEffect(() => {
    loadHistoryTasks();
  }, []);

  // 获取差异标签样式
  const getDifferenceBadgeStyle = (difference: string) => {
    if (difference === "一致") {
      return "bg-gradient-to-r from-green-500 to-green-600 text-white";
    } else {
      return "bg-gradient-to-r from-red-500 to-red-600 text-white";
    }
  };

  const handleCleanupHistory = async () => {
    if (!authToken) {
      toast.error("未找到认证令牌，请重新登录");
      return;
    }

    if (selectedTaskIds.length === 0) {
      toast.error("请至少选择一条记录");
      return;
    }

    setCleanupLoading(true);
    let expectedCount = 0;
    let cleanedCount = 0;
    let cleanupType = cleanupMode;
    let cutoffDateStr = "";

    try {
      if (cleanupMode === "selected") {
        // 清理选中的记录：逐个调用 DELETE 接口
        expectedCount = selectedTaskIds.length;
        for (const taskId of selectedTaskIds) {
          const response = await fetch(
            `${GATEWAY_URL}/api/history/task/${taskId}`,
            {
              method: "DELETE",
              headers: {
                "Content-Type": "application/json",
                "X-User-Level": userLevel || "operator",
              },
            },
          );
          const result = await response.json();
          if (result.code === 200) {
            cleanedCount++;
          }
        }
      } else {
        // 清理选中之前的全部历史记录（不包含选中任务本身）
        const selectedTasks = tasks.filter((t) =>
          selectedTaskIds.includes(t.taskId),
        );
        if (selectedTasks.length === 0) {
          toast.error("未找到选中的任务");
          return;
        }

        // 找出最早的任务日期（本地时间）
        const minDate = new Date(
          Math.min(...selectedTasks.map((t) => t.taskDate.getTime())),
        );
        // 归一化到当天 00:00:00（本地）
        minDate.setHours(0, 0, 0, 0);
        const year = minDate.getFullYear();
        const month = String(minDate.getMonth() + 1).padStart(2, "0");
        const day = String(minDate.getDate()).padStart(2, "0");
        cutoffDateStr = `${year}-${month}-${day}`;

        console.log(
          `[清理] 最早选中任务日期: ${minDate.toLocaleDateString()}, 截止日期: ${cutoffDateStr}（不包含当天）`,
        );

        const response = await fetch(`${GATEWAY_URL}/api/history/cleanup`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-Level": userLevel || "operator",
          },
          body: JSON.stringify({
            cutoff_date: cutoffDateStr,
          }),
        });

        const result = await response.json();
        console.log("[清理] 后端响应:", result);

        if (result.code === 200) {
          cleanedCount = result.data.cleaned_count;
          expectedCount = cleanedCount; // 实际删除数量
        } else {
          throw new Error(result.message || "清理失败");
        }
      }

      // 根据删除结果判断状态和显示消息
      let status: "success" | "partial" | "failed";
      let toastMessage: string;

      if (cleanedCount === 0) {
        status = "failed";
        if (cleanupMode === "selected") {
          toastMessage = `删除失败：未能删除任何选中的记录（共 ${expectedCount} 条）`;
        } else {
          toastMessage = `删除失败：未能删除任何记录（截止日期 ${cutoffDateStr} 之前）`;
        }
        toast.error(toastMessage);
      } else if (cleanedCount < expectedCount) {
        status = "partial";
        if (cleanupMode === "selected") {
          toastMessage = `部分删除成功：成功 ${cleanedCount} 条，失败 ${expectedCount - cleanedCount} 条`;
        } else {
          toastMessage = `部分删除成功：成功 ${cleanedCount} 条，失败 ${expectedCount - cleanedCount} 条`;
        }
        toast.warning(toastMessage);
      } else {
        status = "success";
        if (cleanupMode === "selected") {
          toastMessage = `成功删除 ${cleanedCount} 条选中的记录`;
        } else {
          toastMessage = `成功删除 ${cleanedCount} 条记录（${cutoffDateStr} 之前）`;
        }
        toast.success(toastMessage);
      }

      // 记录操作日志
      await addOperationLog({
        operation_type: "system_cleanup",
        user_id: authToken || undefined,
        user_name: userName || undefined,
        action: "删除盘点任务",
        target:
          cleanupMode === "selected"
            ? `选中的 ${expectedCount} 条记录`
            : `${cutoffDateStr} 之前的全部记录`,
        status: status,
        details: {
          cleanup_type: cleanupType,
          expected_count: expectedCount,
          cleaned_count: cleanedCount,
          failed_count: expectedCount - cleanedCount,
          cutoff_date: cutoffDateStr || undefined,
          task_ids: cleanupMode === "selected" ? selectedTaskIds : undefined,
        },
      });

      // 清空选中状态
      setSelectedTaskIds([]);

      // 重新加载历史任务列表
      await loadHistoryTasks();
    } catch (error) {
      console.error("清理历史数据失败:", error);
      const errorMessage = error instanceof Error ? error.message : "未知错误";
      toast.error("清理历史数据失败: " + errorMessage);

      // 记录失败的操作日志
      await addOperationLog({
        operation_type: "system_cleanup",
        user_id: authToken || undefined,
        user_name: userName || undefined,
        action: "删除盘点任务",
        target:
          cleanupMode === "selected"
            ? `选中的 ${selectedTaskIds.length} 条记录`
            : "选中之前的全部记录",
        status: "failed",
        details: {
          cleanup_type: cleanupType,
          expected_count: expectedCount,
          cleaned_count: cleanedCount,
          error: errorMessage,
        },
      });
    } finally {
      setCleanupLoading(false);
      setShowCleanupDialog(false);
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

          <div className="flex items-center space-x-4">
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
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        {/* 页面标题和导航 */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold text-green-800">盘点历史记录</h2>
            <p className="text-gray-600">查看历史盘点任务和结果详情</p>
          </div>
        </div>

        {/* 主要内容区域：左右布局 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：历史任务列表 */}
          <div className="lg:col-span-1 bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
            {/* 标题 */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <div className="flex justify-between items-center">
                <h4 className="text-lg font-semibold text-gray-800">
                  盘点任务列表
                </h4>
                <div className="flex items-center space-x-2">
                  {userLevel === "admin" && (
                    <button
                      onClick={handleCleanupClick}
                      disabled={selectedTaskIds.length === 0}
                      className={`text-sm px-3 py-1.5 rounded-lg transition-colors flex items-center ${
                        selectedTaskIds.length === 0
                          ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                          : "bg-red-50 text-red-600 hover:bg-red-100"
                      }`}
                    >
                      <i className="fa-solid fa-trash-alt mr-1"></i>
                      清理历史 ({selectedTaskIds.length})
                    </button>
                  )}
                  <div className="flex items-center text-sm text-gray-500">
                    <i className="fa-solid fa-filter mr-2"></i>
                    <span>近6个月内</span>
                  </div>
                </div>
              </div>
            </div>

            {loading ? (
              // 加载状态
              <div className="p-12 text-center">
                <i className="fa-solid fa-spinner fa-spin text-3xl text-green-600 mb-4"></i>
                <p className="text-gray-600">加载历史任务...</p>
              </div>
            ) : tasks.length === 0 ? (
              // 无数据状态
              <div className="p-12 text-center">
                <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mx-auto mb-4">
                  <i className="fa-solid fa-clipboard-list text-2xl"></i>
                </div>
                <h5 className="text-lg font-semibold text-gray-700 mb-2">
                  暂无历史任务
                </h5>
                <p className="text-gray-500 mb-6">近期没有盘点任务记录</p>
              </div>
            ) : (
              // 任务列表
              <div className="divide-y divide-gray-100">
                {/* 全选控制栏 */}
                {userLevel === "admin" && (
                  <div className="px-4 py-2 bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="selectAll"
                        checked={
                          selectedTaskIds.length === tasks.length &&
                          tasks.length > 0
                        }
                        onChange={toggleSelectAll}
                        className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <label
                        htmlFor="selectAll"
                        className="ml-2 text-sm text-gray-600 cursor-pointer"
                      >
                        全选 ({selectedTaskIds.length}/{tasks.length})
                      </label>
                    </div>
                  </div>
                )}
                {tasks.map((task) => (
                  <div
                    key={task.taskId}
                    className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                      selectedTask?.taskId === task.taskId ? "bg-green-50" : ""
                    }`}
                    onClick={() => handleSelectTask(task)}
                  >
                    <div className="flex items-center">
                      {/* 选择框（仅管理员可见） */}
                      {userLevel === "admin" && (
                        <div
                          className="flex-shrink-0 mr-3"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={selectedTaskIds.includes(task.taskId)}
                            onChange={() => toggleTaskSelection(task.taskId)}
                            className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                          />
                        </div>
                      )}
                      <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-gradient-to-r from-blue-100 to-blue-50 flex items-center justify-center text-blue-600 mr-4">
                        <i className="fa-solid fa-clipboard-check text-xl"></i>
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <h5 className="font-medium text-gray-900">
                            {task.taskId}
                          </h5>
                          <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">
                            有效
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          <i className="fa-solid fa-calendar mr-1"></i>
                          {formatDate(task.taskDate)}
                        </p>
                        <div className="flex items-center mt-2">
                          <span className="text-xs text-gray-400">
                            <i className="fa-solid fa-file-excel mr-1"></i>
                            {task.fileName}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 右侧：任务详情 */}
          <div className="lg:col-span-2">
            {selectedTask ? (
              <div className="space-y-6">
                {/* 任务详情卡片 */}
                <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
                  <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-green-50 to-blue-50">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center">
                      <div>
                        <h4 className="text-xl font-bold text-green-800">
                          {selectedTask.taskId}
                        </h4>
                        <p className="text-gray-600">
                          <i className="fa-solid fa-calendar mr-1"></i>
                          盘点时间: {formatDate(selectedTask.taskDate)}
                        </p>
                      </div>
                      <div className="mt-2 md:mt-0">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                          <i className="fa-solid fa-check-circle mr-1"></i>
                          已盘点 {taskDetails.length} 个储位
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 储位选择器 */}
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h5 className="text-sm font-medium text-gray-700 mb-3">
                      选择储位查看详情
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {taskDetails.map((detail) => (
                        <button
                          key={detail.储位名称}
                          onClick={() => handleSelectPosition(detail.储位名称)}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                            selectedPosition === detail.储位名称
                              ? "bg-gradient-to-r from-green-500 to-green-600 text-white shadow-md"
                              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                          }`}
                        >
                          {detail.储位名称}
                          <span className="ml-2 text-xs">
                            ({detail.品规名称})
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* 详情表格和图片 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 左侧：盘点详情表格 */}
                  <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
                    <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                      <h5 className="text-lg font-semibold text-gray-800">
                        盘点详情
                      </h5>
                      <p className="text-sm text-gray-500">
                        储位: {selectedPosition || "未选择"}
                      </p>
                    </div>
                    <div className="p-6">
                      {selectedPosition ? (
                        <div className="space-y-4">
                          {taskDetails
                            .filter((d) => d.储位名称 === selectedPosition)
                            .map((detail) => (
                              <div key={detail.序号} className="space-y-3">
                                <div className="grid grid-cols-2 gap-4">
                                  <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500">
                                      品规名称
                                    </p>
                                    <p className="font-medium">
                                      {detail.品规名称}
                                    </p>
                                  </div>
                                  <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500">
                                      实际品规
                                    </p>
                                    <p className="font-medium">
                                      {detail.实际品规}
                                    </p>
                                  </div>
                                  <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500">
                                      库存数量
                                    </p>
                                    <p className="font-medium text-blue-600">
                                      {detail.库存数量}
                                    </p>
                                  </div>
                                  <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500">
                                      实际数量
                                    </p>
                                    <p className="font-medium text-blue-600">
                                      {detail.实际数量}
                                    </p>
                                  </div>
                                </div>

                                <div className="bg-gray-50 p-4 rounded-lg">
                                  <p className="text-xs text-gray-500 mb-2">
                                    差异结果
                                  </p>
                                  <span
                                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getDifferenceBadgeStyle(
                                      detail.差异,
                                    )}`}
                                  >
                                    <i
                                      className={`fa-solid ${
                                        detail.差异 === "一致"
                                          ? "fa-check-circle mr-1"
                                          : "fa-times-circle mr-1"
                                      }`}
                                    ></i>
                                    {detail.差异}
                                  </span>
                                  {detail.库存数量 === detail.实际数量 ? (
                                    <p className="text-green-600 text-sm mt-2">
                                      <i className="fa-solid fa-thumbs-up mr-1"></i>
                                      库存准确，无需调整
                                    </p>
                                  ) : (
                                    <p className="text-red-600 text-sm mt-2">
                                      <i className="fa-solid fa-exclamation-triangle mr-1"></i>
                                      库存差异:{" "}
                                      {Math.abs(
                                        detail.库存数量 - detail.实际数量,
                                      )}{" "}
                                      件
                                    </p>
                                  )}
                                </div>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mx-auto mb-4">
                            <i className="fa-solid fa-warehouse text-2xl"></i>
                          </div>
                          <p className="text-gray-500">请先选择要查看的储位</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 右侧：图片四宫格 */}
                  <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
                    <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                      <h5 className="text-lg font-semibold text-gray-800">
                        盘点图片记录
                      </h5>
                      <p className="text-sm text-gray-500">
                        储位: {selectedPosition || "未选择"}
                      </p>
                    </div>
                    <div className="p-6">
                      {selectedPosition && currentImages.length > 0 ? (
                        <div>
                          {imagesLoading && (
                            <div className="flex items-center justify-center py-8">
                              <i className="fa-solid fa-spinner fa-spin text-3xl text-green-600 mr-3"></i>
                              <span className="text-gray-600">
                                正在加载图片...
                              </span>
                            </div>
                          )}
                          {!imagesLoading && (
                            <div className="grid grid-cols-2 gap-4">
                              {currentImages.map((image, index) => (
                                <div
                                  key={index}
                                  className="aspect-square rounded-lg overflow-hidden border border-gray-200 bg-gray-100 relative group"
                                >
                                  <img
                                    crossOrigin="anonymous"
                                    src={image}
                                    alt={`盘点图片 ${index + 1}`}
                                    className="w-full h-full object-cover"
                                    loading="eager"
                                    onError={(e) => {
                                      // 图片加载失败时显示占位符
                                      e.currentTarget.style.display = "none";
                                      const parent =
                                        e.currentTarget.parentElement;
                                      if (parent) {
                                        const placeholder =
                                          document.createElement("div");
                                        placeholder.className =
                                          "w-full h-full flex items-center justify-center";
                                        placeholder.innerHTML = `
                <div class="text-center">
                  <i class="fa-solid fa-image text-4xl text-gray-300 mb-2"></i>
                  <p class="text-xs text-gray-500">图片 ${index + 1}</p>
                  <p class="text-xs text-gray-400 mt-1">加载失败</p>
                </div>
              `;
                                        parent.appendChild(placeholder);
                                      }
                                    }}
                                  />
                                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                                    <button
                                      className="bg-white bg-opacity-90 hover:bg-opacity-100 p-2 rounded-full shadow-lg"
                                      onClick={() =>
                                        window.open(image, "_blank")
                                      }
                                    >
                                      <i className="fa-solid fa-expand text-gray-700"></i>
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mx-auto mb-4">
                            <i className="fa-solid fa-images text-2xl"></i>
                          </div>
                          <p className="text-gray-500">暂无图片记录</p>
                          <p className="text-gray-400 text-sm mt-2">
                            选择储位后显示对应图片
                          </p>
                        </div>
                      )}

                      {/* 图片路径信息 */}
                      {selectedPosition && currentImages.length > 0 && (
                        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                          <p className="text-xs text-gray-500 mb-2">
                            <i className="fa-solid fa-info-circle mr-1"></i>
                            图片路径结构
                          </p>
                          <p className="text-sm text-gray-700 font-mono break-all">
                            {selectedTask.taskId}/{selectedPosition}/[照片路径]
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-md p-12 text-center">
                <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mx-auto mb-6">
                  <i className="fa-solid fa-clipboard-question text-3xl"></i>
                </div>
                <h5 className="text-xl font-bold text-gray-800 mb-4">
                  选择盘点任务
                </h5>
                <p className="text-gray-600 mb-6">
                  请在左侧选择一个历史盘点任务以查看详情
                </p>
                {/* <div className="text-sm text-gray-500">
                  <i className="fa-solid fa-lightbulb mr-1"></i>
                  提示：超过6个月的盘点任务已自动隐藏
                </div> */}
              </div>
            )}
          </div>
        </div>

        {/* 底部信息 */}
        {/* <div className="mt-6 text-sm text-gray-500">
          <div className="flex flex-col md:flex-row items-start md:items-center space-y-2 md:space-y-0 md:space-x-6">
            <div className="flex items-center">
              <i className="fa-solid fa-circle-info mr-2 text-green-600"></i>
              <span>
                提示：所有图片路径均为相对路径，实际显示时会拼接任务编号和储位名称
              </span>
            </div>
            <div className="flex items-center">
              <i className="fa-solid fa-clock mr-2 text-blue-600"></i>
              <span>时间格式：任务编号中的日期为YYYYMMDD格式</span>
            </div>
          </div>
        </div> */}
      </main>

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
                href="/"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                <i className="fa-solid fa-home mr-1"></i> 返回首页
              </a>
              <a
                href="#"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                <i className="fa-solid fa-question-circle mr-1"></i> 使用帮助
              </a>
              <a
                href="#"
                className="text-gray-500 hover:text-green-600 text-sm"
              >
                <i className="fa-solid fa-phone mr-1"></i> 技术支持
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* 清理历史数据确认对话框 */}
      {showCleanupDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
        >
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
            {/* 对话框头部 */}
            <div className="px-6 py-4 bg-red-50 border-b border-red-100">
              <div className="flex items-center">
                <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mr-3">
                  <i className="fa-solid fa-exclamation-triangle text-red-600"></i>
                </div>
                <h3 className="text-lg font-bold text-gray-800">
                  清理历史数据
                </h3>
              </div>
            </div>

            {/* 对话框内容 */}
            <div className="px-6 py-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">
                  <i className="fa-solid fa-info-circle mr-2"></i>
                  您已选中{" "}
                  <span className="font-bold">
                    {selectedTaskIds.length}
                  </span>{" "}
                  条记录
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  选择清理方式：
                </label>
                <div className="space-y-3">
                  <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                    <input
                      type="radio"
                      name="cleanupMode"
                      value="selected"
                      checked={cleanupMode === "selected"}
                      onChange={() => setCleanupMode("selected")}
                      className="mt-0.5 mr-3"
                    />
                    <div>
                      <span className="font-medium text-gray-800">
                        清理选中的记录
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        仅删除您选中的 {selectedTaskIds.length} 条记录
                      </p>
                    </div>
                  </label>
                  <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                    <input
                      type="radio"
                      name="cleanupMode"
                      value="beforeSelected"
                      checked={cleanupMode === "beforeSelected"}
                      onChange={() => setCleanupMode("beforeSelected")}
                      className="mt-0.5 mr-3"
                    />
                    <div>
                      <span className="font-medium text-gray-800">
                        清理选中之前的全部历史记录
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        删除第一条选中记录之前的所有记录
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-sm text-yellow-800">
                  <i className="fa-solid fa-exclamation-circle mr-2"></i>
                  此操作不可逆，清理后的数据将无法恢复！
                </p>
              </div>
            </div>

            {/* 对话框按钮 */}
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowCleanupDialog(false);
                  setSelectedTaskIds([]);
                }}
                disabled={cleanupLoading}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                取消
              </button>
              <button
                onClick={handleCleanupHistory}
                disabled={cleanupLoading}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {cleanupLoading ? (
                  <>
                    <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                    清理中...
                  </>
                ) : (
                  <>
                    <i className="fa-solid fa-trash-alt mr-2"></i>
                    确认清理
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 权限不足提示弹窗 */}
      {showPermissionDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
        >
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full mx-4 overflow-hidden">
            <div className="px-6 py-4 bg-orange-50 border-b border-orange-100">
              <div className="flex items-center">
                <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center mr-3">
                  <i className="fa-solid fa-lock text-orange-600"></i>
                </div>
                <h3 className="text-lg font-bold text-gray-800">权限不足</h3>
              </div>
            </div>
            <div className="px-6 py-6">
              <p className="text-gray-600 text-center">
                您当前是
                <span className="font-bold text-orange-600">操作员</span>
                ，无权执行清理历史操作。
              </p>
              <p className="text-sm text-gray-500 text-center mt-2">
                仅管理员可以清理历史记录。
              </p>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-center">
              <button
                onClick={() => setShowPermissionDialog(false)}
                className="px-6 py-2 rounded-lg bg-gray-600 text-white hover:bg-gray-700 transition-colors"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
