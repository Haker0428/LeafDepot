import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { gatewayUrl } from '../config/ip_address';

interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (isAuthenticated: boolean) => void;
  user: any;
  setUser: (user: any) => void;
  authToken: string | null;
  setAuthToken: (authToken: string | null) => void;
  userLevel: string | null; // 新增：用户权限
  setUserLevel: (userLevel: string | null) => void; // 新增：设置用户权限
  userName: string | null; // 新增：用户名
  setUserName: (userName: string | null) => void; // 新增：设置用户名
  userId: string | null; // 新增：用户ID
  setUserId: (userId: string | null) => void; // 新增：设置用户ID
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [authToken, setAuthTokenState] = useState<string | null>(null);
  const [userLevel, setUserLevelState] = useState<string | null>(null); // 新增：用户权限状态
  const [userName, setUserNameState] = useState<string | null>(null); // 新增：用户名状态
  const [userId, setUserIdState] = useState<string | null>(null); // 新增：用户ID状态

  // 统一的设置 token 函数，确保状态和 sessionStorage 同步
  // 使用 sessionStorage 替代 localStorage，关闭浏览器后需要重新登录
  const setAuthToken = useCallback((token: string | null) => {
    setAuthTokenState(token);
    if (token) {
      sessionStorage.setItem('authToken', token);
    } else {
      sessionStorage.removeItem('authToken');
    }
  }, []);

  // 统一的设置用户权限函数
  const setUserLevel = useCallback((level: string | null) => {
    setUserLevelState(level);
    if (level) {
      sessionStorage.setItem('userLevel', level);
    } else {
      sessionStorage.removeItem('userLevel');
    }
  }, []);

  // 统一的设置用户名函数
  const setUserName = useCallback((name: string | null) => {
    setUserNameState(name);
    if (name) {
      sessionStorage.setItem('userName', name);
    } else {
      sessionStorage.removeItem('userName');
    }
  }, []);

  // 统一的设置用户ID函数
  const setUserId = useCallback((id: string | null) => {
    setUserIdState(id);
    if (id) {
      sessionStorage.setItem('userId', id);
    } else {
      sessionStorage.removeItem('userId');
    }
  }, []);

  const logout = useCallback(() => {
    setIsAuthenticated(false);
    setUser(null);
    setAuthToken(null);
    setUserLevel(null); // 清除用户权限
    setUserName(null); // 清除用户名
    setUserId(null); // 清除用户ID
    toast.success('已退出登录');
  }, [setAuthToken, setUserLevel, setUserName, setUserId]);

  const verifyToken = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${gatewayUrl()}/auth/token?token=${token}`);
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);

        // 从用户数据中提取用户权限、用户名和用户ID
        const userLevelFromData = userData.userLevel || 'operator'; // 默认为操作员
        const userNameFromData = userData.userName || '';
        const userIdFromData = userData.userId || '';

        setUserLevel(userLevelFromData);
        setUserName(userNameFromData);
        setUserId(userIdFromData);

        return true; // 验证成功
      } else {
        throw new Error('Token verification failed');
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      // Token 验证失败时，只清除认证状态，但保留 token 以便重试
      setIsAuthenticated(false);
      setUser(null);
      setUserLevel(null);
      setUserName(null);
      setUserId(null);
      toast.error('会话已过期，请重新登录');
      return false; // 验证失败
    }
  }, [setUserLevel, setUserName, setUserId]);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await fetch(`${gatewayUrl()}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const { authToken, userLevel, userName, userId } = data.data;

          // 使用统一的 setAuthToken 函数
          setAuthToken(authToken);

          // 存储用户权限、用户名和用户ID
          setUserLevel(userLevel || 'operator'); // 默认为操作员
          setUserName(userName || '');
          setUserId(userId || '');

          // 验证token - 直接调用，不依赖 useCallback 的依赖项
          const verificationSuccess = await verifyToken(authToken);
          if (verificationSuccess) {
            toast.success('登录成功');
            // 打印 authToken 和用户权限
            console.log('登录成功，authToken:', authToken);
            console.log('用户权限:', userLevel);
            console.log('用户名:', userName);
            console.log('用户ID:', userId);
          } else {
            // 即使验证失败，token 仍然被保存，用户可以进行重试
            toast.warning('登录成功，但用户信息获取失败');
          }
        } else {
          throw new Error(data.message || '登录失败');
        }
      } else {
        throw new Error('登录请求失败');
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error instanceof Error ? error.message : '登录失败');
      throw error;
    }
  }, [setAuthToken, setUserLevel, setUserName, setUserId, verifyToken]);

  useEffect(() => {
    // 检查是否有存储的authToken（用于页面刷新后恢复会话）
    // 使用 sessionStorage，关闭浏览器后数据会被清除
    const storedToken = sessionStorage.getItem('authToken');
    const storedUserLevel = sessionStorage.getItem('userLevel');
    const storedUserName = sessionStorage.getItem('userName');
    const storedUserId = sessionStorage.getItem('userId');

    if (storedToken) {
      setAuthTokenState(storedToken);

      // 如果本地存储了用户权限、用户名和用户ID，先恢复它们
      if (storedUserLevel) {
        setUserLevelState(storedUserLevel);
      }
      if (storedUserName) {
        setUserNameState(storedUserName);
      }
      if (storedUserId) {
        setUserIdState(storedUserId);
      }

      // 验证token
      verifyToken(storedToken);
    }
  }, [verifyToken]);

  const value = {
    isAuthenticated,
    setIsAuthenticated,
    user,
    setUser,
    authToken,
    setAuthToken,
    userLevel, // 新增：提供用户权限
    setUserLevel, // 新增：提供设置用户权限的方法
    userName, // 新增：提供用户名
    setUserName, // 新增：提供设置用户名的方法
    userId, // 新增：提供用户ID
    setUserId, // 新增：提供设置用户ID的方法
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value} >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}