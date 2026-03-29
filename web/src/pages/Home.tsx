import LoginForm from '../components/LoginForm';
import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/authContext'; // 导入 useAuth 而不是 AuthContext
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const { isAuthenticated } = useAuth(); // 使用 useAuth 钩子获取认证状态
  const navigate = useNavigate();
  const [showHelp, setShowHelp] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  // 如果已登录，重定向到Dashboard页面
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // 管理员联系方式
  const adminContact = {
    adminName: "张运维",
    adminPhone: "13800138000"
  };

  // 如果已登录，显示加载中状态
  if (isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <i className="fa-solid fa-spinner fa-spin text-green-600 text-4xl mb-4"></i>
          <p className="text-xl text-gray-600">正在跳转到系统主页...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* 背景图片 */}
      <div className="absolute inset-0 bg-cover bg-center opacity-10"
        style={{
          backgroundImage: 'url(https://lf-code-agent.coze.cn/obj/x-ai-cn/attachment/3868529628819536/背景参考_20250808011802.jfif)'
        }}>
      </div>

      {/* 主内容 */}
      <div className="relative flex-1 flex flex-col items-center justify-center p-4">
        {/* 系统介绍区域 */}
        <div className="max-w-2xl mb-12 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-green-800 mb-4">智慧仓库盘点系统</h1>
          <p className="text-gray-600 text-lg mb-6">
            中国烟草专用仓库管理解决方案，提供高效、精准的库存盘点与管理功能
          </p>
          <div className="flex justify-center space-x-6 mb-8">
            <div className="flex items-center">
              <i className="fa-solid fa-check-circle text-green-600 text-xl mr-2"></i>
              <span className="text-gray-700">高效盘点流程</span>
            </div>
            <div className="flex items-center">
              <i className="fa-solid fa-check-circle text-green-600 text-xl mr-2"></i>
              <span className="text-gray-700">精准数据记录</span>
            </div>
            <div className="flex items-center">
              <i className="fa-solid fa-check-circle text-green-600 text-xl mr-2"></i>
              <span className="text-gray-700">安全权限管理</span>
            </div>
          </div>
        </div>

        {/* 登录表单与品牌元素容器 */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-10 w-full max-w-5xl">
          {/* 品牌装饰元素 */}
          <div className="hidden md:flex flex-col items-center">
            <div className="w-32 h-32 bg-green-700 rounded-full flex items-center justify-center mb-4">
              <i className="fa-solid fa-boxes-stacked text-white text-4xl"></i>
            </div>
            <div className="text-center">
              <div className="text-green-800 font-bold text-xl">中国烟草</div>
              <div className="text-gray-500 text-sm">智慧物流体系</div>
            </div>
          </div>

          {/* 登录表单容器 */}
          <div className="w-full md:w-96 flex flex-col items-center">
            <LoginForm className="w-full" />

            {/* 帮助链接 */}
            <div className="mt-6 flex flex-col sm:flex-row justify-center gap-4 text-sm text-gray-600 w-full">
              <button
                type="button"
                onClick={() => setShowHelp(true)}
                className="hover:text-green-700 transition-colors flex items-center justify-center"
              >
                <i className="fa-solid fa-question-circle mr-1"></i> 登录帮助
              </button>
              <span className="hidden sm:inline">|</span>
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="hover:text-green-700 transition-colors flex items-center justify-center"
              >
                <i className="fa-solid fa-lock-open mr-1"></i> 忘记密码
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 登录帮助模态窗口 */}
      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* 背景遮罩 */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowHelp(false)}
          ></div>

          {/* 模态窗口内容 */}
          <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 transform transition-all">
            {/* 关闭按钮 */}
            <button
              onClick={() => setShowHelp(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <i className="fas fa-times text-xl"></i>
            </button>

            {/* 标题 */}
            <div className="flex items-center mb-6">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mr-4">
                <i className="fas fa-info-circle text-green-700 text-xl"></i>
              </div>
              <h3 className="text-xl font-bold text-gray-800">登录权限说明</h3>
            </div>

            {/* 权限说明内容 */}
            <div className="space-y-4">
              {/* 操作员权限 */}
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                <div className="flex items-start">
                  <div className="w-8 h-8 bg-blue-200 rounded-full flex items-center justify-center mr-3 flex-shrink-0 mt-1">
                    <i className="fas fa-user text-blue-700 text-sm"></i>
                  </div>
                  <div>
                    <h4 className="font-semibold text-blue-800 mb-2">操作员身份</h4>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li className="flex items-start">
                        <i className="fas fa-check text-blue-500 mr-2 mt-1"></i>
                        <span>使用盘点功能</span>
                      </li>
                      <li className="flex items-start">
                        <i className="fas fa-check text-blue-500 mr-2 mt-1"></i>
                        <span>查看历史记录</span>
                      </li>
                      <li className="flex items-start">
                        <i className="fas fa-times text-red-400 mr-2 mt-1"></i>
                        <span>无权管理用户</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* 管理员权限 */}
              <div className="bg-green-50 rounded-lg p-4 border border-green-100">
                <div className="flex items-start">
                  <div className="w-8 h-8 bg-green-200 rounded-full flex items-center justify-center mr-3 flex-shrink-0 mt-1">
                    <i className="fas fa-user-shield text-green-700 text-sm"></i>
                  </div>
                  <div>
                    <h4 className="font-semibold text-green-800 mb-2">管理员身份</h4>
                    <ul className="text-sm text-green-700 space-y-1">
                      <li className="flex items-start">
                        <i className="fas fa-check text-green-500 mr-2 mt-1"></i>
                        <span>所有操作员权限</span>
                      </li>
                      <li className="flex items-start">
                        <i className="fas fa-check text-green-500 mr-2 mt-1"></i>
                        <span>新增人员</span>
                      </li>
                      <li className="flex items-start">
                        <i className="fas fa-check text-green-500 mr-2 mt-1"></i>
                        <span>删除人员</span>
                      </li>
                      <li className="flex items-start">
                        <i className="fas fa-check text-green-500 mr-2 mt-1"></i>
                        <span>修改人员权限</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* 提示信息 */}
              <div className="bg-amber-50 rounded-lg p-4 border border-amber-100">
                <div className="flex items-start">
                  <i className="fas fa-lightbulb text-amber-600 mr-3 mt-1"></i>
                  <div className="text-sm text-amber-800">
                    <p className="font-semibold mb-1">温馨提示</p>
                    <p>如需新增或管理人员，请以管理员身份登录后访问"人员权限"功能。</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 关闭按钮 */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowHelp(false)}
                className="bg-green-700 hover:bg-green-800 text-white font-medium py-2 px-6 rounded-lg transition-colors"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 忘记密码模态窗口 */}
      {showForgotPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* 背景遮罩 */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowForgotPassword(false)}
          ></div>

          {/* 模态窗口内容 */}
          <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 transform transition-all">
            {/* 关闭按钮 */}
            <button
              onClick={() => setShowForgotPassword(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <i className="fas fa-times text-xl"></i>
            </button>

            {/* 标题 */}
            <div className="flex items-center mb-6">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4">
                <i className="fas fa-key text-blue-700 text-xl"></i>
              </div>
              <h3 className="text-xl font-bold text-gray-800">忘记密码</h3>
            </div>

            {/* 内容 */}
            <div className="space-y-4">
              <p className="text-gray-600 mb-4">
                如需重置密码，请联系管理员协助处理。
              </p>

              {/* 管理员信息卡片 */}
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="flex items-center mb-3">
                  <i className="fas fa-user-shield text-green-700 text-2xl mr-3"></i>
                  <div>
                    <h4 className="font-semibold text-gray-800">管理员</h4>
                  </div>
                </div>
                <div className="space-y-2 text-gray-700">
                  <div className="flex items-center">
                    <i className="fas fa-user text-gray-500 w-6 mr-2"></i>
                    <span className="text-sm">李管理</span>
                  </div>
                  <div className="flex items-center">
                    <i className="fas fa-phone text-gray-500 w-6 mr-2"></i>
                    <span className="text-sm">13900139000</span>
                  </div>
                  <div className="flex items-center">
                    <i className="fas fa-envelope text-gray-500 w-6 mr-2"></i>
                    <span className="text-sm">admin@example.com</span>
                  </div>
                </div>
              </div>

              {/* 运维人员信息 - 小字说明 */}
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 mt-4">
                <div className="text-xs text-gray-500">
                  <div className="font-semibold mb-2 text-gray-600">运维支持</div>
                  <div className="space-y-1">
                    <div className="flex items-center">
                      <i className="fas fa-user-cog text-gray-400 w-5 mr-2"></i>
                      <span>运维人员：{adminContact.adminName}</span>
                    </div>
                    <div className="flex items-center">
                      <i className="fas fa-phone-alt text-gray-400 w-5 mr-2"></i>
                      <span>联系电话：{adminContact.adminPhone}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 温馨提示 */}
              <div className="bg-amber-50 rounded-lg p-4 border border-amber-100">
                <div className="flex items-start">
                  <i className="fas fa-info-circle text-amber-600 mr-3 mt-1"></i>
                  <div className="text-sm text-amber-800">
                    <p className="font-semibold mb-1">温馨提示</p>
                    <p>为保障系统安全，密码重置需管理员验证身份后处理。</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 关闭按钮 */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowForgotPassword(false)}
                className="bg-green-700 hover:bg-green-800 text-white font-medium py-2 px-6 rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 页脚 */}
      <footer className="relative py-4 text-center text-green-800 text-sm">
        <p>© 2025 智慧仓库盘点系统 - 中国烟草</p>
      </footer>
    </div>
  );
}