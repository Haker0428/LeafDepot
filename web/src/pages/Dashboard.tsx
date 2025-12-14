import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/authContext'; // 统一导入 useAuth
import { motion } from 'framer-motion';
import { toast } from 'sonner'; // 添加 toast 导入
import { GATEWAY_URL } from '@/config/ip_address'; // 导入常量

export default function Dashboard() {
  // 统一使用 useAuth 钩子
  const { authToken, logout } = useAuth(); // 从 useAuth 获取 logout
  // const [bins, setBins] = useState<any[]>([]);
  // const [tasks, setTasks] = useState<any[]>([]);
  // const [loading, setLoading] = useState(false);

  const navigate = useNavigate(); // 添加 navigate

  // 获取库位信息
  // const fetchBins = async () => {
  //   if (!authToken) return;

  //   setLoading(true);
  //   try {
  //     const response = await fetch(`${GATEWAY_URL}/lms/getLmsBin?authToken=${authToken}`);
  //     if (response.ok) {
  //       const data = await response.json();
  //       setBins(data);
  //       console.log('获取库位信息成功:', data);
  //     }
  //   } catch (error) {
  //     console.error('Failed to fetch bins:', error);
  //     toast.error('获取库位信息失败');
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  // 获取盘点任务
  // const fetchTasks = async () => {
  //   if (!authToken) return;

  //   setLoading(true); const { authToken, logout } = useAuth(); // 从 useAuth 获取 logout

  //   try {
  //     const response = await fetch(`${GATEWAY_URL}/lms/getCountTasks?authToken=${authToken}`);
  //     if (response.ok) {
  //       const data = await response.json();
  //       setTasks(data);
  //       console.log('获取盘点任务成功:', data);
  //     }
  //   } catch (error) {
  //     console.error('Failed to fetch tasks:', error);
  //     toast.error('获取盘点任务失败');
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  // 开始盘点按钮点击处理
  // const handleStartInventory = () => {
  //   // 获取库位信息
  //   // fetchBins();
  //   // 获取盘点任务
  //   // fetchTasks();

  //   // 跳转到盘点页面
  //   navigate('/inventory/start');
  // };

  // 设置当前日期
  useEffect(() => {
    const dateElement = document.getElementById('current-date');
    if (dateElement) {
      const options: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
      };
      const currentDate = new Date().toLocaleDateString('zh-CN', options);
      dateElement.textContent = currentDate;
    }
  }, []);

  // 功能选项数据
  const features = [
    {
      title: "开始盘点",
      description: "启动新的仓库盘点任务",
      icon: "fa-clipboard-check",
      color: "from-green-500 to-green-600",
      path: "/inventory/start"
    },
    {
      title: "历史盘点",
      description: "查看过往盘点记录和报表",
      icon: "fa-history",
      color: "from-blue-500 to-blue-600",
      path: "/inventory/history"
    },
    {
      title: "人员权限",
      description: "管理系统用户和权限设置",
      icon: "fa-users-gear",
      color: "from-purple-500 to-purple-600",
      path: "/personnel/permissions"
    }
  ];

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
            onClick={logout}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-all flex items-center"
          >
            <i className="fa-solid fa-sign-out-alt mr-2"></i>退出登录
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        {/* 用户欢迎与日期 */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold text-green-800">智慧仓库盘点系统</h2>
            <p className="text-gray-600">欢迎使用中国烟草仓库管理解决方案</p>
          </div>
          <div className="mt-4 md:mt-0 flex items-center text-gray-500">
            <i className="fa-solid fa-calendar mr-2"></i>
            <span id="current-date">2025年8月8日</span>
          </div>
        </div>

        {/* 统计数据卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">总仓库数</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">12</h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                <i className="fa-solid fa-warehouse text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 2 个
              </span>
              <span className="text-gray-500 ml-2">较上月</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">在库商品</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">1,286</h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                <i className="fa-solid fa-box text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 12%
              </span>
              <span className="text-gray-500 ml-2">较上月</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">本日盘点</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">6</h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                <i className="fa-solid fa-clipboard-check text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 1 次
              </span>
              <span className="text-gray-500 ml-2">较昨日</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">本月盘点</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">99.7%</h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center text-amber-600">
                <i className="fa-solid fa-check-circle text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 8次
              </span>
              <span className="text-gray-500 ml-2">较上月</span>
            </div>
          </div>
        </div>

        {/* 功能选择区域标题 */}
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-green-800 mb-2">功能导航</h2>
          <p className="text-gray-600">请选择以下功能进行操作</p>
        </div>

        {/* 功能选项卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Link to={feature.path}>
                <div className={`bg-white rounded-2xl shadow-xl overflow-hidden transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 border border-gray-100`}>
                  <div className={`h-2 w-full ${feature.color}`}></div>
                  <div className="p-6">
                    <div className={`w-14 h-14 rounded-full bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 text-white text-2xl`}>
                      <i className={`fa-solid ${feature.icon}`}></i>
                    </div>
                    <h3 className="text-xl font-bold text-gray-800 mb-2">{feature.title}</h3>
                    <p className="text-gray-500 mb-4">{feature.description}</p>
                    <div className="inline-flex items-center text-green-600 font-medium">
                      <span>查看详情</span>
                      <i className="fa-solid fa-arrow-right ml-2 text-sm"></i>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
        {/* 最近操作记录 */}
        <div className="mt-12 bg-white rounded-xl shadow-md p-6 border border-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-800">最近操作记录</h3>
            <a href="#" className="text-green-600 hover:text-green-800 text-sm font-medium">查看全部</a>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">仓库</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-clipboard-check text-green-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">完成盘点任务</div>
                        <div className="text-xs text-gray-500">任务编号: PD20250807001</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">一号仓库A区</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">2025-08-07 14:30</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-file-export text-blue-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">导出盘点报表</div>
                        <div className="text-xs text-gray-500">报表编号: RPT20250806002</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">二号仓库B区</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">2025-08-06 09:15</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-user-plus text-purple-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">添加操作员</div>
                        <div className="text-xs text-gray-500">用户ID: OP20250805003</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">系统管理</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">2025-08-05 16:45</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 系统公告 */}
        <div className="mt-8 bg-amber-50 rounded-xl p-6 border border-amber-100">
          <div className="flex items-start">
            <i className="fa-solid fa-bullhorn text-amber-500 mt-1 mr-4 text-xl"></i>
            <div>
              <h3 className="text-lg font-semibold text-amber-800 mb-2">系统公告</h3>
              <p className="text-amber-700">
                将于2025年8月15日00:00-02:00进行系统维护，请提前安排好工作，避免影响正常业务。
              </p>
            </div>
          </div>
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