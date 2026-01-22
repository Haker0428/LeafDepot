import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/authContext";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { GATEWAY_URL } from "@/config/ip_address";
import { useNavigate } from "react-router-dom";

// 用户类型定义
interface User {
  userCode: string;
  userName: string;
  userLevel: "admin" | "operator";
  companyName?: string;
  deptName?: string;
  mobile?: string;
  employeeId?: string;
  authToken?: string;
}

export default function UserManage() {
  const { userLevel, userName, authToken, logout } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]); // 改为存储userCode
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    userName: "",
    userCode: "",
    password: "",
    confirmPassword: "",
    userLevel: "operator",
    mobile: "",
    deptName: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const navigate = useNavigate();

  // 处理返回按钮点击
  const handleBack = () => {
    navigate("/dashboard");
  };

  useEffect(() => {
    console.log("UserManage - Current authentication state:", {
      userLevel,

      userName,

      authToken: authToken ? authToken.substring(0, 10) + "..." : "null",
    });
  }, [userLevel, userName, authToken]);

  // 加载用户数据
  const loadUsers = async () => {
    setLoading(true);
    try {
      console.log(
        "开始加载用户数据，token长度:",
        authToken ? authToken.length : 0,
      );

      if (!authToken) {
        toast.error("认证令牌缺失，请重新登录");
        logout();
        return;
      }

      // 尝试两种方式：先作为查询参数，如果不行再尝试作为请求头
      const url = `${GATEWAY_URL}/lms/getUsers?authToken=${encodeURIComponent(
        authToken,
      )}`;
      console.log("请求URL:", url);

      const response = await fetch(url, {
        method: "GET",
        // 同时也在请求头中发送，兼容两种方式
        headers: {
          authToken: authToken,
        },
      });

      console.log("响应状态:", response.status, response.statusText);

      if (!response.ok) {
        // 尝试获取错误信息
        let errorData;
        try {
          const text = await response.text();
          console.log("错误响应文本:", text);
          errorData = JSON.parse(text);
        } catch (e) {
          console.log("无法解析错误响应为JSON");
        }

        const errorMessage =
          errorData?.message ||
          errorData?.detail ||
          `请求失败: ${response.status} ${response.statusText}`;

        if (response.status === 401) {
          toast.error("认证已过期，请重新登录");
          logout();
          return;
        } else if (response.status === 403) {
          throw new Error("权限不足，只有管理员可以查看用户列表");
        } else if (response.status === 422) {
          // 422错误，尝试另一种方式
          console.log("收到422错误");
          return;
        } else if (response.status === 503) {
          throw new Error("无法连接到LMS服务，请确保服务已启动");
        } else {
          throw new Error(errorMessage);
        }
      }

      // 解析JSON数据
      const result = await response.json();
      console.log("接口返回数据:", result);

      if (result.code === 200 && result.data) {
        console.log("成功获取用户数据:", result.data.length, "个用户");
        setUsers(result.data);
      } else {
        throw new Error(result.message || "获取用户列表失败");
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "获取用户列表失败";
      toast.error(errorMessage);
      console.error("加载用户列表失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 组件加载时获取用户数据
  useEffect(() => {
    if (userLevel === "admin" && authToken) {
      loadUsers();
    }
  }, [userLevel, authToken]);

  // 处理用户选择
  const handleSelectUser = (userCode: string) => {
    if (selectedUsers.includes(userCode)) {
      setSelectedUsers(selectedUsers.filter((code) => code !== userCode));
    } else {
      setSelectedUsers([...selectedUsers, userCode]);
    }
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedUsers.length === users.length) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(users.map((user) => user.userCode));
    }
  };

  // 打开注册模态框
  const handleOpenRegisterModal = () => {
    if (userLevel !== "admin") {
      toast.warning("只有管理员可以注册新用户");
      return;
    }
    setNewUserForm({
      userName: "",
      userCode: "",
      password: "",
      confirmPassword: "",
      userLevel: "operator",
      mobile: "",
      deptName: "",
    });
    setFormErrors({});
    setShowRegisterModal(true);
  };

  // 关闭注册模态框
  const handleCloseRegisterModal = () => {
    setShowRegisterModal(false);
  };

  // 处理表单输入变化
  const handleFormChange = (field: string, value: string) => {
    setNewUserForm({
      ...newUserForm,
      [field]: value,
    });

    // 清除该字段的错误信息
    if (formErrors[field]) {
      setFormErrors({
        ...formErrors,
        [field]: "",
      });
    }
  };

  // 验证表单
  const validateForm = () => {
    const errors: Record<string, string> = {};

    if (!newUserForm.userName.trim()) {
      errors.userName = "请输入用户名";
    }

    if (!newUserForm.userCode.trim()) {
      errors.userCode = "请输入用户代码";
    } else if (!/^[a-zA-Z0-9_]+$/.test(newUserForm.userCode)) {
      errors.userCode = "用户代码只能包含字母、数字和下划线";
    }

    if (!newUserForm.password) {
      errors.password = "请输入密码";
    } else if (newUserForm.password.length < 6) {
      errors.password = "密码长度至少6位";
    }

    if (newUserForm.password !== newUserForm.confirmPassword) {
      errors.confirmPassword = "两次输入的密码不一致";
    }

    if (newUserForm.mobile && !/^1[3-9]\d{9}$/.test(newUserForm.mobile)) {
      errors.mobile = "请输入正确的手机号码";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // 提交注册表单
  const handleRegisterSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const response = await fetch(`${GATEWAY_URL}/lms/registerUser`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          authToken: authToken || "",
        },
        body: JSON.stringify({
          userCode: newUserForm.userCode,
          password: newUserForm.password,
          userName: newUserForm.userName,
          userLevel: newUserForm.userLevel,
          mobile: newUserForm.mobile,
          deptName: newUserForm.deptName || "省物流处",
        }),
      });

      const result = await response.json();

      if (response.ok && result.code === 200) {
        toast.success(`用户 ${newUserForm.userName} 注册成功！`);
        handleCloseRegisterModal();
        // 刷新用户列表
        loadUsers();
      } else {
        throw new Error(result.message || "注册失败");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "注册失败";
      toast.error(errorMessage);
      console.error("注册用户失败:", error);
    }
  };

  // 处理删除用户
  const handleDeleteUsers = async () => {
    if (userLevel !== "admin") {
      toast.warning("只有管理员可以删除用户");
      return;
    }

    if (selectedUsers.length === 0) {
      toast.warning("请先选择要删除的用户");
      return;
    }

    // 防止删除自己
    if (selectedUsers.includes("admin")) {
      toast.error("不能删除管理员账号");
      return;
    }

    try {
      // 逐个删除选中的用户
      for (const userCode of selectedUsers) {
        const response = await fetch(`${GATEWAY_URL}/lms/deleteUser`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            authToken: authToken || "",
          },
          body: JSON.stringify({
            userCode: userCode,
          }),
        });

        const result = await response.json();

        if (!response.ok || result.code !== 200) {
          throw new Error(
            `删除用户 ${userCode} 失败: ${result.message || "未知错误"}`,
          );
        }
      }

      toast.success(`成功删除 ${selectedUsers.length} 个用户`);

      // 刷新用户列表并清空选择
      loadUsers();
      setSelectedUsers([]);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "删除用户失败";
      toast.error(errorMessage);
      console.error("删除用户失败:", error);
    }
  };

  // 获取权限标签样式
  const getLevelBadgeStyle = (level: "admin" | "operator") => {
    if (level === "admin") {
      return "bg-gradient-to-r from-purple-500 to-purple-600 text-white";
    } else {
      return "bg-gradient-to-r from-blue-500 to-blue-600 text-white";
    }
  };

  // 获取权限显示文本
  // 替换 getLevelText 函数

  const getLevelText = (level: string | null) => {
    if (!level) return "未知";

    const normalizedLevel = level.toLowerCase().trim();

    switch (normalizedLevel) {
      case "admin":
        return "管理员";

      case "operator":
        return "操作员";

      default:
        console.warn(`Unexpected user level: ${level}`);

        return "未知权限";
    }
  };

  // 权限不足时显示的内容
  if (userLevel !== "admin") {
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

        {/* 顶部导航栏 - 根据当前用户显示 */}
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
                  权限：{getLevelText(userLevel)}
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
            </div>
          </div>
        </header>

        {/* 主内容区 - 权限不足提示 */}
        <main className="flex-1 container mx-auto px-4 py-8 relative z-10 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-md p-8 text-center max-w-md">
            <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center text-red-600 mx-auto mb-6">
              <i className="fa-solid fa-ban text-3xl"></i>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">权限不足</h2>
            <p className="text-gray-600 mb-6">
              您没有权限访问用户管理页面，只有管理员可以查看用户列表。
            </p>
            <a
              href="/"
              className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-6 py-3 rounded-lg transition-all duration-300 inline-flex items-center"
            >
              <i className="fa-solid fa-arrow-left mr-2"></i>
              返回首页
            </a>
          </div>
        </main>

        {/* 页脚 */}
        <footer className="bg-white py-6 border-t border-gray-200 relative z-10">
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

      {/* 顶部导航栏 - 根据当前用户显示 */}
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
                权限：{getLevelText(userLevel)}
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
            <h2 className="text-3xl font-bold text-green-800">用户管理</h2>
            <p className="text-gray-600">管理系统用户和权限设置</p>
          </div>
          <div className="mt-4 md:mt-0 flex items-center text-gray-500">
            <i className="fa-solid fa-users mr-2"></i>
            <span>共 {users.length} 个用户</span>
            <button
              onClick={loadUsers}
              className="ml-4 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-sync-alt mr-1"></i>刷新
            </button>
          </div>
        </div>

        {/* 操作按钮区域 */}
        <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100 mb-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center">
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-2">用户管理</h3>
              <p className="text-gray-500 text-sm">
                您可以管理用户账户、设置权限和查看用户状态
              </p>
            </div>

            <div className="flex space-x-3 mt-4 md:mt-0">
              <button
                onClick={handleOpenRegisterModal}
                className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-5 py-2.5 rounded-lg transition-all duration-300 flex items-center shadow-md hover:shadow-lg"
              >
                <i className="fa-solid fa-user-plus mr-2"></i>
                注册新用户
              </button>

              <button
                onClick={handleDeleteUsers}
                disabled={selectedUsers.length === 0}
                className={`px-5 py-2.5 rounded-lg transition-all duration-300 flex items-center shadow-md hover:shadow-lg ${
                  selectedUsers.length > 0
                    ? "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
              >
                <i className="fa-solid fa-trash mr-2"></i>
                删除用户 ({selectedUsers.length})
              </button>
            </div>
          </div>
        </div>

        {/* 用户表格区域 */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
          {/* 表格标题 */}
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div className="flex justify-between items-center">
              <h4 className="text-lg font-semibold text-gray-800">用户列表</h4>
              <div className="flex items-center text-sm text-gray-500">
                <i className="fa-solid fa-circle-info mr-2"></i>
                <span>已选择 {selectedUsers.length} 个用户</span>
              </div>
            </div>
          </div>

          {loading ? (
            // 加载状态
            <div className="p-12 text-center">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-green-600 mb-4"></i>
              <p className="text-gray-600">加载用户列表...</p>
            </div>
          ) : users.length === 0 ? (
            // 无数据状态
            <div className="p-12 text-center">
              <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mx-auto mb-4">
                <i className="fa-solid fa-users-slash text-2xl"></i>
              </div>
              <h5 className="text-lg font-semibold text-gray-700 mb-2">
                暂无用户数据
              </h5>
              <p className="text-gray-500 mb-6">还没有任何用户，请先注册用户</p>
              <button
                onClick={handleOpenRegisterModal}
                className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-5 py-2.5 rounded-lg transition-all duration-300 flex items-center mx-auto"
              >
                <i className="fa-solid fa-user-plus mr-2"></i>
                注册新用户
              </button>
            </div>
          ) : (
            // 表格内容 - 美化后的表格
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-center w-12">
                      <div className="flex items-center justify-center">
                        <input
                          type="checkbox"
                          checked={
                            selectedUsers.length === users.length &&
                            users.length > 0
                          }
                          onChange={handleSelectAll}
                          className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500"
                        />
                      </div>
                    </th>
                    <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                      序号
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用户代码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用户名称
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用户权限
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      所属部门
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      手机号码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      员工ID
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user, index) => (
                    <tr
                      key={user.userCode}
                      className={`hover:bg-gray-50 transition-colors ${
                        selectedUsers.includes(user.userCode)
                          ? "bg-green-50"
                          : ""
                      }`}
                    >
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(user.userCode)}
                          onChange={() => handleSelectUser(user.userCode)}
                          className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500"
                        />
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900 text-center w-16">
                        {index + 1}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-400 to-blue-500 flex items-center justify-center text-white text-sm font-bold mr-3">
                            {user.userCode.charAt(0)}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {user.userCode}
                            </div>
                            <div className="text-xs text-gray-500">
                              ID: {user.employeeId || "N/A"}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.userName}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getLevelBadgeStyle(
                            user.userLevel,
                          )}`}
                        >
                          <i
                            className={`fa-solid ${
                              user.userLevel === "admin"
                                ? "fa-user-shield mr-1"
                                : "fa-user mr-1"
                            }`}
                          ></i>
                          {getLevelText(user.userLevel)}
                        </span>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                        <div className="flex items-center">
                          <i className="fa-solid fa-building mr-2 text-gray-400"></i>
                          {user.deptName || "未分配"}
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                        <div className="flex items-center">
                          <i className="fa-solid fa-phone mr-2 text-gray-400"></i>
                          {user.mobile || "未设置"}
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                        <div className="flex items-center">
                          <i className="fa-solid fa-id-badge mr-2 text-gray-400"></i>
                          {user.employeeId || "N/A"}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 底部信息 */}
        <div className="mt-6 text-sm text-gray-500">
          <div className="flex items-center">
            <i className="fa-solid fa-circle-info mr-2 text-green-600"></i>
            <span>提示：只有管理员可以注册和删除用户</span>
          </div>
        </div>
      </main>

      {/* 注册用户模态框 */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-gray-200"
          >
            {/* 模态框头部 */}
            <div className="bg-gradient-to-r from-green-500 to-green-600 p-6 text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-xl font-bold">注册新用户</h3>
                  <p className="text-green-100 text-sm mt-1">
                    添加新的系统用户
                  </p>
                </div>
                <button
                  onClick={handleCloseRegisterModal}
                  className="w-8 h-8 rounded-full bg-white bg-opacity-20 hover:bg-opacity-30 flex items-center justify-center transition-all"
                >
                  <i className="fa-solid fa-times"></i>
                </button>
              </div>
            </div>

            {/* 模态框内容 */}
            <div className="p-6">
              <div className="space-y-4">
                {/* 用户名称 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    用户名称 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                      <i className="fa-solid fa-user"></i>
                    </span>
                    <input
                      type="text"
                      value={newUserForm.userName}
                      onChange={(e) =>
                        handleFormChange("userName", e.target.value)
                      }
                      className={`w-full pl-10 pr-4 py-2.5 rounded-lg border ${
                        formErrors.userName
                          ? "border-red-300 focus:ring-red-500 focus:border-red-500"
                          : "border-gray-300 focus:ring-green-500 focus:border-green-500"
                      } transition-all`}
                      placeholder="请输入用户姓名"
                    />
                  </div>
                  {formErrors.userName && (
                    <p className="mt-1 text-xs text-red-600">
                      {formErrors.userName}
                    </p>
                  )}
                </div>

                {/* 用户代码 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    用户代码 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                      <i className="fa-solid fa-id-card"></i>
                    </span>
                    <input
                      type="text"
                      value={newUserForm.userCode}
                      onChange={(e) =>
                        handleFormChange("userCode", e.target.value)
                      }
                      className={`w-full pl-10 pr-4 py-2.5 rounded-lg border ${
                        formErrors.userCode
                          ? "border-red-300 focus:ring-red-500 focus:border-red-500"
                          : "border-gray-300 focus:ring-green-500 focus:border-green-500"
                      } transition-all`}
                      placeholder="请输入登录用户名（字母、数字、下划线）"
                    />
                  </div>
                  {formErrors.userCode && (
                    <p className="mt-1 text-xs text-red-600">
                      {formErrors.userCode}
                    </p>
                  )}
                </div>

                {/* 用户权限 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    用户权限 <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => handleFormChange("userLevel", "operator")}
                      className={`py-3 rounded-lg border-2 flex flex-col items-center justify-center transition-all ${
                        newUserForm.userLevel === "operator"
                          ? "border-green-500 bg-white text-green-700"
                          : "border-gray-200 hover:border-gray-300 text-gray-700 bg-white"
                      }`}
                    >
                      <i className="fa-solid fa-user text-xl mb-1"></i>
                      <span className="font-medium">操作员</span>
                      <span className="text-xs text-gray-500 mt-1">
                        基础功能权限
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleFormChange("userLevel", "admin")}
                      className={`py-3 rounded-lg border-2 flex flex-col items-center justify-center transition-all ${
                        newUserForm.userLevel === "admin"
                          ? "border-purple-500 bg-white text-purple-700"
                          : "border-gray-200 hover:border-gray-300 text-gray-700 bg-white"
                      }`}
                    >
                      <i className="fa-solid fa-user-shield text-xl mb-1"></i>
                      <span className="font-medium">管理员</span>
                      <span className="text-xs text-gray-500 mt-1">
                        全部系统权限
                      </span>
                    </button>
                  </div>
                </div>

                {/* 手机号码 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    手机号码
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                      <i className="fa-solid fa-phone"></i>
                    </span>
                    <input
                      type="tel"
                      value={newUserForm.mobile}
                      onChange={(e) =>
                        handleFormChange("mobile", e.target.value)
                      }
                      className={`w-full pl-10 pr-4 py-2.5 rounded-lg border ${
                        formErrors.mobile
                          ? "border-red-300 focus:ring-red-500 focus:border-red-500"
                          : "border-gray-300 focus:ring-green-500 focus:border-green-500"
                      } transition-all`}
                      placeholder="请输入手机号码（可选）"
                      autoComplete="off" // 添加这个属性
                    />
                  </div>
                  {formErrors.mobile && (
                    <p className="mt-1 text-xs text-red-600">
                      {formErrors.mobile}
                    </p>
                  )}
                </div>

                {/* 密码 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    密码 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                      <i className="fa-solid fa-lock"></i>
                    </span>
                    <input
                      type="password"
                      value={newUserForm.password}
                      onChange={(e) =>
                        handleFormChange("password", e.target.value)
                      }
                      className={`w-full pl-10 pr-4 py-2.5 rounded-lg border ${
                        formErrors.password
                          ? "border-red-300 focus:ring-red-500 focus:border-red-500"
                          : "border-gray-300 focus:ring-green-500 focus:border-green-500"
                      } transition-all`}
                      placeholder="至少6位字符"
                      autoComplete="new-password" // 添加这个属性 修复BUG
                    />
                  </div>
                  {formErrors.password && (
                    <p className="mt-1 text-xs text-red-600">
                      {formErrors.password}
                    </p>
                  )}
                </div>

                {/* 确认密码 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    确认密码 <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                      <i className="fa-solid fa-lock"></i>
                    </span>
                    <input
                      type="password"
                      value={newUserForm.confirmPassword}
                      onChange={(e) =>
                        handleFormChange("confirmPassword", e.target.value)
                      }
                      className={`w-full pl-10 pr-4 py-2.5 rounded-lg border ${
                        formErrors.confirmPassword
                          ? "border-red-300 focus:ring-red-500 focus:border-red-500"
                          : "border-gray-300 focus:ring-green-500 focus:border-green-500"
                      } transition-all`}
                      placeholder="再次输入密码"
                    />
                  </div>
                  {formErrors.confirmPassword && (
                    <p className="mt-1 text-xs text-red-600">
                      {formErrors.confirmPassword}
                    </p>
                  )}
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex space-x-3 mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={handleCloseRegisterModal}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-3 px-4 rounded-lg transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleRegisterSubmit}
                  className="flex-1 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-medium py-3 px-4 rounded-lg transition-all flex items-center justify-center"
                >
                  <i className="fa-solid fa-user-plus mr-2"></i>
                  注册用户
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

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
