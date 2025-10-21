import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { GATEWAY_URL } from '@/config/ip_address'; // 导入常量
import { useAuth } from '@/contexts/authContext';

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
}

interface LocationInfo {
  warehouseId: string;
  warehouseName: string;
  storageAreaId: string;
  storageAreaName: string;
  locationId: string;
  locationName: string;
}

export default function InventoryProgress() {
  // 统一使用 useAuth 钩子
  const { authToken } = useAuth();
  const [bins, setBins] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false); // 为盘点任务添加单独的加载状态

  const navigate = useNavigate();
  const location = useLocation();
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [selectedLocation, setSelectedLocation] = useState<LocationInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // 从路由状态获取选中的库位信息
  useEffect(() => {
    if (location.state && location.state.selectedLocation) {
      setSelectedLocation(location.state.selectedLocation);
      // 模拟加载盘点数据
      loadInventoryData(location.state.selectedLocation);
    } else {
      toast.error('未获取到库位信息，请返回重新选择');
      setTimeout(() => navigate('/inventory/start'), 1500);
    }
  }, [location, navigate]);

  // 模拟加载盘点数据
  const loadInventoryData = (location: LocationInfo) => {
    // 模拟API请求延迟
    setTimeout(() => {
      // 模拟盘点数据，包含一些差异项
      const mockItems: InventoryItem[] = [
        {
          id: 'INV001',
          productName: '黄鹤楼',
          specification: '硬盒',
          systemQuantity: 50,
          actualQuantity: null,
          unit: '箱',
          locationId: location.locationId,
          locationName: location.locationName
        },
        {
          id: 'INV002',
          productName: '玉溪',
          specification: '软盒',
          systemQuantity: 35,
          actualQuantity: null,
          unit: '箱',
          locationId: location.locationId,
          locationName: location.locationName
        },
        {
          id: 'INV003',
          productName: '荷花',
          specification: '细支',
          systemQuantity: 28,
          actualQuantity: null,
          unit: '箱',
          locationId: location.locationId,
          locationName: location.locationName
        },
        {
          id: 'INV004',
          productName: '利群',
          specification: '新版',
          systemQuantity: 42,
          actualQuantity: null,
          unit: '箱',
          locationId: location.locationId,
          locationName: location.locationName
        },
        {
          id: 'INV005',
          productName: 'ESSE',
          specification: '蓝盒',
          systemQuantity: 60,
          actualQuantity: null,
          unit: '箱',
          locationId: location.locationId,
          locationName: location.locationName
        }
      ];

      setInventoryItems(mockItems);

      // 模拟进度更新
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 30) {
            clearInterval(interval);
            return 30; // 初始加载完成30%
          }
          return prev + 5;
        });
      }, 200);

      return () => clearInterval(interval);
    }, 1000);
  };

  // 处理实际数量输入变化
  const handleActualQuantityChange = (id: string, value: string) => {
    const numericValue = value ? parseInt(value, 10) : null;

    setInventoryItems(prevItems =>
      prevItems.map(item =>
        item.id === id
          ? { ...item, actualQuantity: numericValue }
          : item
      )
    );

    // 更新进度 - 每完成一个项目增加14% (70% / 5项)
    const completedCount = inventoryItems.filter(
      item => item.actualQuantity !== null && (item.id !== id || numericValue !== null)
    ).length;

    const newProgress = 30 + (completedCount / inventoryItems.length) * 70;
    setProgress(Math.min(Math.round(newProgress), 100));
  };

  // ✅ 修正：不再在异步函数中调用 useAuth
  const handleSaveInventoryToLMS = async () => {
    if (isSaving) return;
    try {
      setIsSaving(true);

      // 获取盘点结果数据
      const inventoryResults = [
        {
          taskDetailId: "DT20251021001",
          itemId: "ITEM001",
          countQty: 15,
        },
        {
          taskDetailId: "DT20251021002",
          itemId: "ITEM002",
          countQty: 8,
        }
      ];

      // ✅ 直接使用从函数组件顶部获取的 authToken
      const response = await fetch(`${GATEWAY_URL}/lms/setTaskResults`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'authToken': authToken || '',
        },
        body: JSON.stringify(inventoryResults),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          toast.success('盘点结果已成功上传至LMS');
          setProgress(100);
        } else {
          throw new Error(result.message || '上传失败');
        }
      } else {
        const errorText = await response.text();
        throw new Error(`LMS上传失败: ${errorText}`);
      }
    } catch (error) {
      console.error('上传盘点结果失败:', error);
      toast.error(`上传失败: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };


  // 处理保存盘点结果
  const handleSaveInventory = () => {
    // 检查是否所有项目都已输入实际数量
    const incompleteItems = inventoryItems.filter(item => item.actualQuantity === null);

    if (incompleteItems.length > 0) {
      toast.warning(`尚有 ${incompleteItems.length} 项未完成盘点，请完成后再保存`);
      return;
    }

    setIsSaving(true);

    // 模拟保存请求
    setTimeout(() => {
      setIsSaving(false);
      toast.success('盘点结果保存成功！');

      // 2秒后返回仪表盘
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    }, 1500);
  };

  // 处理返回按钮
  const handleBack = () => {
    navigate('/inventory/start');
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
            <i className="fa-solid fa-spinner fa-spin mr-3 text-green-600"></i>
            盘点进行中
          </h2>
          <p className="text-gray-600 mt-1">正在盘点选中库位的库存，请输入实际数量</p>
        </div>

        {/* 盘点进度 */}
        <div className="mb-8 bg-white rounded-xl shadow-md p-6 border border-gray-100">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-bold text-green-800">
              <i className="fa-solid fa-chart-line mr-2 text-green-600"></i>盘点进度
            </h3>
            <span className="text-2xl font-bold text-green-700">{progress}%</span>
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

          {/* 库位信息 */}
          {selectedLocation && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-gray-500">仓库</p>
                <p className="font-medium text-gray-800">{selectedLocation.warehouseName} ({selectedLocation.warehouseId})</p>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-gray-500">库区</p>
                <p className="font-medium text-gray-800">{selectedLocation.storageAreaName} ({selectedLocation.storageAreaId})</p>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-gray-500">库位</p>
                <p className="font-medium text-gray-800">{selectedLocation.locationName} ({selectedLocation.locationId})</p>
              </div>
            </div>
          )}
        </div>

        {/* 盘点区域和实时观察区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧盘点数据区域 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-2"
          >
            <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
              <div className="p-6 border-b border-gray-100">
                <h3 className="text-xl font-bold text-green-800">
                  <i className="fa-solid fa-table mr-2 text-green-600"></i>盘点数据录入
                  <span className="ml-3 text-sm font-normal text-gray-500">
                    (单位: 箱)
                  </span>
                </h3>
              </div>

              {/* 表格区域 */}
              <div className="flex-1 overflow-auto p-6">
                {inventoryItems.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序号</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">品规</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">规格</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">系统库存</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实际库存</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">差异</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {inventoryItems.map((item, index) => {
                          const difference = item.actualQuantity !== null ? item.actualQuantity - item.systemQuantity : null;
                          const hasDifference = difference !== null && difference !== 0;

                          return (
                            <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{index + 1}</td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                  <div className="text-sm font-medium text-gray-900">{item.productName}</div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.specification}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.systemQuantity}</td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <input
                                  type="number"
                                  min="0"
                                  value={item.actualQuantity || ''}
                                  onChange={(e) => handleActualQuantityChange(item.id, e.target.value)}
                                  className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all"
                                  placeholder="输入数量"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {difference !== null ? (
                                  <span className={`text-sm font-medium ${hasDifference ? 'text-red-600' : 'text-green-600'}`}>
                                    {hasDifference ? (
                                      <>
                                        <i className="fa-solid fa-exclamation-circle mr-1"></i>
                                        {difference > 0 ? `+${difference}` : difference}
                                      </>
                                    ) : (
                                      <>
                                        <i className="fa-solid fa-check-circle mr-1"></i>
                                        一致
                                      </>
                                    )}
                                  </span>
                                ) : (
                                  <span className="text-sm text-gray-400">待输入</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="w-16 h-16 border-4 border-green-200 border-t-green-700 rounded-full animate-spin mb-4"></div>
                    <p className="text-gray-500">正在加载盘点数据...</p>
                  </div>
                )}
              </div>

              {/* 底部操作栏 */}
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-4">
                <button
                  onClick={handleSaveInventory}
                  disabled={isSaving || progress < 100}
                  className={`px-6 py-3 rounded-lg transition-colors flex items-center ${progress < 100
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-700 hover:bg-green-800 text-white'
                    }`}
                >
                  {isSaving ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 保存中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-save mr-2"></i> 完成盘点并保存结果
                    </>
                  )}
                </button>

                <button
                  onClick={handleSaveInventoryToLMS}
                  // disabled={isSaving || progress < 100}

                  className={`px-6 py-3 rounded-lg transition-colors flex items-center 
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-700 hover:bg-green-800 text-white'
                    }`}
                >
                  {isSaving ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i> 上传中...
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-save mr-2"></i> 上传盘点结果至LMS
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>

          {/* 右侧实时观察窗口 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
              <div className="p-6 border-b border-gray-100">
                <h3 className="text-xl font-bold text-green-800 flex items-center">
                  <i className="fa-solid fa-eye mr-2 text-green-600"></i>实时观察窗口
                </h3>
              </div>

              {/* 图片显示区域 */}
              <div className="flex-1 p-6 flex items-center justify-center bg-gray-100 rounded-lg m-6 overflow-hidden">
                <div className="relative w-full h-full max-w-md mx-auto">
                  <img
                    src="https://lf-code-agent.coze.cn/obj/x-ai-cn/132590375682/attachment/微信图片_20250402193001_20250808014157.jpg"
                    alt="仓库实时画面"
                    className="w-full h-full object-contain rounded-lg shadow-lg border-2 border-green-700"
                  />
                  <div className="absolute bottom-4 right-4 bg-green-700 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center">
                    <i className="fa-solid fa-circle text-green-400 mr-2 animate-pulse"></i>
                    实时传输中
                  </div>
                </div>
              </div>

              {/* 观察窗口控制 */}
              <div className="p-6 border-t border-gray-100 flex justify-center space-x-4">
                <button className="p-3 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
                  <i className="fa-solid fa-search-plus text-gray-700"></i>
                </button>
                <button className="p-3 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
                  <i className="fa-solid fa-search-minus text-gray-700"></i>
                </button>
                <button className="p-3 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
                  <i className="fa-solid fa-arrows text-gray-700"></i>
                </button>
                <button className="p-3 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
                  <i className="fa-solid fa-refresh text-gray-700"></i>
                </button>
              </div>

              {/* 当前库位信息 */}
              {selectedLocation && (
                <div className="p-6 border-t border-gray-100 bg-gray-50">
                  <h4 className="text-sm font-medium text-gray-500 mb-2">当前盘点库位</h4>
                  <p className="text-lg font-bold text-green-800">{selectedLocation.locationName}</p>
                  <p className="text-sm text-gray-600 mt-1">{selectedLocation.warehouseName} - {selectedLocation.storageAreaName}</p>
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
    </div>
  );
}