import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { GATEWAY_URL } from '@/config/ip_address'; // 导入常量
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

export default function InventoryStart() {
  // 统一使用 useAuth 钩子
  const { authToken } = useAuth();
  const [bins, setBins] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false); // 为盘点任务添加单独的加载状态

  const navigate = useNavigate();

  // 状态管理
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('ALL');
  const [selectedStorageArea, setSelectedStorageArea] = useState<string>('ALL');
  const [selectedLocation, setSelectedLocation] = useState<string>('ALL');
  const [inventoryData, setInventoryData] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [storageAreas, setStorageAreas] = useState<StorageArea[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);

  // 模拟数据 - 仓库列表
  useEffect(() => {
    const mockWarehouses: Warehouse[] = [
      { id: 'WH001', name: '一号仓库' },
      { id: 'WH002', name: '二号仓库' },
      { id: 'WH003', name: '三号仓库' },
      { id: 'WH004', name: '四号仓库' },
    ];
    setWarehouses(mockWarehouses);

    // 模拟数据 - 库区列表
    const mockStorageAreas: StorageArea[] = [
      { id: 'SA001', name: 'A区', warehouseId: 'WH001' },
      { id: 'SA002', name: 'B区', warehouseId: 'WH001' },
      { id: 'SA003', name: 'C区', warehouseId: 'WH002' },
      { id: 'SA004', name: 'D区', warehouseId: 'WH002' },
      { id: 'SA005', name: 'E区', warehouseId: 'WH003' },
      { id: 'SA006', name: 'F区', warehouseId: 'WH004' },
    ];
    setStorageAreas(mockStorageAreas);

    // 模拟数据 - 库位列表
    const mockLocations: Location[] = [
      { id: 'LOC001', name: 'A01', storageAreaId: 'SA001' },
      { id: 'LOC002', name: 'A02', storageAreaId: 'SA001' },
      { id: 'LOC003', name: 'B01', storageAreaId: 'SA002' },
      { id: 'LOC004', name: 'B02', storageAreaId: 'SA002' },
      { id: 'LOC005', name: 'C01', storageAreaId: 'SA003' },
      { id: 'LOC006', name: 'C02', storageAreaId: 'SA003' },
      { id: 'LOC007', name: 'D01', storageAreaId: 'SA004' },
      { id: 'LOC008', name: 'D02', storageAreaId: 'SA004' },
      { id: 'LOC009', name: 'E01', storageAreaId: 'SA005' },
      { id: 'LOC010', name: 'E02', storageAreaId: 'SA005' },
      { id: 'LOC011', name: 'F01', storageAreaId: 'SA006' },
      { id: 'LOC012', name: 'F02', storageAreaId: 'SA006' },
    ];
    setLocations(mockLocations);
  }, []);

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
      toast.success('获取盘点任务成功');

      // 将获取的任务数据保存到状态中
      setTasks(data.data || data); // 根据实际返回数据结构调整

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
  }

  // 模拟获取库存数据
  const fetchInventoryData = async () => {
    setIsLoading(true);

    // 模拟API请求延迟
    setTimeout(() => {
      // 根据选择的仓库、库区、库位生成模拟库存数据
      const cigaretteBrands = [
        '黄鹤楼(硬)', '黄鹤楼(软)', '黄鹤楼(1916)',
        '玉溪(软)', '玉溪(硬)', '玉溪(和谐)',
        '荷花(硬)', '荷花(细支)',
        '利群(新版)', '利群(软蓝)', '利群(阳光)'
      ];

      const mockInventory: InventoryItem[] = [];

      // 随机生成3-8条库存记录
      const itemCount = Math.floor(Math.random() * 6) + 3;

      for (let i = 0; i < itemCount; i++) {
        // 随机选择一个烟品牌
        const randomBrand = cigaretteBrands[Math.floor(Math.random() * cigaretteBrands.length)];

        mockInventory.push({
          id: `INV${Date.now()}${i}`,
          productName: randomBrand.split('(')[0],
          specification: randomBrand.split('(')[1]?.replace(')', '') || '常规',
          quantity: Math.floor(Math.random() * 100) + 10, // 10-109箱
          unit: '箱',
          locationId: selectedLocation === 'ALL'
            ? locations[Math.floor(Math.random() * locations.length)].id
            : selectedLocation
        });
      }

      setInventoryData(mockInventory);
      setIsLoading(false);

      if (mockInventory.length === 0) {
        toast.info('未查询到库存数据');
      } else {
        toast.success(`成功查询到 ${mockInventory.length} 条库存数据`);
      }
    }, 800);

    // ###############################################################
    if (!authToken) {
      toast.error('未找到认证令牌，请重新登录');
      return;
    }
    console.log('使用的 authToken:', authToken);
    console.log('请求URL:', `${GATEWAY_URL}/lms/getLmsBin?authToken=${authToken}`);

    setTaskLoading(true);
    try {
      const response = await fetch(`${GATEWAY_URL}/lms/getLmsBin?authToken=${authToken}`, {
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

      // 处理逻辑

      console.log('获取库位信息成功:', data);
      toast.success('获取库位信息成功');

      // 将获取的任务数据保存到状态中
      setTasks(data.data || data); // 根据实际返回数据结构调整

      return data;

    } catch (error) {
      console.error('获取库位信息失败:', error);

      // 根据错误类型显示不同的提示信息
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        toast.error('网络连接失败，请检查网络设置和后端服务状态');
      } else if (error instanceof Error) {
        // 显示具体的错误信息
        toast.error(`获取库位信息失败: ${error.message}`);
      } else {
        toast.error('获取库位信息失败');
      }

      throw error;
    } finally {
      setTaskLoading(false);
    }
  };

  // 处理返回按钮点击
  const handleBack = () => {
    navigate('/dashboard');
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
          <p className="text-gray-600 mt-1">请选择仓库信息并获取当前库位库存数据</p>
        </div>

        {/* 选择区域和数据展示区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧选择区域 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-1"
          >
            <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 h-full">
              <h3 className="text-xl font-bold text-green-800 mb-6 pb-3 border-b border-gray-100">
                <i className="fa-solid fa-filter mr-2 text-green-600"></i>库位选择
              </h3>

              <div className="space-y-6">
                {/* 仓库选择 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    仓库号 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <select
                      value={selectedWarehouse}
                      onChange={(e) => setSelectedWarehouse(e.target.value)}
                      className="w-full pl-4 pr-10 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all appearance-none bg-white"
                    >
                      <option value="ALL">ALL - 所有仓库</option>
                      {warehouses.map(warehouse => (
                        <option key={warehouse.id} value={warehouse.id}>
                          {warehouse.id} - {warehouse.name}
                        </option>
                      ))}
                    </select>
                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-gray-500">
                      <i className="fa-solid fa-chevron-down"></i>
                    </div>
                  </div>
                </div>

                {/* 库区选择 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    库区号 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <select
                      value={selectedStorageArea}
                      onChange={(e) => setSelectedStorageArea(e.target.value)}
                      className="w-full pl-4 pr-10 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all appearance-none bg-white"
                      disabled={selectedWarehouse === 'ALL'}
                    >
                      <option value="ALL">ALL - 所有库区</option>
                      {storageAreas
                        .filter(area => selectedWarehouse === 'ALL' || area.warehouseId === selectedWarehouse)
                        .map(area => (
                          <option key={area.id} value={area.id}>
                            {area.id} - {area.name}
                          </option>
                        ))}
                    </select>
                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-gray-500">
                      <i className="fa-solid fa-chevron-down"></i>
                    </div>
                  </div>
                </div>

                {/* 库位选择 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    库位号 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <select
                      value={selectedLocation}
                      onChange={(e) => setSelectedLocation(e.target.value)}
                      className="w-full pl-4 pr-10 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all appearance-none bg-white"
                      disabled={selectedStorageArea === 'ALL' && selectedWarehouse !== 'ALL'}
                    >
                      <option value="ALL">ALL - 所有库位</option>
                      {locations
                        .filter(loc => {
                          if (selectedStorageArea === 'ALL') {
                            return selectedWarehouse === 'ALL' ||
                              storageAreas.find(area => area.id === loc.storageAreaId)?.warehouseId === selectedWarehouse;
                          }
                          return loc.storageAreaId === selectedStorageArea;
                        })
                        .map(location => (
                          <option key={location.id} value={location.id}>
                            {location.id} - {location.name}
                          </option>
                        ))}
                    </select>
                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-gray-500">
                      <i className="fa-solid fa-chevron-down"></i>
                    </div>
                  </div>
                </div>

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
                  onClick={fetchCountingTask} // 直接调用，不需要参数
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
                {isLoading ? (
                  // 加载状态
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="w-16 h-16 border-4 border-green-200 border-t-green-700 rounded-full animate-spin mb-4"></div>
                    <p className="text-gray-500">正在获取库存数据...</p>
                  </div>
                ) : inventoryData.length > 0 ? (
                  // 数据表格
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序号</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">品规</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">规格</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">库存数量</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
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
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <button className="text-green-600 hover:text-green-900 mr-4">
                                <i className="fa-solid fa-edit mr-1"></i>盘点
                              </button>
                            </td>
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
                    <h4 className="text-lg font-medium text-gray-900 mb-2">暂无库存数据</h4>
                    <p className="text-gray-500 max-w-md">
                      请在左侧选择仓库、库区和库位信息，然后点击"获取当前库位信息"按钮查询库存数据
                    </p>
                  </div>
                )}
              </div>

              {/* 底部操作栏 */}
              {inventoryData.length > 0 && (
                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
                  <div className="text-sm text-gray-500">
                    共 <span className="font-medium text-green-700">{inventoryData.length}</span> 条记录
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
                        // 获取选中的仓库、库区、库位信息
                        const warehouseInfo = warehouses.find(w => w.id === selectedWarehouse) || { id: selectedWarehouse, name: '所有仓库' };
                        const storageAreaInfo = storageAreas.find(a => a.id === selectedStorageArea) || { id: selectedStorageArea, name: '所有库区' };
                        const locationInfo = locations.find(l => l.id === selectedLocation) || { id: selectedLocation, name: '所有库位' };

                        // 跳转到盘点进度页面并传递参数
                        navigate('/inventory/progress', {
                          state: {
                            selectedLocation: {
                              warehouseId: warehouseInfo.id,
                              warehouseName: warehouseInfo.name,
                              storageAreaId: storageAreaInfo.id,
                              storageAreaName: storageAreaInfo.name,
                              locationId: locationInfo.id,
                              locationName: locationInfo.name
                            }
                          }
                        });
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