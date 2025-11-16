import LoginForm from '@/components/LoginForm';
import { useEffect } from 'react';
import { useAuth } from '@/contexts/authContext'; // 导入 useAuth 而不是 AuthContext
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const { isAuthenticated } = useAuth(); // 使用 useAuth 钩子获取认证状态
  const navigate = useNavigate();

  // 如果已登录，重定向到Dashboard页面
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

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

          {/* 登录表单 */}
          <LoginForm className="w-full md:w-96" />
        </div>

        {/* 帮助链接 */}
        <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4 text-sm text-gray-600">
          <a href="#" className="hover:text-green-700 transition-colors flex items-center justify-center">
            <i className="fa-solid fa-question-circle mr-1"></i> 登录帮助
          </a>
          <span className="hidden sm:inline">|</span>
          <a href="#" className="hover:text-green-700 transition-colors flex items-center justify-center">
            <i className="fa-solid fa-lock-open mr-1"></i> 忘记密码
          </a>
          <span className="hidden sm:inline">|</span>
          <a href="#" className="hover:text-green-700 transition-colors flex items-center justify-center">
            <i className="fa-solid fa-user-tie mr-1"></i> 联系管理员
          </a>
        </div>
      </div>

      {/* 页脚 */}
      <footer className="relative py-4 text-center text-green-800 text-sm">
        <p>© 2025 智慧仓库盘点系统 - 中国烟草</p>
      </footer>
    </div>
  );
}