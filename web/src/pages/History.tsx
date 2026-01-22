import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/authContext";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "@/config/ip_address";
import * as XLSX from "xlsx";
import { useNavigate } from "react-router-dom";

// 历史任务类型定义
interface HistoryTask {
  taskId: string;
  taskDate: Date;
  fileName: string;
  isExpired: boolean;
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // 处理返回按钮点击
  const handleBack = () => {
    navigate("/dashboard");
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

  // 模拟从指定路径读取xlsx文件
  const loadHistoryTasks = async () => {
    setLoading(true);
    try {
      // 实际项目中，这里应该是从后端API获取文件列表
      // 这里我们模拟一个示例任务
      const mockTasks: HistoryTask[] = [
        {
          taskId: "HS2026011817",
          taskDate: parseTaskDate("HS2026011817") || new Date(2026, 0, 18),
          fileName: "HS2026011817.xlsx",
          isExpired: false,
        },
        {
          taskId: "HS2025121512",
          taskDate: parseTaskDate("HS2025121512") || new Date(2025, 11, 15),
          fileName: "HS2025121512.xlsx",
          isExpired: false,
        },
        {
          taskId: "HS2024072008",
          taskDate: parseTaskDate("HS2024072008") || new Date(2024, 6, 20),
          fileName: "HS2024072008.xlsx",
          isExpired: true, // 超过6个月
        },
        {
          taskId: "HS2026093014",
          taskDate: parseTaskDate("HS2026093014") || new Date(2026, 8, 30),
          fileName: "HS2026093014.xlsx",
          isExpired: false,
        },
        {
          taskId: "HS2025110511",
          taskDate: parseTaskDate("HS2025110511") || new Date(2025, 10, 5),
          fileName: "HS2025110511.xlsx",
          isExpired: false,
        },
      ].filter((task) => !task.isExpired); // 过滤掉过期任务

      console.log("加载的历史任务:", mockTasks);
      setTasks(mockTasks);

      // 默认选中第一个任务
      if (mockTasks.length > 0) {
        setSelectedTask(mockTasks[0]);
        await loadTaskDetails(mockTasks[0]);
      }
    } catch (error) {
      toast.error("加载历史任务失败");
      console.error("加载历史任务失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 加载任务详情
  const loadTaskDetails = async (task: HistoryTask) => {
    try {
      // 实际项目中，这里应该从后端API获取文件内容
      // 这里我们模拟解析xlsx文件
      const mockDetails: InventoryDetail[] = [
        {
          序号: 1,
          品规名称: "黄鹤楼",
          储位名称: "20-01-01",
          实际品规: "黄鹤楼",
          库存数量: 50,
          实际数量: 50,
          差异: "一致",
          照片1路径: "/3D_CAMERA/MAIN.JPEG",
          照片2路径: "/3D_CAMERA/DEPTH.JPEG",
          照片3路径: "/SCAN_CAMERA_1/1.JPEG",
          照片4路径: "/SCAN_CAMERA_2/1.JPEG",
        },
        {
          序号: 2,
          品规名称: "玉溪",
          储位名称: "20-01-02",
          实际品规: "玉溪",
          库存数量: 35,
          实际数量: 35,
          差异: "一致",
          照片1路径: "/3D_CAMERA/MAIN.JPEG",
          照片2路径: "/3D_CAMERA/DEPTH.JPEG",
          照片3路径: "/SCAN_CAMERA_1/2.JPEG",
          照片4路径: "/SCAN_CAMERA_2/2.JPEG",
        },
        {
          序号: 3,
          品规名称: "荷花",
          储位名称: "20-01-03",
          实际品规: "荷花",
          库存数量: 28,
          实际数量: 28,
          差异: "一致",
          照片1路径: "/3D_CAMERA/MAIN.JPEG",
          照片2路径: "/3D_CAMERA/DEPTH.JPEG",
          照片3路径: "/SCAN_CAMERA_1/3.JPEG",
          照片4路径: "/SCAN_CAMERA_2/3.JPEG",
        },
        {
          序号: 4,
          品规名称: "利群",
          储位名称: "20-01-04",
          实际品规: "利群",
          库存数量: 42,
          实际数量: 42,
          差异: "一致",
          照片1路径: "/3D_CAMERA/MAIN.JPEG",
          照片2路径: "/3D_CAMERA/DEPTH.JPEG",
          照片3路径: "/SCAN_CAMERA_1/4.JPEG",
          照片4路径: "/SCAN_CAMERA_2/4.JPEG",
        },
      ];

      setTaskDetails(mockDetails);

      // 默认选中第一个储位
      if (mockDetails.length > 0) {
        setSelectedPosition(mockDetails[0].储位名称);
        updateImagesForPosition(mockDetails[0]);
      }
    } catch (error) {
      toast.error(`加载任务 ${task.taskId} 详情失败`);
      console.error("加载任务详情失败:", error);
    }
  };

  // 更新当前显示的图片
  const updateImagesForPosition = (detail: InventoryDetail) => {
    // 构建完整的图片路径：任务编号+储位名称+照片路径
    const basePath = `${selectedTask?.taskId}/${detail.储位名称}`;
    const images = [
      `${basePath}${detail.照片1路径}`,
      `${basePath}${detail.照片2路径}`,
      `${basePath}${detail.照片3路径}`,
      `${basePath}${detail.照片4路径}`,
    ];
    setCurrentImages(images);
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
    if (detail) {
      updateImagesForPosition(detail);
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
          <div className="mt-4 md:mt-0 flex items-center text-gray-500">
            <i className="fa-solid fa-history mr-2"></i>
            <span>共 {tasks.length} 个有效任务</span>
            <button
              onClick={loadHistoryTasks}
              className="ml-4 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-sync-alt mr-1"></i>刷新
            </button>
            <input
              type="file"
              ref={fileInputRef}
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="ml-3 text-sm bg-green-100 hover:bg-green-200 text-green-700 px-3 py-1 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-upload mr-1"></i>上传Excel
            </button>
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
                <div className="flex items-center text-sm text-gray-500">
                  <i className="fa-solid fa-filter mr-2"></i>
                  <span>近6个月内</span>
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
                {tasks.map((task) => (
                  <div
                    key={task.taskId}
                    className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                      selectedTask?.taskId === task.taskId ? "bg-green-50" : ""
                    }`}
                    onClick={() => handleSelectTask(task)}
                  >
                    <div className="flex items-center">
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
                        <div className="grid grid-cols-2 gap-4">
                          {currentImages.map((image, index) => (
                            <div
                              key={index}
                              className="aspect-square rounded-lg overflow-hidden border border-gray-200 bg-gray-100 relative group"
                            >
                              {/* 在实际项目中，这里应该是真实的图片URL */}
                              <div className="w-full h-full flex items-center justify-center">
                                <div className="text-center">
                                  <i className="fa-solid fa-image text-4xl text-gray-300 mb-2"></i>
                                  <p className="text-xs text-gray-500">
                                    图片 {index + 1}
                                  </p>
                                  <p className="text-xs text-gray-400 mt-1 truncate px-2">
                                    {image.split("/").pop()}
                                  </p>
                                </div>
                              </div>
                              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                                <button className="bg-white bg-opacity-90 hover:bg-opacity-100 p-2 rounded-full shadow-lg">
                                  <i className="fa-solid fa-expand text-gray-700"></i>
                                </button>
                              </div>
                            </div>
                          ))}
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
                <div className="text-sm text-gray-500">
                  <i className="fa-solid fa-lightbulb mr-1"></i>
                  提示：超过6个月的盘点任务已自动隐藏
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 底部信息 */}
        <div className="mt-6 text-sm text-gray-500">
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
        </div>
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
    </div>
  );
}
