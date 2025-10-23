import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { GATEWAY_URL } from '@/config/ip_address';
import { useAuth } from '@/contexts/authContext';

// 定义接口类型
interface Warehouse {
  id: string;
  name: string;
}

interface StorageArea {
  id: string;
  name: string;
  warehouseId: string;
}

interface Location {
  id: string;
  name: string;
  storageAreaId: string;
}

interface InventoryItem {
  id: string;
  productName: string;
  specification: string;
  quantity: number;
  unit: string;
  locationId: string;
}

// 定义盘点任务接口
interface CountingTask {
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

export default function InventoryStart() {
  const navigate = useNavigate();

  // 统一使用 useAuth 钩子
  const { authToken } = useAuth();
  const [bins, setBins] = useState<any[]>([]);
  const [tasks, setTasks] = useState<CountingTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false);
  const [inventoryData, setInventoryData] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // 新建盘点任务模态框状态
  const [isCreateTaskModalOpen, setIsCreateTaskModalOpen] = useState(false);
  const [newTask, setNewTask] = useState<Omit<CountingTask, 'status'>>({
    taskNo: 'T20251023005',
    taskDetailId: 'DT20251025005',
    binId: 'BIN-005',
    binDesc: 'A区-01排-02层',
    binCode: 'A-01-02',
    itemId: 'ITEM005',
    itemCode: 'YC-ZHONGHUA',
    itemDesc: '中华(硬盒)',
    invQty: 120.0,
    qtyUnit: '条',
    countQty: 0,
  });

  // 用于拖拽排序
  const dragItem = useRef<number | null>(null);
  const dragOverItem = useRef<number | null>(null);

