import { useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/authContext";
import { motion } from "framer-motion";
import * as XLSX from "xlsx";
import { toast } from "sonner";

export default function Dashboard() {
  const [supportedWarehouseCount, setSupportedWarehouseCount] = useState(0);
  const [supportedCategoryCount, setSupportedCategoryCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const { authToken, logout } = useAuth(); // 从 useAuth 获取 logout

  // 设置当前日期
  useEffect(() => {
    const dateElement = document.getElementById("current-date");
    if (dateElement) {
      const options: Intl.DateTimeFormatOptions = {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
      };
      const currentDate = new Date().toLocaleDateString("zh-CN", options);
      dateElement.textContent = currentDate;
    }
  }, []);

  // 读取Excel文件并统计支持仓库数和支持品类数
  useEffect(() => {
    // 模拟从Excel文件中读取数据
    const readExcelData = async () => {
      setIsLoading(true);
      try {
        // 模拟仓库数据Excel文件
        const warehouseMockData = [
          ["仓库编号", "仓库名称", "描述"],
          ["101", "一号仓库", "主仓库"],
          ["102", "二号仓库", "副仓库"],
          ["103", "三号仓库", "临时仓库"],
          ["101", "一号仓库", "重复记录"], // 重复的仓库编号
          ["104", "四号仓库", "新仓库"],
          ["105", "五号仓库", "备用仓库"],
          ["106", "六号仓库", "中转仓库"],
          ["103", "三号仓库", "重复记录"], // 重复的仓库编号
        ];

        // 模拟品类数据Excel文件
        const categoryMockData = [
          ["品类ID", "品类名称", "规格"],
          ["C001", "黄鹤楼", "硬盒"],
          ["C002", "玉溪", "软盒"],
          ["C003", "荷花", "细支"],
          ["C004", "利群", "新版"],
          ["C005", "ESSE", "蓝盒"],
          ["C006", "云烟", "印象"],
          ["C007", "南京", "金陵十二钗"],
          ["C008", "红塔山", "经典"],
          ["C009", "中华", "软盒"],
          ["C010", "苏烟", "铂晶"],
          ["C011", "贵烟", "国酒香"],
          ["C012", "天子", "中支"],
          ["C013", "芙蓉王", "硬黄"],
          ["C014", "白沙", "和天下"],
          ["C015", "七匹狼", "通仙"],
          ["C016", "娇子", "宽窄"],
          ["C017", "黄金叶", "天叶"],
          ["C018", "牡丹", "软蓝"],
          ["C019", "大前门", "短支"],
          ["C020", "中南海", "5mg"],
          ["C021", "红双喜", "晶派"],
          ["C022", "娇子", "X"],
          ["C023", "兰州", "飞天"],
          ["C024", "长白山", "777"],
          ["C025", "黄山", "红方印"],
          ["C026", "钻石", "荷花"],
          ["C027", "泰山", "佛光"],
          ["C028", "好猫", "长乐"],
          ["C029", "红旗渠", "天河"],
          ["C030", "哈德门", "精品"],
        ];

        // 统计支持仓库数（第A列不同数字的数量）
        const warehouseColumnAValues = warehouseMockData
          .slice(1)
          .map((row) => row[0]);
        const uniqueWarehouseValues = new Set(warehouseColumnAValues);
        const uniqueWarehouseCount = uniqueWarehouseValues.size;

        // 统计支持品类数（除首行外的行数）
        const categoryCount = categoryMockData.length - 1; // 减去首行

        setSupportedWarehouseCount(uniqueWarehouseCount);
        setSupportedCategoryCount(categoryCount);

        toast.success(
          `成功读取Excel文件，识别到 ${uniqueWarehouseCount} 个不同的仓库编号和 ${categoryCount} 种品类`
        );
      } catch (error) {
        console.error("读取Excel文件出错:", error);
        toast.error("读取Excel文件失败，使用默认数据");
        setSupportedWarehouseCount(8); // 设置默认值
        setSupportedCategoryCount(30); // 设置默认值
      } finally {
        setIsLoading(false);
      }
    };

    // 在实际应用中，这里应该是用户选择文件后触发
    // 为了演示，我们在组件加载时自动模拟读取
    readExcelData();
  }, []);

  // 功能选项数据
  const features = [
    {
      title: "开始盘点",
      description: "启动新的仓库盘点任务",
      icon: "fa-clipboard-check",
      color: "from-green-500 to-green-600",
      path: "/inventory/start",
    },
    {
      title: "历史盘点",
      description: "查看过往盘点记录和报表",
      icon: "fa-history",
      color: "from-blue-500 to-blue-600",
      path: "/inventory/history",
    },
    {
      title: "人员权限",
      description: "管理系统用户和权限设置",
      icon: "fa-users-gear",
      color: "from-purple-500 to-purple-600",
      path: "/user_manage",
    },
  ];

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
            <h2 className="text-3xl font-bold text-green-800">
              智慧仓库盘点系统
            </h2>
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
                <p className="text-gray-500 text-sm">支持仓库数</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">
                  {isLoading ? (
                    <span className="inline-block w-12 h-8 bg-gray-200 rounded animate-pulse"></span>
                  ) : (
                    supportedWarehouseCount
                  )}
                </h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                <i className="fa-solid fa-warehouse text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 2 个
              </span>
              <span className="text-gray-500 ml-2">较去年</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">支持品类数</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">
                  {isLoading ? (
                    <span className="inline-block w-16 h-8 bg-gray-200 rounded animate-pulse"></span>
                  ) : (
                    supportedCategoryCount
                  )}
                </h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                <i className="fa-solid fa-box text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 20 种
              </span>
              <span className="text-gray-500 ml-2">较去年</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">本月盘点</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">24</h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                <i className="fa-solid fa-clipboard-check text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 8 次
              </span>
              <span className="text-gray-500 ml-2">较上月</span>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 transform transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-gray-500 text-sm">准确率</p>
                <h3 className="text-3xl font-bold text-green-800 mt-1">
                  99.7%
                </h3>
              </div>
              <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center text-amber-600">
                <i className="fa-solid fa-check-circle text-xl"></i>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-green-600 flex items-center">
                <i className="fa-solid fa-arrow-up mr-1"></i> 0.3%
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
                <div
                  className={`bg-white rounded-2xl shadow-xl overflow-hidden transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 border border-gray-100`}
                >
                  <div className={`h-2 w-full ${feature.color}`}></div>
                  <div className="p-6">
                    <div
                      className={`w-14 h-14 rounded-full bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 text-white text-2xl`}
                    >
                      <i className={`fa-solid ${feature.icon}`}></i>
                    </div>
                    <h3 className="text-xl font-bold text-gray-800 mb-2">
                      {feature.title}
                    </h3>
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
            <a
              href="#"
              className="text-green-600 hover:text-green-800 text-sm font-medium"
            >
              查看全部
            </a>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    仓库
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* 最近下发的盘点任务 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-tasks text-green-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          下发盘点任务
                        </div>
                        <div className="text-xs text-gray-500">
                          任务编号: PD20260110001
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    一号仓库A区
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2026-01-10 14:30
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                      进行中
                    </span>
                  </td>
                </tr>
                {/* 历史盘点记录自动删除 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-trash-alt text-amber-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          历史盘点记录自动删除
                        </div>
                        <div className="text-xs text-gray-500">
                          删除了2025年7月10日前的所有记录
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    系统管理
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2026-01-10 00:05
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
                {/* 人员权限变动 - 增加新用户 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-user-plus text-purple-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          增加新用户
                        </div>
                        <div className="text-xs text-gray-500">
                          用户名: zhangwei, 角色: 仓库管理员
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    系统管理
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2026-01-09 16:45
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
                {/* 人员权限变动 - 权限变更 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-key text-blue-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          用户权限变更
                        </div>
                        <div className="text-xs text-gray-500">
                          用户名: lili, 旧角色: 操作员 → 新角色: 高级操作员
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    系统管理
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2026-01-08 11:20
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      成功
                    </span>
                  </td>
                </tr>
                {/* 最近下发的盘点任务 */}
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <i className="fa-solid fa-tasks text-green-600 mr-3"></i>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          下发盘点任务
                        </div>
                        <div className="text-xs text-gray-500">
                          任务编号: PD20260108002
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    二号仓库B区
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2026-01-08 09:15
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      已完成
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
              <h3 className="text-lg font-semibold text-amber-800 mb-2">
                系统公告
              </h3>
              <ul className="text-amber-700 space-y-2">
                <li className="flex items-start">
                  <i className="fa-solid fa-circle-info mt-1 mr-2 text-sm"></i>
                  <span>如有新增仓库或品类需求，请联系运维人员进行处理。</span>
                </li>
                <li className="flex items-start">
                  <i className="fa-solid fa-circle-info mt-1 mr-2 text-sm"></i>
                  <span>历史盘点只会保留6个月内数据，历史数据将自动清理。</span>
                </li>
              </ul>
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
