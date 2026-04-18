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
  operator?: string;
  hasModified?: boolean;
  isValid?: boolean;
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
  修改记录: string;
  照片1路径: string;
  照片2路径: string;
  照片3路径: string;
  照片4路径: string;
}

// 历史任务详情元信息
interface TaskMeta {
  operator: string;
  hasModified: boolean;
  modifiedBins: string[];
  isValid: boolean;
}

export default function History() {
  const { userLevel, userName, authToken, logout } = useAuth();
  const [tasks, setTasks] = useState<HistoryTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<HistoryTask | null>(null);
  const [taskDetails, setTaskDetails] = useState<InventoryDetail[]>([]);
  const [taskMeta, setTaskMeta] = useState<TaskMeta>({ operator: "", hasModified: false, modifiedBins: [], isValid: true });
  const today = new Date().toISOString().split("T")[0];
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>(today);
  // 日历选择相关
  const [availableDates, setAvailableDates] = useState<Set<string>>(new Set());
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
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

  // 加载有数据的日期列表
  const loadAvailableDates = async () => {
    try {
      const response = await fetch(`${GATEWAY_URL}/api/history/available-dates`);
      const result = await response.json();
      if (result.code === 200 && result.data?.dates) {
        setAvailableDates(new Set(result.data.dates as string[]));
      }
    } catch (error) {
      console.error("加载可用日期失败:", error);
    }
  };

  // 1. 修改 loadHistoryTasks 函数：
  const loadHistoryTasks = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      const query = params.toString() ? `?${params.toString()}` : "";
      const response = await fetch(`${GATEWAY_URL}/api/history/tasks${query}`);
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
            operator: task.operator || "",
            hasModified: task.hasModified || false,
            isValid: task.isValid !== false,
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
            修改记录: item.修改记录 || "",
            照片1路径: item.照片1路径,
            照片2路径: item.照片2路径,
            照片3路径: item.照片3路径,
            照片4路径: item.照片4路径,
          }),
        );

        setTaskDetails(details);
        setTaskMeta({
          operator: result.data.operator || "",
          hasModified: result.data.hasModified || false,
          modifiedBins: result.data.modifiedBins || [],
          isValid: result.data.isValid !== undefined ? result.data.isValid : true,
        });

        // 默认选中第一个储位
      } else {
        toast.error(`加载任务 ${task.taskId} 详情失败: ${result.message}`);
      }
    } catch (error) {
      toast.error(`加载任务 ${task.taskId} 详情失败`);
      console.error("加载任务详情失败:", error);
    }
  };

  // 3. 修改 updateImagesForPosition 函数中的图片路径构建：
  // 处理选择任务
  const handleSelectTask = async (task: HistoryTask) => {
    setSelectedTask(task);
    await loadTaskDetails(task);
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
    loadAvailableDates();
    loadHistoryTasks();
  }, []);

  // 点击外部关闭日历
  useEffect(() => {
    if (!calendarOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".calendar-dropdown")) {
        setCalendarOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [calendarOpen]);

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

        {/* 日期筛选 — 日历选择器 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-sm font-medium text-gray-700">选择盘点日期：</span>

            {/* 当前筛选条件显示 */}
            <button
              onClick={() => setCalendarOpen(!calendarOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors text-sm"
            >
              <i className="fa-solid fa-calendar text-green-600"></i>
              <span className="text-green-800">
                {startDate ? `${startDate}` : "全部日期"}
              </span>
              <i className={`fa-solid fa-chevron-down text-xs text-green-600 transition-transform ${calendarOpen ? "rotate-180" : ""}`}></i>
            </button>

            {(startDate || endDate) && (
              <button
                onClick={() => {
                  setStartDate("");
                  setEndDate("");
                  loadHistoryTasks();
                }}
                className="px-3 py-2 text-gray-500 hover:text-gray-700 text-sm"
              >
                清除筛选
              </button>
            )}
            <button
              onClick={() => loadHistoryTasks()}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition-colors"
            >
              刷新
            </button>

            {/* 日历下拉 */}
            {calendarOpen && (
              <div className="relative">
                <div className="calendar-dropdown absolute top-full left-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 z-50 p-4 w-80">
                  {/* 月份导航 */}
                  <div className="flex items-center justify-between mb-4">
                    <button
                      onClick={() => {
                        const [y, m] = calendarMonth.split("-").map(Number);
                        const d = new Date(y, m - 2, 1);
                        setCalendarMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
                      }}
                      className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-600"
                    >
                      <i className="fa-solid fa-chevron-left"></i>
                    </button>
                    <span className="font-medium text-gray-800">
                      {calendarMonth.split("-")[0]}年 {parseInt(calendarMonth.split("-")[1])}月
                    </span>
                    <button
                      onClick={() => {
                        const [y, m] = calendarMonth.split("-").map(Number);
                        const d = new Date(y, m, 1);
                        setCalendarMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
                      }}
                      className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-600"
                    >
                      <i className="fa-solid fa-chevron-right"></i>
                    </button>
                  </div>

                  {/* 星期标题 */}
                  <div className="grid grid-cols-7 mb-1">
                    {["日", "一", "二", "三", "四", "五", "六"].map((d) => (
                      <div key={d} className="text-center text-xs text-gray-400 py-1">{d}</div>
                    ))}
                  </div>

                  {/* 日期格子 */}
                  <div className="grid grid-cols-7 gap-0.5">
                    {/* 填充上月末尾日期 */}
                    {(() => {
                      const [y, m] = calendarMonth.split("-").map(Number);
                      const firstDay = new Date(y, m - 1, 1).getDay();
                      return Array.from({ length: firstDay }, (_, i) => (
                        <div key={`pad-${i}`} className="h-8"></div>
                      ));
                    })()}

                    {/* 当月日期 */}
                    {(() => {
                      const [y, m] = calendarMonth.split("-").map(Number);
                      const daysInMonth = new Date(y, m, 0).getDate();
                      const todayStr = today;
                      return Array.from({ length: daysInMonth }, (_, i) => {
                        const day = i + 1;
                        const dateStr = `${calendarMonth}-${String(day).padStart(2, "0")}`;
                        const hasData = availableDates.has(dateStr);
                        const isStart = dateStr === startDate;
                        const isEnd = dateStr === endDate;
                        const isInRange = startDate && endDate && dateStr > startDate && dateStr < endDate;
                        const isSelected = isStart || isEnd;
                        return (
                          <button
                            key={day}
                            onClick={() => {
                              // 点一次即精确筛选当天
                              setStartDate(dateStr);
                              setEndDate(dateStr);
                              setSelectingEnd(false);
                              setCalendarOpen(false);
                              loadHistoryTasks();
                            }}
                            disabled={!hasData}
                            className={`h-8 rounded-lg text-sm flex flex-col items-center justify-center relative transition-colors
                              ${hasData ? "hover:bg-green-50 cursor-pointer" : "text-gray-300 cursor-not-allowed"}
                              ${isSelected ? "bg-green-600 text-white hover:bg-green-700" : ""}
                              ${isInRange ? "bg-green-100 text-green-800" : ""}
                            `}
                          >
                            {day}
                            {hasData && !isSelected && (
                              <span className="w-1 h-1 rounded-full bg-green-500 absolute bottom-0.5"></span>
                            )}
                          </button>
                        );
                      });
                    })()}
                  </div>

                  {/* 提示 */}
                  <p className="text-xs text-gray-400 mt-3 text-center">
                    点击日期筛选当天盘点记录。绿色圆点表示有盘点数据。
                  </p>
                </div>
              </div>
            )}
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
                          <span className={`text-xs px-2 py-1 rounded-full font-bold ${
                            task.isValid === false
                              ? "bg-red-100 text-red-700"
                              : task.hasModified
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-green-100 text-green-800"
                          }`}>
                            {task.isValid === false ? "无效" : task.hasModified ? "订正" : "有效"}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          <i className="fa-solid fa-calendar mr-1"></i>
                          {formatDate(task.taskDate)}
                          {task.operator && (
                            <>
                              <span className="mx-1">|</span>
                              <i className="fa-solid fa-user mr-1"></i>
                              {task.operator}
                            </>
                          )}
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
                {/* 任务信息横幅 */}
                <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
                  <div className="flex flex-col md:flex-row">
                    {/* 左侧：任务基本信息 */}
                    <div className="flex-1 px-6 py-5 border-b md:border-b-0 md:border-r border-gray-200">
                      <h4 className="text-3xl font-bold text-green-800 mb-2">{selectedTask.taskId}</h4>
                      <div className="flex flex-col gap-y-1 text-lg text-gray-600">
                        <span><i className="fa-solid fa-calendar mr-2 w-5"></i>{formatDate(selectedTask.taskDate)}</span>
                        <span><i className="fa-solid fa-user mr-2 w-5"></i>{taskMeta.operator || "-"}</span>
                        {taskMeta.hasModified ? (
                          <span className="font-bold text-yellow-700">
                            <i className="fa-solid fa-pen mr-2 w-5"></i>存在人工修改
                          </span>
                        ) : (
                          <span className="text-green-600">
                            <i className="fa-solid fa-circle-check mr-2 w-5"></i>无人工修改
                          </span>
                        )}
                      </div>
                    </div>
                    {/* 右侧：统计数字 + 详情按钮 */}
                    <div className="flex items-center gap-0">
                      {/* 盘点类型标志 */}
                      <div className="px-5 py-4 text-center border-r border-gray-200">
                        {taskMeta.isValid === false ? (
                          <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-red-200 text-red-900 border-2 border-red-400 whitespace-nowrap">
                            <i className="fa-solid fa-xmark mr-1"></i>无效盘点
                          </span>
                        ) : taskMeta.hasModified ? (
                          <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-yellow-200 text-yellow-900 border-2 border-yellow-400 whitespace-nowrap">
                            <i className="fa-solid fa-pen mr-1"></i>有效修正盘点
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-green-200 text-green-900 border-2 border-green-400 whitespace-nowrap">
                            <i className="fa-solid fa-check mr-1"></i>有效盘点
                          </span>
                        )}
                      </div>
                      {/* 统计区 */}
                      <div className="flex divide-x divide-gray-200">
                        <div className="px-5 py-4 text-center min-w-[80px]">
                          <p className="text-4xl font-bold text-gray-800">{taskDetails.length}</p>
                          <p className="text-sm text-gray-500 mt-0.5">下发库位</p>
                        </div>
                        <div className="px-5 py-4 text-center min-w-[80px] bg-green-50">
                          <p className="text-4xl font-bold text-green-600">{taskDetails.filter(d => d.差异 === "一致").length}</p>
                          <p className="text-sm text-green-600 mt-0.5">一致库位</p>
                        </div>
                        <div className="px-5 py-4 text-center min-w-[80px]">
                          <p className={`text-4xl font-bold ${taskDetails.length > 0 ? (taskDetails.filter(d => d.差异 !== "一致" || d.修改记录 === "人工修改").length > 0 ? "text-red-500" : "text-gray-400") : "text-gray-400"}`}>
                            {taskDetails.length > 0
                              ? `${Math.round(taskDetails.filter(d => d.差异 !== "一致" || d.修改记录 === "人工修改").length / taskDetails.length * 100)}%`
                              : "0%"}
                          </p>
                          <p className="text-sm text-gray-500 mt-0.5">异常比例</p>
                        </div>
                      </div>
                      {/* 详情大按钮，与横幅融合 */}
                      <button
                        onClick={() => selectedTask && navigate(`/inventory/history/${selectedTask.taskId}`)}
                        className="h-full px-6 py-4 bg-blue-600 hover:bg-blue-700 text-white transition-all flex flex-col items-center justify-center gap-1 rounded-tr-xl rounded-br-xl min-w-[120px]"
                        style={{ borderTopRightRadius: "0.75rem", borderBottomRightRadius: "0.75rem" }}
                      >
                        <i className="fa-solid fa-chart-bar text-2xl"></i>
                        <span className="text-base font-bold">详细信息</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 差异汇总表格 */}
                <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
                  <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                    <h5 className="text-2xl font-semibold text-gray-800">
                      <i className="fa-solid fa-triangle-exclamation mr-2 text-orange-500"></i>
                      异常库位 ({taskDetails.filter(d => d.差异 !== "一致" || d.修改记录 === "人工修改").length} 个)
                    </h5>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-base">
                      <thead className="bg-gray-50 text-gray-600 text-sm uppercase">
                        <tr>
                          <th className="px-5 py-4 text-left font-medium">库位号</th>
                          <th className="px-5 py-4 text-left font-medium">系统品规</th>
                          <th className="px-5 py-4 text-left font-medium">盘点品规</th>
                          <th className="px-5 py-4 text-center font-medium">系统数量</th>
                          <th className="px-5 py-4 text-center font-medium">盘点数量</th>
                          <th className="px-5 py-4 text-center font-medium">修改类型</th>
                        </tr>
                      </thead>
                      <tbody>
                        {taskDetails
                          .filter(d => d.差异 !== "一致" || d.修改记录 === "人工修改")
                          .map((detail, idx) => {
                            const isManualModified = detail.修改记录 === "人工修改";
                            return (
                              <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="px-5 py-4 font-medium text-gray-800">
                                  {detail.储位名称}
                                </td>
                                <td className="px-5 py-4 text-gray-600">
                                  {detail.品规名称}
                                </td>
                                <td className="px-5 py-4 text-gray-600">
                                  <span className={detail.实际品规 !== detail.品规名称 ? "text-red-600 font-medium" : ""}>
                                    {detail.实际品规 || "-"}
                                  </span>
                                </td>
                                <td className="px-5 py-4 text-center text-blue-600 font-medium">
                                  {detail.库存数量}
                                </td>
                                <td className="px-5 py-4 text-center font-medium">
                                  <span className={detail.差异 !== "一致" ? "text-red-600" : "text-gray-800"}>
                                    {detail.实际数量}
                                  </span>
                                </td>
                                <td className="px-5 py-4 text-center">
                                  {isManualModified ? (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-200 text-yellow-900 border border-yellow-400">
                                      <i className="fa-solid fa-pen mr-1"></i>人工修改
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-orange-200 text-orange-900 border border-orange-400">
                                      <i className="fa-solid fa-robot mr-1"></i>系统修改
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        {taskDetails.filter(d => d.差异 !== "一致" || d.修改记录 === "人工修改").length === 0 && (
                          <tr>
                            <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                              <i className="fa-solid fa-circle-check text-3xl mb-2 block"></i>
                              <p>所有库位盘点正常，无异常</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
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