  // 用于管理选中任务
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);

  // 确保在数据更新后正确显示
  useEffect(() => {
    if (inventoryData.length > 0) {
      // 确保首次渲染时显示数据
      console.log("Inventory data updated:", inventoryData);
    }
  }, [inventoryData]);

  // 确保在bins数据更新后正确设置inventoryData
  useEffect(() => {
    if (bins.length > 0) {
      // 将库位数据转换为库存数据格式
      const inventoryData = bins.map(bin => ({
        id: bin.binCode,
        productName: bin.binDesc,
        specification: '库位',
        quantity: bin.binQty,
        unit: '个',
        locationId: bin.binCode
      }));
      setInventoryData(inventoryData);
    }
  }, [bins]);

  // 获取库位信息
  const fetchBins = async (retryCount = 0): Promise<boolean> => {
    if (!authToken) {
      toast.error('未找到认证令牌，请重新登录');
      return false;
    }
    setLoading(true);
    try {
      const response = await fetch(`${GATEWAY_URL}/lms/getLmsBin?authToken=${authToken}`, {
        signal: AbortSignal.timeout(5000)
      });
      if (response.status === 401) {
        toast.error('认证过期，请重新登录');
        return false;
      }
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }));
        if (retryCount < 2) {
          console.log(`请求失败（状态码: ${response.status}），重试 ${retryCount + 1}/2`);
          await new Promise(resolve => setTimeout(resolve, 1000));
          return fetchBins(retryCount + 1);
        }
        toast.error(`获取库位信息失败: ${errorData.message || response.statusText}`);
        return false;
      }
      const data = await response.json();
      setBins(data);
      return true;
    } catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        toast.error('请求超时，请检查网络');
      } else {
        toast.error('网络异常，请重试');
      }
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 获取盘点任务（已修改，数据直接显示在库存区域）
  const fetchCountingTask = async () => {
    if (!authToken) {
      toast.error('未找到认证令牌，请重新登录');
      return;
    }
    console.log('使用的 authToken:', authToken);
    console.log('请求URL:', `${GATEWAY_URL}/lms/getCountTasks?authToken=${authToken}`);
    setTaskLoading(true);
    try {
      const response = await fetch(`${GATEWAY_URL}/lms/getCountTasks?authToken=${authToken}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      console.log('响应状态:', response.status);
      console.log('响应头:', Object.fromEntries(response.headers.entries()));
      if (!response.ok) {
        let errorMessage = `HTTP错误! 状态: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
          console.error('错误响应数据:', errorData);
        } catch (parseError) {
          // 如果响应不是JSON，尝试读取文本
          const text = await response.text();
          errorMessage = text || errorMessage;
          console.error('错误响应文本:', text);
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      console.log('获取盘点任务成功:', data);

      setTasks([...data]);

      // 保持原有库存数据，只更新盘点任务
      // setInventoryData(inventoryData);
      toast.success('获取盘点任务成功');
      return data;
    } catch (error) {
      console.error('获取盘点任务失败:', error);
      // 根据错误类型显示不同的提示信息
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        toast.error('网络连接失败，请检查网络设置和后端服务状态');
      } else if (error instanceof Error) {
        // 显示具体的错误信息
        toast.error(`获取盘点任务失败: ${error.message}`);
      } else {
        toast.error('获取盘点任务失败，未知错误');
      }
      throw error;
    } finally {
      setTaskLoading(false);
    }
  };

  // 获取当前库位信息（已修改，数据直接显示在库存区域）
  const fetchInventoryData = async () => {
    setIsLoading(true);
    try {
      const success = await fetchBins(); // 获取库位信息
      if (success) {
        toast.success(`成功获取库位信息`);
      }
    } catch (error) {
      console.error('获取库存数据失败:', error);
      toast.error('获取库存数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 辅助函数（避免重复逻辑）
  const getStatusText = (status: string) => {
    switch (status) {
      case '1': return '正常';
      case '2': return '预警';
      case '3': return '异常';
      default: return '已锁定';
    }
  };

  // 处理返回按钮点击
  const handleBack = () => {
    navigate('/dashboard');
  };


  // 生成任务清单
  const createTaskMainfest = () => {
    // 检查是否有选中的任务
    if (selectedTasks.length === 0) {
      toast.error('请先选择要生成清单的盘点任务');
      return;
    }

    // 从所有任务中筛选出选中的任务
    const selectedTaskList = tasks.filter(task =>
      selectedTasks.includes(task.taskDetailId)
    );

    // 创建任务清单对象
    const taskManifest = {
      id: `MANIFEST_${Date.now()}`,
      createdAt: new Date().toISOString(),
      taskCount: selectedTaskList.length,
      tasks: selectedTaskList,
      status: 'pending', // pending, in-progress, completed
      totalItems: selectedTaskList.reduce((sum, task) => sum + task.invQty, 0)
    };

    try {
      // 获取现有的任务清单列表
      const existingManifests = JSON.parse(localStorage.getItem('inventoryTaskManifests') || '[]');

      // 添加新的任务清单
      const updatedManifests = [...existingManifests, taskManifest];

      // 存储到本地存储
      localStorage.setItem('inventoryTaskManifests', JSON.stringify(updatedManifests));

      // 同时存储当前活动的任务清单（用于其他页面直接调用）
      localStorage.setItem('currentTaskManifest', JSON.stringify(taskManifest));

      // 显示成功消息
      toast.success(`成功生成任务清单，包含 ${selectedTaskList.length} 个任务`);

      // 可选：清空选中状态
      // setSelectedTasks([]);

      console.log('生成的任务清单:', taskManifest);

      // 可选：跳转到任务清单详情页面
      // navigate('/inventory/manifest-detail');

      return taskManifest;
    } catch (error) {
      console.error('生成任务清单失败:', error);
      toast.error('生成任务清单失败，请重试');
    }
  };

  // 实现导入本地盘点任务函数
  const setIsImportLocalTask = () => {
    // 创建隐藏的文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.csv';
    fileInput.style.display = 'none';

    // 添加change事件监听器
    fileInput.addEventListener('change', (event) => {
      const target = event.target as HTMLInputElement;
      const file = target.files?.[0];

      if (!file) {
        toast.error('未选择文件');
        return;
      }

      // 检查文件类型
      if (!file.name.endsWith('.csv')) {
        toast.error('请选择CSV文件');
        return;
      }

      // 读取文件内容
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          // 解析CSV内容
          const tasks = parseCSVContent(content);

          if (tasks.length > 0) {
            // 添加到现有任务列表
            setTasks(prevTasks => [...prevTasks, ...tasks]);
            toast.success(`成功导入 ${tasks.length} 条盘点任务`);
          } else {
            toast.error('CSV文件中没有有效的盘点任务数据');
          }
        } catch (error) {
          console.error('解析CSV文件失败:', error);
          toast.error('解析CSV文件失败，请检查文件格式');
        }
      };

      reader.onerror = () => {
        toast.error('读取文件失败');
      };

      reader.readAsText(file, 'UTF-8');

      // 清理
      document.body.removeChild(fileInput);
    });

    // 添加到DOM并触发点击
    document.body.appendChild(fileInput);
    fileInput.click();
  };

  // 解析CSV内容的辅助函数
  const parseCSVContent = (content: string): CountingTask[] => {
    const lines = content.split('\n');
    const tasks: CountingTask[] = [];

    // 跳过标题行（假设第一行是标题）
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      // 简单的CSV解析（处理逗号分隔）
      const columns = line.split(',').map(col => col.trim());

      if (columns.length >= 12) { // 确保有足够的列
        const task: CountingTask = {
          taskNo: columns[1] || `TASK_${Date.now()}_${i}`,
          taskDetailId: columns[2] || `DETAIL_${Date.now()}_${i}`,
          binId: columns[3] || '',
          binDesc: columns[4] || '',
          binCode: columns[5] || '',
          itemId: columns[6] || '',
          itemCode: columns[7] || '',
          itemDesc: columns[8] || '',
          invQty: Number(columns[9]) || 0,
          qtyUnit: columns[10] || '个',
          countQty: Number(columns[11]) || 0,
          status: mapStatus(columns[12] || '1')
        };

        tasks.push(task);
      }
    }

    return tasks;
  };

  // 状态映射辅助函数
  const mapStatus = (status: string): string => {
    const statusMap: { [key: string]: string } = {
      '未盘点': '1',
      '盘点中': '2',
      '已完成': '3',
      '正常': '1',
      '预警': '2',
      '异常': '3'
    };

    return statusMap[status] || '1';
  };

  // 处理新建盘点任务
  const handleCreateTask = () => {
    // 确保所有必填字段都有值
    if (!newTask.taskNo || !newTask.binDesc || !newTask.invQty || !newTask.qtyUnit) {
      toast.error('请填写所有必填字段');
      return;
    }
    // 生成唯一的 taskDetailId
    const taskDetailId = `TASK_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    // 创建新的盘点任务
    const newTaskItem: CountingTask = {
      ...newTask,
      taskDetailId,
      status: '1', // 默认状态为正常
    };
    // 添加到任务列表
    setTasks([...tasks, newTaskItem]);
    // 关闭模态框
    setIsCreateTaskModalOpen(false);
    // 清空表单
    setNewTask({
      taskNo: '',
      taskDetailId: '',
      binId: '',
      binDesc: '',
      binCode: '',
      itemId: '',
      itemCode: '',
      itemDesc: '',
      invQty: 0,
      qtyUnit: '',
      countQty: 0,
    });
    toast.success('新建盘点任务成功');
  };

  // 删除盘点任务
  const handleDeleteTask = (taskDetailId: string) => {
    setTasks(tasks.filter(task => task.taskDetailId !== taskDetailId));
    // 同时从选中列表中移除
    setSelectedTasks(selectedTasks.filter(id => id !== taskDetailId));
    toast.success('盘点任务已删除');
  };

  // 处理全选/全不选
  const handleSelectAll = () => {
    const allSelected = tasks.every(task => selectedTasks.includes(task.taskDetailId));
    if (allSelected) {
      setSelectedTasks([]);
    } else {
      setSelectedTasks(tasks.map(task => task.taskDetailId));
    }
  };

  // 处理复选框选择
  const handleTaskSelect = (taskDetailId: string) => {
    setSelectedTasks(prev => {
      const isSelected = prev.includes(taskDetailId);
      return isSelected
        ? prev.filter(id => id !== taskDetailId)
        : [...prev, taskDetailId];
    });
  };

  // 拖拽排序
  const onDragStart = (e: React.DragEvent, index: number) => {
    dragItem.current = index;
    e.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    const dragIndex = dragItem.current;
    if (dragIndex === null || dragIndex === index) return;

    const newTasks = [...tasks];
    const [movedItem] = newTasks.splice(dragIndex, 1);
    newTasks.splice(index, 0, movedItem);

    setTasks(newTasks);
    dragItem.current = null;
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* 背景图片 */}
      <div className="absolute inset-0 bg-cover bg-center opacity-5"
        style={{
          backgroundImage: 'url(https://lf-code-agent.coze.cn/obj/x-ai-cn/attachment/3868529628819536/背景参考_20250808011802.jfif)'
        }}>
      </div>
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
          {/* 左侧操作区域 - 已移除仓库、库区和库位选择 */}
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
                  onClick={fetchInventoryData}
                  disabled={isLoading}
                  className="w-full bg-green-700 hover:bg-green-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center mt-6"
                >
                  {isLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 获取中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-database mr-2"></i> 获取当前库位信息
                    </>
                  )}
                </button>
                {/* 获取LMS盘点任务按钮 */}
                <button
                  onClick={fetchCountingTask}
                  disabled={taskLoading}
                  className="w-full bg-blue-700 hover:bg-blue-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center mt-6"
                >
                  {taskLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 获取中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-list-check mr-2"></i> 获取LMS盘点任务
                    </>
                  )}
                </button>
                {/* 新建盘点任务按钮 */}
                <button
                  onClick={() => setIsCreateTaskModalOpen(true)}
                  className="w-full bg-purple-700 hover:bg-purple-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center mt-6"
                >
                  <i className="fa-solid fa-plus mr-2"></i> 新建盘点任务
                </button>

                {/* 导入本地盘点任务按钮 */}
                <button
                  onClick={() => setIsImportLocalTask(true)}
                  className="w-full bg-purple-700 hover:bg-purple-800 text-white font-bold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center mt-6"
                >
                  <i className="fa-solid fa-plus mr-2"></i> 导入本地盘点任务
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
                  <i className="fa-solid fa-table mr-2 text-green-600"></i>库存数据
                  <span className="ml-3 text-sm font-normal text-gray-500">
                    (单位: 箱)
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
                ) : inventoryData.length > 0 ? (
                  // 库位信息表格
                  <div className="overflow-x-auto mb-8">
                    <h4 className="text-lg font-semibold text-green-800 mb-4">库位信息</h4>
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序号</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">描述</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">数量</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">单位</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryData.map((item, index) => (
                          <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{index + 1}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <div className="text-sm font-medium text-gray-900">{item.productName}</div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.specification}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.quantity}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.unit}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  // 无数据状态
                  <div className="flex flex-col items-center justify-center h-full text-center p-8">
                    <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                      <i className="fa-solid fa-box-open text-gray-400 text-4xl"></i>
                    </div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">暂无库位信息</h4>
                    <p className="text-gray-500 max-w-md">
                      请在左侧点击"获取当前库位信息"按钮获取数据
                    </p>
                  </div>
                )}
                {/* 盘点任务表 */}
                <div className="overflow-x-auto">
                  <h4 className="text-lg font-semibold text-green-800 mb-4">盘点任务</h4>
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          <input
                            type="checkbox"
                            checked={tasks.length > 0 && selectedTasks.length === tasks.length}
                            onChange={handleSelectAll}
                            className="h-4 w-4 text-green-600 rounded border-gray-300"
                          />
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序号</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">任务编号</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">库位描述</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">库存数量</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">单位</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {tasks.length > 0 ? (
                        tasks.map((task, index) => (
                          <tr
                            key={task.taskDetailId}
                            className="hover:bg-gray-50 transition-colors cursor-move"
                            draggable={true}
                            onDragStart={(e) => onDragStart(e, index)}
                            onDragOver={onDragOver}
                            onDrop={(e) => onDrop(e, index)}
                          >
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                              <input
                                type="checkbox"
                                checked={selectedTasks.includes(task.taskDetailId)}
                                onChange={() => handleTaskSelect(task.taskDetailId)}
                                className="h-4 w-4 text-green-600 rounded border-gray-300"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{index + 1}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{task.taskNo}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{task.binDesc}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{task.invQty}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{task.qtyUnit}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                              {getStatusText(task.status)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <button
                                onClick={() => handleDeleteTask(task.taskDetailId)}
                                className="text-red-600 hover:text-red-900 flex items-center"
                              >
                                <i className="fa-solid fa-trash mr-1"></i> 删除
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={8} className="px-6 py-4 whitespace-nowrap text-center text-gray-500">
                            暂无盘点任务
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              {/* 底部操作栏 */}
              {inventoryData.length > 0 && (
                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
                  <div className="text-sm text-gray-500">
                    库位信息共 <span className="font-medium text-green-700">{inventoryData.length}</span> 条记录
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
                      <i className="fa-solid fa-check-circle mr-2"></i>生成任务清单
                    </button>
                    <button
                      className="px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded-lg transition-colors flex items-center"
                      onClick={() => {
                        // 跳转到盘点进度页面
                        navigate('/inventory/progress');
                      }}
                    >
                      <i className="fa-solid fa-check-circle mr-2"></i>开始盘点
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </main >
      {/* 新建盘点任务模态框 */}
      {
        isCreateTaskModalOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-plus mr-2 text-green-600"></i>
                  新建盘点任务
                </h3>
              </div>
              <div className="p-6">
                <form>
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        任务编号 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={newTask.taskNo}
                        onChange={(e) => setNewTask({ ...newTask, taskNo: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入任务编号"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        库位描述 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={newTask.binDesc}
                        onChange={(e) => setNewTask({ ...newTask, binDesc: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入库位描述"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        库存数量 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="number"
                        value={newTask.invQty}
                        onChange={(e) => setNewTask({ ...newTask, invQty: Number(e.target.value) })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入库存数量"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        单位 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={newTask.qtyUnit}
                        onChange={(e) => setNewTask({ ...newTask, qtyUnit: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入单位"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        库位ID
                      </label>
                      <input
                        type="text"
                        value={newTask.binId}
                        onChange={(e) => setNewTask({ ...newTask, binId: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入库位ID"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        库位编码
                      </label>
                      <input
                        type="text"
                        value={newTask.binCode}
                        onChange={(e) => setNewTask({ ...newTask, binCode: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入库位编码"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        商品ID
                      </label>
                      <input
                        type="text"
                        value={newTask.itemId}
                        onChange={(e) => setNewTask({ ...newTask, itemId: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入商品ID"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        商品编码
                      </label>
                      <input
                        type="text"
                        value={newTask.itemCode}
                        onChange={(e) => setNewTask({ ...newTask, itemCode: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="请输入商品编码"
                      />
                    </div>
                  </div>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      商品描述
                    </label>
                    <input
                      type="text"
                      value={newTask.itemDesc}
                      onChange={(e) => setNewTask({ ...newTask, itemDesc: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      placeholder="请输入商品描述"
                    />
                  </div>
                  <div className="flex justify-end space-x-3">
                    <button
                      type="button"
                      onClick={() => setIsCreateTaskModalOpen(false)}
                      className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      取消
                    </button>
                    <button
                      type="button"
                      onClick={handleCreateTask}
                      className="px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded-lg transition-colors"
                    >
                      确认新建
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )
      }
      {/* 页脚 */}
      <footer className="bg-white py-6 border-t border-gray-200 relative z-10 mt-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <p className="text-gray-500 text-sm">© 2025 中国烟草 - 智慧仓库盘点系统</p>
            </div>
            <div className="flex space-x-6">
              <a href="#" className="text-gray-500 hover:text-green-600 text-sm">使用帮助</a>
              <a href="#" className="text-gray-500 hover:text-green-600 text-sm">系统手册</a>
              <a href="#" className="text-gray-500 hover:text-green-600 text-sm">联系技术支持</a>
            </div>
          </div>
        </div>
      </footer>
    </div >
  );
}