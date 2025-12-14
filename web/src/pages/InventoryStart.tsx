import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "@/config/ip_address";
import { useAuth } from "@/contexts/authContext";

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
  tobaccoName: string;
  tobaccoCode: string;
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
  tobaccoName: string;
  tobaccoCode: string;
}

export default function InventoryStart() {
  const navigate = useNavigate();

  const { authToken } = useAuth();
  const [inventoryTasks, setInventoryTasks] = useState<InventoryTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false);
  const [binsData, setBinsData] = useState<BinItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // 新增状态：选中的库位信息
  const [selectedBins, setSelectedBins] = useState<string[]>([]);
  // 新增状态：任务号输入框 - 作为全局变量
  const [taskNoInput, setTaskNoInput] = useState<string>("");

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

  // 库位信息更新显示
  useEffect(() => {
    if (binsData.length > 0) {
      // 确保首次渲染时显示数据
      console.log("Inventory data updated:", binsData);
    }
  }, [binsData]);

  // 获取库位信息
  const fetchBins = async (retryCount = 0): Promise<boolean> => {
    if (!authToken) {
      toast.error("未找到认证令牌，请重新登录");
      return false;
    }
    setLoading(true);
    try {
      const response = await fetch(
        `${GATEWAY_URL}/lms/getLmsBin?authToken=${authToken}`,
        {
          signal: AbortSignal.timeout(5000),
        }
      );
      if (response.status === 401) {
        toast.error("认证过期，请重新登录");
        return false;
      }
      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: "未知错误" }));
        if (retryCount < 2) {
          console.log(
            `请求失败（状态码: ${response.status}），重试 ${retryCount + 1}/2`
          );
          await new Promise((resolve) => setTimeout(resolve, 1000));
          return fetchBins(retryCount + 1);
        }
        toast.error(
          `获取库位信息失败: ${errorData.message || response.statusText}`
        );
        return false;
      }
      const data = await response.json();
      setBinsData(data);
      // 清空选中的库位
      setSelectedBins([]);
      return true;
    } catch (error) {
      toast.error("请求超时，请重试");

      return false;
    } finally {
      setLoading(false);
    }
  };

  // 获取盘点任务
  const fetchInventoryTask = async () => {
    if (!authToken) {
      toast.error("未找到认证令牌，请重新登录");
      return;
    }
    console.log("使用的 authToken:", authToken);
    console.log(
      "请求URL:",
      `${GATEWAY_URL}/lms/getCountTasks?authToken=${authToken}`
    );
    setTaskLoading(true);
    try {
      const response = await fetch(
        `${GATEWAY_URL}/lms/getCountTasks?authToken=${authToken}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      console.log("响应状态:", response.status);
      console.log("响应头:", Object.fromEntries(response.headers.entries()));
      if (!response.ok) {
        let errorMessage = `HTTP错误! 状态: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
          console.error("错误响应数据:", errorData);
        } catch (parseError) {
          // 如果响应不是JSON，尝试读取文本
          const text = await response.text();
          errorMessage = text || errorMessage;
          console.error("错误响应文本:", text);
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      console.log("获取盘点任务成功:", data);

      setInventoryTasks([...data]);

      toast.success("获取盘点任务成功");
      return data;
    } catch (error) {
      console.error("获取盘点任务失败:", error);
      // 根据错误类型显示不同的提示信息
      if (
        error instanceof TypeError &&
        error.message.includes("Failed to fetch")
      ) {
        toast.error("网络连接失败，请检查网络设置和后端服务状态");
      } else if (error instanceof Error) {
        // 显示具体的错误信息
        toast.error(`获取盘点任务失败: ${error.message}`);
      } else {
        toast.error("获取盘点任务失败，未知错误");
      }
      throw error;
    } finally {
      setTaskLoading(false);
    }
  };

  // 获取当前库位信息
  const fetchbinData = async () => {
    setIsLoading(true);
    try {
      const success = await fetchBins(); // 获取库位信息
      if (success) {
        toast.success(`成功获取库位信息`);
      }
    } catch (error) {
      console.error("获取库存数据失败:", error);
      toast.error("获取库存数据失败");
    } finally {
      setIsLoading(false);
    }
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
        0
      ),
      // 添加任务统计信息
      stats: {
        totalBins: inventoryTasks.length,
        totalQuantity: inventoryTasks.reduce(
          (sum, task) => sum + task.tobaccoQty,
          0
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

      // 可以选择跳转到任务清单详情页面或盘点进度页面
      // navigate('/inventory/manifest-detail');

      // 或者直接开始盘点
      // handleStartInventory();

      return taskManifest;
    } catch (error) {
      console.error("生成任务清单失败:", error);
      toast.error("生成任务清单失败，请重试");
    }
  };
  // 开始盘点 - 将任务编号传递给下一个页面
  const handleStartInventory = () => {
    // 检查是否有任务清单
    if (inventoryTasks.length === 0) {
      toast.error("请先创建盘点任务");
      return;
    }

    // if (!taskNoInput.trim()) {
    //   toast.error("请先填写任务号");
    //   return;
    // }

    // 首先生成任务清单
    const manifest = createTaskMainfest();

    if (manifest) {
      // 保存任务编号到本地存储，作为全局变量
      localStorage.setItem("currentTaskNo", taskNoInput);

      // 跳转到盘点进度页面，并传递任务编号和任务数据
      navigate("/inventory/progress", {
        state: {
          taskNo: taskNoInput,
          inventoryTasks: inventoryTasks,
          taskManifest: manifest,
        },
      });
    }
  };

  // 删除盘点任务
  const handleDeleteTask = (taskID: string) => {
    setInventoryTasks(inventoryTasks.filter((task) => task.taskID !== taskID));
    // 同时从选中列表中移除
    setSelectedTasks(selectedTasks.filter((id) => id !== taskID));
    toast.success("盘点任务已删除");
  };

  // 处理全选/全不选（库位信息）
  const handleSelectAllBins = () => {
    const allSelected = binsData.every((bin) =>
      selectedBins.includes(bin.binCode)
    );
    if (allSelected) {
      setSelectedBins([]);
    } else {
      setSelectedBins(binsData.map((bin) => bin.binCode));
    }
  };

  // 处理库位信息复选框选择
  const handleBinSelect = (binCode: string) => {
    setSelectedBins((prev) => {
      const isSelected = prev.includes(binCode);
      return isSelected
        ? prev.filter((id) => id !== binCode)
        : [...prev, binCode];
    });
  };

  // 将选中的库位信息添加到盘点任务
  const addSelectedBinsToTasks = () => {
    if (selectedBins.length === 0) {
      toast.error("请先选择库位信息");
      return;
    }

    // / 检查任务号是否填写
    if (!taskNoInput.trim()) {
      toast.error("请先填写任务编号");
      return;
    }

    // 使用输入的任务号
    const taskNo = taskNoInput.trim();

    const newTasks: InventoryTask[] = selectedBins
      .map((binCode) => {
        const bin = binsData.find((b) => b.binCode === binCode);
        if (!bin) return null;

        return {
          taskID: taskNo,
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
    taskID: "w-40", // 任务编号列宽度
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
          <button
            onClick={handleBack}
            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-all flex items-center"
          >
            <i className="fa-solid fa-arrow-left mr-2"></i>返回
          </button>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧操作区域 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-1"
          >
            <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 h-full">
              <h3 className="text-xl font-bold text-green-800 mb-6 pb-3 border-b border-gray-100">
                <i className="fa-solid fa-filter mr-2 text-green-600"></i>
                操作
              </h3>
              <div className="space-y-6">
                {/* 获取当前库位按钮 */}
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
                      <i className="fa-solid fa-database mr-2"></i>{" "}
                      获取当前库位信息
                    </>
                  )}
                </button>

                {/* 获取LMS盘点任务按钮 */}
                <button
                  onClick={fetchInventoryTask}
                  disabled={taskLoading}
                  className="w-full bg-blue-700 hover:bg-blue-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center"
                >
                  {taskLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 获取中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-list-check mr-2"></i>{" "}
                      获取LMS盘点任务
                    </>
                  )}
                </button>

                {/* 添加选中的库位到任务按钮 */}
                <button
                  onClick={addSelectedBinsToTasks}
                  disabled={selectedBins.length === 0}
                  className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center"
                >
                  <i className="fa-solid fa-plus mr-2"></i>
                  添加盘点库位 ({selectedBins.length})
                </button>
              </div>
            </div>
          </motion.div>
          {/* 右侧数据展示区域 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="lg:col-span-2"
          >
            <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
              <div className="p-6 border-b border-gray-100">
                <h3 className="text-xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-table mr-2 text-green-600"></i>
                  库位数据
                  <span className="ml-3 text-sm font-normal text-gray-500">
                    (LMS系统)
                  </span>
                </h3>
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
                      <h4 className="text-lg font-semibold text-green-800 mr-4">
                        库位信息（已选中 {selectedBins.length} 项）
                      </h4>
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          placeholder="请输入任务编号"
                          value={taskNoInput}
                          onChange={(e) => setTaskNoInput(e.target.value)}
                          className="border border-gray-300 rounded px-3 py-2 text-sm w-48 h-10"
                        />
                        <span className="text-sm text-gray-500">
                          当前任务编号: {taskNoInput || "未填写"}
                        </span>
                      </div>
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
                              key={index}
                              className="hover:bg-gray-50 transition-colors"
                            >
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 ${columnWidths.checkbox}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedBins.includes(item.binCode)}
                                  onChange={() => handleBinSelect(item.binCode)}
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

                {/* 盘点任务表 */}
                <div className="overflow-x-auto">
                  <div className="flex items-center mb-4">
                    <h4 className="text-lg font-semibold text-green-800 mr-4">
                      盘点任务（共 {inventoryTasks.length} 项）
                    </h4>
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
                          <th
                            className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${columnWidths.taskID}`}
                          >
                            任务编号
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryTasks.length > 0 ? (
                          inventoryTasks.map((task, index) => (
                            <tr
                              key={`${task.taskID}-${task.binCode}-${index}`}
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
                                  onClick={() => handleDeleteTask(task.taskID)}
                                  className="text-red-600 hover:text-red-900 flex items-center"
                                >
                                  <i className="fa-solid fa-trash mr-1"></i>{" "}
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
                              <td
                                className={`px-4 py-4 text-sm text-gray-700 truncate ${columnWidths.taskID}`}
                                title={task.taskID}
                              >
                                {task.taskID}
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
                    <button className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors flex items-center">
                      <i className="fa-solid fa-print mr-2"></i>打印
                    </button>
                    <button className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors flex items-center">
                      <i className="fa-solid fa-file-export mr-2"></i>导出
                    </button>
                    <button
                      className="px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded-lg transition-colors flex items-center"
                      onClick={() => {
                        createTaskMainfest();
                      }}
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
    </div>
  );
}
