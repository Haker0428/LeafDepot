import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "../config/ip_address";
import { useAuth } from "../contexts/authContext";
import { addOperationLog } from "../lib/operationLog";

// 库位信息结构体
interface BinItem {
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
  // 唯一标识符
  id: string;
}

// 盘点任务结构体
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
  id: string; // 唯一标识符
}

export default function InventoryStart() {
  const navigate = useNavigate();

  const { authToken, userName, userLevel, userId } = useAuth();
  const [inventoryTasks, setInventoryTasks] = useState<InventoryTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false);
  const [binsData, setBinsData] = useState<BinItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // 新增状态：选中的库位信息
  const [selectedBins, setSelectedBins] = useState<string[]>([]);
  // 新增状态：任务号输入框 - 作为全局变量
  const [taskNoInput, setTaskNoInput] = useState<string>("");

  // 新增状态：仓库和储区选择
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>("all");
  const [selectedArea, setSelectedArea] = useState<string>("all");
  // 下拉菜单选项（从 bins_data.xlsx 动态加载）
  const [warehouseOptions, setWarehouseOptions] = useState<{ value: string; label: string }[]>([]);
  const [areaOptions, setAreaOptions] = useState<{ value: string; label: string }[]>([]);
  const [positionOptions, setPositionOptions] = useState<{ value: string; label: string }[]>([]);
  // 位号区域多选
  const [selectedPositions, setSelectedPositions] = useState<string[]>([]);

  // 新增状态：确认对话框和消息提示
  const [showConfirmDialog, setShowConfirmDialog] = useState<boolean>(false);
  const [showMessage, setShowMessage] = useState<boolean>(false);
  const [messageType, setMessageType] = useState<"success" | "error" | "info">(
    "info",
  );
  const [messageContent, setMessageContent] = useState<string>("");

  // 生成任务号函数
  const generateTaskNo = () => {
    // 前缀（服务器名称缩写，这里使用衡水的缩写HS）
    const prefix = "HS";

    // 获取当前日期并格式化为YYYYMMDD
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const dateStr = `${year}${month}${day}`;

    // 从本地存储获取今日最后使用的序号
    const storageKey = `lastTaskNoIndex_${dateStr}`;
    const lastIndex = localStorage.getItem(storageKey);
    const currentIndex = lastIndex ? parseInt(lastIndex, 10) + 1 : 1;

    // 保存当前序号回本地存储
    localStorage.setItem(storageKey, String(currentIndex));

    // 生成完整的任务号
    const taskNo = `${prefix}${dateStr}${String(currentIndex).padStart(2, "0")}`;
    return taskNo;
  };

  // 生成储位唯一ID
  const generateBinId = (
    whCode: string,
    areaCode: string,
    binCode: string,
    binDesc: string,
  ): string => {
    // 优先用 binDesc（如 "01-01-01"），其次用 binCode
    return `${whCode}_${areaCode}_${binDesc || binCode}`;
  };

  // 为储位数据添加唯一ID
  const addUniqueIdsToBins = (bins: BinItem[]): BinItem[] => {
    return bins.map((bin) => ({
      ...bin,
      id: generateBinId(bin.whCode, bin.areaCode, bin.binCode, bin.binDesc),
    }));
  };

  // 模拟库位数据
  const mockBinData: BinItem[] = [
    {
      whCode: "WH001",
      areaCode: "A",
      areaName: "A区",
      binCode: "A001",
      binDesc: "A区001储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 50,
      tobaccoCode: "C001",
      tobaccoName: "黄鹤楼(硬盒)",
      rcsCode: "RCS001",
      id: "WH001_A_A001",
    },
    {
      whCode: "WH001",
      areaCode: "A",
      areaName: "A区",
      binCode: "A002",
      binDesc: "A区002储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 35,
      tobaccoCode: "C002",
      tobaccoName: "玉溪(软盒)",
      rcsCode: "RCS002",
      id: "WH001_A_A002",
    },
    {
      whCode: "WH001",
      areaCode: "B",
      areaName: "B区",
      binCode: "B001",
      binDesc: "B区001储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 28,
      tobaccoCode: "C003",
      tobaccoName: "荷花(细支)",
      rcsCode: "RCS003",
      id: "WH001_B_B001",
    },
    {
      whCode: "WH001",
      areaCode: "B",
      areaName: "B区",
      binCode: "B002",
      binDesc: "B区002储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 42,
      tobaccoCode: "C004",
      tobaccoName: "利群(新版)",
      rcsCode: "RCS004",
      id: "WH001_B_B002",
    },
    {
      whCode: "WH002",
      areaCode: "A",
      areaName: "A区",
      binCode: "A001",
      binDesc: "二号库A区001储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 60,
      tobaccoCode: "C005",
      tobaccoName: "ESSE(蓝盒)",
      rcsCode: "RCS005",
      id: "WH002_A_A001",
    },
    {
      whCode: "WH002",
      areaCode: "A",
      areaName: "A区",
      binCode: "A002",
      binDesc: "二号库A区002储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 45,
      tobaccoCode: "C006",
      tobaccoName: "云烟(印象)",
      rcsCode: "RCS006",
      id: "WH002_A_A002",
    },
    {
      whCode: "WH002",
      areaCode: "B",
      areaName: "B区",
      binCode: "B001",
      binDesc: "二号库B区001储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 30,
      tobaccoCode: "C007",
      tobaccoName: "南京(金陵十二钗)",
      rcsCode: "RCS007",
      id: "WH002_B_B001",
    },
    {
      whCode: "WH002",
      areaCode: "B",
      areaName: "B区",
      binCode: "B002",
      binDesc: "二号库B区002储位",
      maxQty: 100,
      binStatus: "1",
      tobaccoQty: 55,
      tobaccoCode: "C008",
      tobaccoName: "红塔山(经典)",
      rcsCode: "RCS008",
      id: "WH002_B_B002",
    },
  ];

  // 库位状态
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

  // 用于拖拽排序
  const dragItem = useRef<number | null>(null);
  const dragOverItem = useRef<number | null>(null);

  // 用于管理选中任务
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);

  // 组件加载时自动生成任务号
  useEffect(() => {
    const autoGeneratedTaskNo = generateTaskNo();
    setTaskNoInput(autoGeneratedTaskNo);
  }, []);

  // 页面加载时从 bins_data.xlsx 获取仓库、储区、位号区域下拉选项
  useEffect(() => {
    const loadDropdownOptions = async () => {
      if (!authToken) return;
      try {
        const url = `${GATEWAY_URL}/lms/getLmsBin?authToken=${encodeURIComponent(authToken)}&useLocal=true`;
        const response = await fetch(url, { method: "GET", headers: { "Content-Type": "application/json" } });
        if (!response.ok) return;
        const result = await response.json();
        const binList = Array.isArray(result) ? result : (result.data || []);

        // 提取唯一的仓库编码
        const whCodes = [...new Set(binList.map((b: BinItem) => b.whCode).filter(Boolean))];
        setWarehouseOptions(whCodes.map((code: string) => ({ value: code, label: code })));

        // 提取唯一的储区编码
        const areaCodes = [...new Set(binList.map((b: BinItem) => b.areaCode).filter(Boolean))];
        setAreaOptions(areaCodes.map((code: string) => ({ value: code, label: code })));

        // 提取唯一的位号区域（binDesc 的 AA 部分，如 "01" 来自 "01-01-01"）
        const positionCodes = [...new Set(
          binList
            .map((b: BinItem) => b.binDesc?.split("-")[0])
            .filter(Boolean)
        )];
        positionCodes.sort();
        setPositionOptions(positionCodes.map((code: string) => ({ value: code, label: code })));
      } catch (e) {
        console.error("加载仓库/储区下拉选项失败:", e);
      }
    };
    loadDropdownOptions();
  }, [authToken]);

  // 库位信息更新显示
  useEffect(() => {
    if (binsData.length > 0) {
      // 确保首次渲染时显示数据
      console.log("Inventory data updated:", binsData);
    }
  }, [binsData]);

  const fetchBins = async (
    warehouse: string,
    area: string,
    positions: string[],
  ): Promise<{ success: boolean; count: number }> => {
    if (!authToken) {
      toast.error("未找到认证令牌，请重新登录");
      return { success: false, count: 0 };
    }

    setIsLoading(true);
    try {
      // 使用 useLocal=true 从本地 bins_data.xlsx 读取最新数据
      const url = `${GATEWAY_URL}/lms/getLmsBin?authToken=${encodeURIComponent(authToken)}&useLocal=true`;
      const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`请求失败 (${response.status}): ${errorText}`);
      }

      const result = await response.json();

      // 根据实际接口返回格式解析数据
      let binList: BinItem[] = [];
      if (Array.isArray(result)) {
        binList = result;
      } else if (result.data && Array.isArray(result.data)) {
        binList = result.data;
      } else {
        throw new Error("接口返回的数据格式不正确，期望数组或 { data: [] }");
      }

      // 前端筛选仓库、储区和位号区域
      let filteredData = binList;
      if (warehouse !== "all") {
        filteredData = filteredData.filter((item) => item.whCode === warehouse);
      }
      if (area !== "all") {
        filteredData = filteredData.filter((item) => item.areaCode === area);
      }
      if (positions.length > 0) {
        filteredData = filteredData.filter((item) =>
          positions.includes(item.binDesc?.split("-")[0])
        );
      }

      // 为筛选后的数据添加唯一ID
      const dataWithIds = addUniqueIdsToBins(filteredData);
      setBinsData(dataWithIds);
      setSelectedBins([]);

      const filterInfo = [];
      if (warehouse !== "all") filterInfo.push(`${warehouse}仓库`);
      if (area !== "all") filterInfo.push(`${area}区`);
      if (positions.length > 0) filterInfo.push(`位号区域: ${positions.join(", ")}`);
      const filterText =
        filterInfo.length > 0 ? `（${filterInfo.join("，")}）` : "";

      toast.success(
        `成功获取库位信息${filterText}，共 ${filteredData.length} 条记录`,
      );
      return { success: true, count: filteredData.length };
    } catch (error) {
      console.error("获取库位信息失败:", error);
      toast.error(`获取库位信息失败: ${error.message}`);
      setBinsData([]); // 清空数据
      setSelectedBins([]);
      return { success: false, count: 0 };
    } finally {
      setIsLoading(false);
    }
  };
  // 获取盘点任务
  const fetchInventoryTask = async () => {
    if (!authToken) {
      toast.error("未找到认证令牌，请重新登录");
      return;
    }
    setTaskLoading(true);
    try {
      // 模拟API请求延迟
      setTimeout(() => {
        // 使用库位数据的前3条作为模拟的盘点任务
        const mockTasks: InventoryTask[] = mockBinData
          .slice(0, 3)
          .map((bin) => ({
            ...bin,
            taskID: `TASK_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
          }));

        setInventoryTasks(mockTasks);
        setTaskLoading(false);
        toast.success("成功获取盘点任务");
      }, 1000);
    } catch (error) {
      console.error("获取盘点任务失败:", error);
      toast.error("获取盘点任务失败，使用模拟数据");

      // 发生错误时，使用模拟数据
      setTimeout(() => {
        const mockTasks: InventoryTask[] = mockBinData
          .slice(0, 3)
          .map((bin) => ({
            ...bin,
            taskID: `TASK_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
          }));

        setInventoryTasks(mockTasks);
        setTaskLoading(false);
        toast.info("已使用模拟任务数据");
      }, 500);
    }
  };

  // 获取当前库位信息
  const fetchbinData = async () => {
    await fetchBins(selectedWarehouse, selectedArea, selectedPositions);
  };

  // 处理返回按钮点击
  const handleBack = () => {
    navigate("/dashboard");
  };

  // 生成任务清单
  const createTaskMainfest = () => {
    // 检查盘点任务表格是否为空
    if (inventoryTasks.length === 0) {
      toast.error("请先创建盘点任务");
      return;
    }

    // 创建任务清单对象，使用盘点任务表格中的全部任务
    const taskManifest = {
      id: `MANIFEST_${Date.now()}`,
      taskNo: taskNoInput || "未命名任务", // 添加任务编号
      createdAt: new Date().toISOString(),
      taskCount: inventoryTasks.length,
      tasks: [...inventoryTasks], // 复制当前所有任务
      status: "pending", // pending, in-progress, completed
      totalItems: inventoryTasks.reduce(
        (sum, task) => sum + task.tobaccoQty,
        0,
      ),
      // 添加任务统计信息
      stats: {
        totalBins: inventoryTasks.length,
        totalQuantity: inventoryTasks.reduce(
          (sum, task) => sum + task.tobaccoQty,
          0,
        ),
        uniqueItems: new Set(inventoryTasks.map((task) => task.tobaccoName))
          .size,
        uniqueLocations: new Set(inventoryTasks.map((task) => task.binCode))
          .size,
      },
    };

    try {
      // 保存到本地存储，作为全局变量供下一个页面使用
      localStorage.setItem("currentTaskManifest", JSON.stringify(taskManifest));

      // 同时保存任务编号，因为下一个页面可能需要单独使用
      localStorage.setItem("currentTaskNo", taskNoInput);

      // 显示成功消息
      toast.success(`成功生成任务清单，包含 ${inventoryTasks.length} 个任务`);

      console.log("生成的任务清单:", taskManifest);

      return taskManifest;
    } catch (error) {
      console.error("生成任务清单失败:", error);
      toast.error("生成任务清单失败，请重试");
      return null;
    }
  };

  // 生成任务清单并记录日志
  const handleCreateManifest = async () => {
    const manifest = createTaskMainfest();
    // 仅生成任务清单，不单独记录日志
    // 日志记录在 handleStartInventory 中统一处理
  };

  // 开始盘点 - 将任务编号传递给下一个页面
  const handleStartInventory = async () => {
    // 检查是否有任务清单
    if (inventoryTasks.length === 0) {
      toast.error("请先创建盘点任务");
      return;
    }

    // 首先生成任务清单
    const manifest = createTaskMainfest();

    if (manifest) {
      // 保存任务编号到本地存储，作为全局变量
      localStorage.setItem("currentTaskNo", taskNoInput);

      // 确保传递选中的库位信息给盘点进度页面
      const selectedLocation = {
        warehouseId: inventoryTasks[0].whCode,
        warehouseName: `仓库${inventoryTasks[0].whCode}`,
        storageAreaId: inventoryTasks[0].areaCode,
        storageAreaName: inventoryTasks[0].areaName,
        locationId: inventoryTasks[0].binCode,
        locationName: inventoryTasks[0].binDesc,
      };

      // 记录操作日志 - 合并为"生成任务清单"
      await addOperationLog({
        operation_type: "inventory",
        user_id: userId || undefined,
        user_name: userName || undefined,
        action: "生成任务清单",
        target: taskNoInput,
        status: "success",
        details: {
          task_no: taskNoInput,
          task_count: inventoryTasks.length,
          total_quantity: manifest.totalItems,
          start_time: new Date().toISOString(),
        },
      });

      // 跳转到盘点进度页面，并传递任务编号、任务数据和选中的库位信息
      navigate("/inventory/progress", {
        state: {
          taskNo: taskNoInput,
          inventoryTasks: inventoryTasks,
          taskManifest: manifest,
          selectedLocation: selectedLocation,
        },
      });
    }
  };

  // 删除盘点任务
  const handleDeleteTask = (taskID: string) => {
    // 确保只删除与传入的taskID完全匹配的任务
    setInventoryTasks((prevTasks) =>
      prevTasks.filter((task) => task.taskID !== taskID),
    );
    // 同时从选中列表中移除
    setSelectedTasks(selectedTasks.filter((id) => id !== taskID));
    toast.success("盘点任务已删除");
  };

  // 处理全选/全不选（库位信息）
  const handleSelectAllBins = () => {
    const allSelected = binsData.every((bin) => selectedBins.includes(bin.id));
    if (allSelected) {
      setSelectedBins([]);
    } else {
      setSelectedBins(binsData.map((bin) => bin.id));
    }
  };

  // 处理库位信息复选框选择
  const handleBinSelect = (binId: string) => {
    setSelectedBins((prev) => {
      const isSelected = prev.includes(binId);
      return isSelected ? prev.filter((id) => id !== binId) : [...prev, binId];
    });
  };

  // 将选中的库位信息添加到盘点任务
  const addSelectedBinsToTasks = () => {
    if (selectedBins.length === 0) {
      toast.error("请先选择库位信息");
      return;
    }

    // 检查任务号是否填写，如果为空则自动生成
    if (!taskNoInput.trim()) {
      const autoGeneratedTaskNo = generateTaskNo();
      setTaskNoInput(autoGeneratedTaskNo);
      toast.info(`已自动生成任务号: ${autoGeneratedTaskNo}`);
    }

    // 使用输入的任务号，如果为空则自动生成一个
    let taskNo = taskNoInput.trim();
    if (!taskNo) {
      taskNo = generateTaskNo();
      setTaskNoInput(taskNo);
    }

    // 过滤掉已经在任务列表中的库位（使用id判断）
    const existingBinIds = new Set(
      inventoryTasks.map(
        (task) =>
          task.id || generateBinId(task.whCode, task.areaCode, task.binCode),
      ),
    );
    const uniqueSelectedBins = selectedBins.filter(
      (binId) => !existingBinIds.has(binId),
    );

    if (uniqueSelectedBins.length === 0) {
      toast.warning("所选库位已全部在盘点任务中");
      return;
    }

    // 提示有多少个库位已存在
    const duplicateCount = selectedBins.length - uniqueSelectedBins.length;
    if (duplicateCount > 0) {
      toast.info(`已跳过 ${duplicateCount} 个已存在的库位`);
    }

    const newTasks: InventoryTask[] = uniqueSelectedBins
      .map((binId, index) => {
        const bin = binsData.find((b) => b.id === binId);
        if (!bin) return null;

        // 为每个任务生成唯一的taskID
        const uniqueTaskID = `${taskNo}_${Date.now()}_${index}`;

        return {
          taskID: uniqueTaskID,
          whCode: bin.whCode,
          areaCode: bin.areaCode,
          areaName: bin.areaName,
          binCode: bin.binCode,
          binDesc: bin.binDesc,
          maxQty: bin.maxQty,
          binStatus: bin.binStatus,
          tobaccoQty: bin.tobaccoQty,
          tobaccoName: bin.tobaccoName,
          tobaccoCode: bin.tobaccoCode,
          rcsCode: bin.rcsCode,
          id: bin.id, // 添加id字段
        };
      })
      .filter((task): task is InventoryTask => task !== null);

    setInventoryTasks((prevTasks) => [...prevTasks, ...newTasks]);
    toast.success(`成功添加 ${newTasks.length} 条盘点任务`);

    // 清空选中的库位
    setSelectedBins([]);
  };

  // 拖拽排序
  const onDragStart = (e: React.DragEvent, index: number) => {
    dragItem.current = index;
    e.dataTransfer.effectAllowed = "move";
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const onDrop = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    const dragIndex = dragItem.current;
    if (dragIndex === null || dragIndex === index) return;

    const newTasks = [...inventoryTasks];
    const [movedItem] = newTasks.splice(dragIndex, 1);
    newTasks.splice(index, 0, movedItem);

    setInventoryTasks(newTasks);
    dragItem.current = null;
  };

  // 统一的列宽度配置
  const columnWidths = {
    action: "w-20", // 操作列宽度
    checkbox: "w-20", // 复选框列宽度
    index: "w-16", // 序号列宽度
    whCode: "w-32", // 仓库编码列宽度
    areaCode: "w-32", // 储区编码列宽度
    binDesc: "w-40", // 储位名称列宽度
    tobaccoName: "w-48", // 品规名称列宽度
    tobaccoQty: "w-28", // 数量列宽度
    binStatus: "w-40", // 储位状态列宽度
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
          </div>
        </div>
      </header>
      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        {/* 页面标题 */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-green-800 flex items-center">
            <i className="fa-solid fa-clipboard-check mr-3 text-green-600"></i>
            开始盘点
          </h2>
          <p className="text-gray-600 mt-1">获取当前库位信息和盘点任务</p>
        </div>
        {/* 选择区域和数据展示区域 */}
        <div className="flex flex-col lg:flex-row gap-8">
          {/* 左侧操作区域 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:w-1/4"
          >
            <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 h-full flex flex-col">
              <h3 className="text-xl font-bold text-green-800 mb-6 pb-3 border-b border-gray-100">
                <i className="fa-solid fa-filter mr-2 text-green-600"></i>
                库位选择
              </h3>
              <div className="flex flex-col flex-grow space-y-6">
                {/* 仓库选择下拉框 */}
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    选择仓库
                  </label>
                  <select
                    value={selectedWarehouse}
                    onChange={(e) => setSelectedWarehouse(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                  >
                    <option value="all">全部仓库</option>
                    {warehouseOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* 储区选择下拉框 */}
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    选择储区
                  </label>
                  <select
                    value={selectedArea}
                    onChange={(e) => setSelectedArea(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                  >
                    <option value="all">全部储区</option>
                    {areaOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* 位号区域多选 */}
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    位号区域{selectedPositions.length > 0 ? ` (已选 ${selectedPositions.length} 个)` : ""}
                  </label>
                  <div className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white min-h-[42px] flex flex-wrap gap-1 items-center">
                    {positionOptions.length === 0 ? (
                      <span className="text-gray-400 text-sm">加载中...</span>
                    ) : selectedPositions.length === 0 ? (
                      <span className="text-gray-400 text-sm">全部位号区域</span>
                    ) : null}
                    {positionOptions.map((opt) => {
                      const checked = selectedPositions.includes(opt.value);
                      return (
                        <label
                          key={opt.value}
                          className={`flex items-center gap-1 px-2 py-0.5 rounded text-sm cursor-pointer select-none ${
                            checked
                              ? "bg-green-100 text-green-800 border border-green-300"
                              : "bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              if (checked) {
                                setSelectedPositions(selectedPositions.filter((p) => p !== opt.value));
                              } else {
                                setSelectedPositions([...selectedPositions, opt.value]);
                              }
                            }}
                            className="sr-only"
                          />
                          {opt.label}
                        </label>
                      );
                    })}
                  </div>
                </div>

                {/* 获取库位信息按钮 */}
                <button
                  onClick={fetchbinData}
                  disabled={isLoading}
                  className="w-full bg-green-700 hover:bg-green-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center"
                >
                  {isLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 获取中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-database mr-2"></i> 获取库位信息
                    </>
                  )}
                </button>

                {/* 空出来一段距离 - 保持弹性布局 */}
                <div className="flex-grow"></div>
              </div>

              {/* 空出来一段距离 - 保持弹性布局 */}
              <div className="flex-grow"></div>
            </div>
          </motion.div>
          {/* 右侧数据展示区域 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="lg:w-3/4"
          >
            <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-green-800 flex items-center">
                    <i className="fa-solid fa-table mr-2 text-green-600"></i>
                    库位数据
                    <span className="ml-3 text-sm font-normal text-gray-500">
                      (LMS系统)
                    </span>
                  </h3>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="自动生成，可手动修改"
                      value={taskNoInput}
                      onChange={(e) => setTaskNoInput(e.target.value)}
                      className="border border-gray-300 rounded px-3 py-2 text-sm w-64 h-10"
                    />
                    <button
                      onClick={() => {
                        const newTaskNo = generateTaskNo();
                        setTaskNoInput(newTaskNo);
                        toast.success(`已生成新任务号: ${newTaskNo}`);
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                    >
                      随机生成
                    </button>
                  </div>
                </div>
              </div>
              {/* 表格区域 */}
              <div className="flex-1 overflow-auto p-6">
                {/* 库位信息表 */}
                {isLoading ? (
                  // 加载状态
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="w-16 h-16 border-4 border-green-200 border-t-green-700 rounded-full animate-spin mb-4"></div>
                    <p className="text-gray-500">正在获取数据...</p>
                  </div>
                ) : binsData.length > 0 ? (
                  // 库位信息表格
                  <div className="mb-8">
                    <div className="flex items-center mb-4">
                      <h4 className="text-lg font-semibold text-green-800">
                        库位信息（已选中 {selectedBins.length} 项）
                      </h4>
                    </div>
                    {/* 可滚动容器 - 限制高度为20行 */}
                    <div className="overflow-x-auto overflow-y-auto max-h-[300px] border rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200 table-fixed">
                        <thead className="bg-gray-50 sticky top-0 z-10">
                          <tr>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.checkbox}`}
                            >
                              <input
                                type="checkbox"
                                checked={
                                  binsData.length > 0 &&
                                  selectedBins.length === binsData.length
                                }
                                onChange={handleSelectAllBins}
                                className="h-4 w-4 text-green-600 rounded border-gray-300"
                              />
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.index}`}
                            >
                              序号
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.whCode}`}
                            >
                              仓库编码
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.areaCode}`}
                            >
                              储区编码
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.binDesc}`}
                            >
                              储位名称
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.tobaccoName}`}
                            >
                              品规名称
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.tobaccoQty}`}
                            >
                              数量（件）
                            </th>
                            <th
                              className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.binStatus}`}
                            >
                              储位状态
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {binsData.map((item, index) => (
                            <tr
                              key={item.id}
                              className="hover:bg-gray-50 transition-colors"
                            >
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.checkbox}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedBins.includes(item.id)}
                                  onChange={() => handleBinSelect(item.id)}
                                  className="h-4 w-4 text-green-600 rounded border-gray-300"
                                />
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.index}`}
                              >
                                {index + 1}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-900 truncate ${columnWidths.whCode}`}
                                title={item.whCode}
                              >
                                {item.whCode}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.areaCode}`}
                                title={item.areaCode}
                              >
                                {item.areaCode}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.binDesc}`}
                                title={item.binDesc}
                              >
                                {item.binDesc}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.tobaccoName}`}
                                title={item.tobaccoName}
                              >
                                {item.tobaccoName}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.tobaccoQty}`}
                              >
                                {item.tobaccoQty}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.binStatus}`}
                              >
                                {binStatus(item.binStatus)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {/* 数据统计信息 */}
                    <div className="mt-2 text-sm text-gray-500">
                      共 {binsData.length}{" "}
                      条数据，当前显示前20条（滚动查看更多）
                    </div>
                  </div>
                ) : (
                  // 无数据状态
                  <div className="flex flex-col items-center justify-center h-full text-center p-8">
                    <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                      <i className="fa-solid fa-box-open text-gray-400 text-4xl"></i>
                    </div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      暂无库位信息
                    </h4>
                    <p className="text-gray-500 max-w-md">
                      请在左侧点击"获取当前库位信息"按钮获取数据
                    </p>
                  </div>
                )}

                {/* 添加盘点库位按钮 - 移动到这里 */}
                <button
                  onClick={addSelectedBinsToTasks}
                  disabled={selectedBins.length === 0}
                  className="w-full mb-6 bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center"
                >
                  <i className="fa-solid fa-check mr-2"></i>
                  添加盘点库位 ({selectedBins.length})
                </button>

                {/* 盘点任务表 */}
                <div className="overflow-x-auto">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-green-800 mr-4">
                      盘点任务（共 {inventoryTasks.length} 项）
                    </h4>
                    <button
                      onClick={() => {
                        if (inventoryTasks.length > 0) {
                          setShowConfirmDialog(true);
                        } else {
                          setShowMessage(true);
                          setMessageType("info");
                          setMessageContent("当前没有盘点任务");
                        }
                      }}
                      disabled={inventoryTasks.length === 0}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
                        inventoryTasks.length > 0
                          ? "bg-red-600 text-white hover:bg-red-700"
                          : "bg-gray-300 text-gray-500 cursor-not-allowed"
                      }`}
                    >
                      <i className="fa-solid fa-trash-can mr-1"></i> 全部删除
                    </button>
                  </div>
                  {/* 添加高度限制和滚动 */}
                  <div className="overflow-x-auto overflow-y-auto max-h-[300px] border rounded-lg">
                    <table className="min-w-full divide-y divide-gray-200 table-fixed">
                      <thead className="bg-gray-50 sticky top-0 z-10">
                        <tr>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.action}`}
                          >
                            操作
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.index}`}
                          >
                            序号
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.whCode}`}
                          >
                            仓库编码
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.areaCode}`}
                          >
                            储区编码
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.binDesc}`}
                          >
                            储位名称
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.tobaccoName}`}
                          >
                            品规名称
                          </th>
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.tobaccoQty}`}
                          >
                            数量（件）
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryTasks.length > 0 ? (
                          inventoryTasks.map((task, index) => (
                            <tr
                              key={task.id || task.taskID}
                              className="hover:bg-gray-50 transition-colors cursor-move"
                              draggable={true}
                              onDragStart={(e) => onDragStart(e, index)}
                              onDragOver={onDragOver}
                              onDrop={(e) => onDrop(e, index)}
                            >
                              <td
                                className={`px-4 py-4 text-sm ${columnWidths.action}`}
                              >
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation(); // 防止触发拖拽
                                    handleDeleteTask(task.taskID);
                                  }}
                                  className="text-red-600 hover:text-red-900 flex items-center"
                                >
                                  <i className="fa-solid fa-trash mr-1"></i>
                                </button>
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.index}`}
                              >
                                {index + 1}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-900 truncate ${columnWidths.whCode}`}
                                title={task.whCode}
                              >
                                {task.whCode}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.areaCode}`}
                                title={task.areaCode}
                              >
                                {task.areaCode}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.binDesc}`}
                                title={task.binDesc}
                              >
                                {task.binDesc}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.tobaccoName}`}
                                title={task.tobaccoName}
                              >
                                {task.tobaccoName}
                              </td>
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.tobaccoQty}`}
                              >
                                {task.tobaccoQty}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td
                              colSpan={8}
                              className="px-6 py-4 whitespace-nowrap text-center text-gray-500"
                            >
                              暂无盘点任务
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              {/* 底部操作栏 */}
              {binsData.length > 0 && (
                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
                  <div className="text-sm text-gray-500">
                    库位信息共{" "}
                    <span className="font-medium text-green-700">
                      {binsData.length}
                    </span>{" "}
                    条记录，盘点任务共{" "}
                    <span className="font-medium text-blue-700">
                      {inventoryTasks.length}
                    </span>{" "}
                    条记录
                  </div>
                  <div className="flex space-x-3">
                    <button
                      className="px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded-lg transition-colors flex items-center"
                      onClick={handleCreateManifest}
                    >
                      <i className="fa-solid fa-check-circle mr-2"></i>
                      生成任务清单
                    </button>
                    <button
                      className="px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded-lg transition-colors flex items-center"
                      onClick={handleStartInventory}
                    >
                      <i className="fa-solid fa-check-circle mr-2"></i>开始盘点
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
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

      {/* 自定义确认对话框 */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4"
          >
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mr-4">
                  <i className="fa-solid fa-exclamation-triangle text-red-600 text-xl"></i>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">确认删除</h3>
                  <p className="text-gray-600 mt-1">
                    确定要删除全部 {inventoryTasks.length} 个盘点任务吗？
                  </p>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end space-x-4">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => {
                  setInventoryTasks([]);
                  setShowConfirmDialog(false);
                  // 显示成功消息
                  setMessageType("success");
                  setMessageContent("所有盘点任务已删除");
                  setShowMessage(true);

                  // 3秒后自动关闭消息
                  setTimeout(() => setShowMessage(false), 3000);
                }}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                确认删除
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* 自定义消息提示 */}
      {showMessage && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50"
        >
          <div
            className={`px-6 py-4 rounded-lg shadow-lg flex items-center ${
              messageType === "success"
                ? "bg-green-50 border-l-4 border-green-500"
                : messageType === "error"
                  ? "bg-red-50 border-l-4 border-red-500"
                  : "bg-blue-50 border-l-4 border-blue-500"
            }`}
          >
            <i
              className={`fa-solid mr-3 text-xl ${
                messageType === "success"
                  ? "text-green-500"
                  : messageType === "error"
                    ? "text-red-500"
                    : "text-blue-500"
              }`}
            >
              {messageType === "success"
                ? "check-circle"
                : messageType === "error"
                  ? "times-circle"
                  : "info-circle"}
            </i>
            <p
              className={`font-medium ${
                messageType === "success"
                  ? "text-green-800"
                  : messageType === "error"
                    ? "text-red-800"
                    : "text-blue-800"
              }`}
            >
              {messageContent}
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
