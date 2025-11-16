import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { GATEWAY_URL } from '@/config/ip_address'; // 导入常量

interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (isAuthenticated: boolean) => void;
  user: any;
  setUser: (user: any) => void;
  authToken: string | null;
  setAuthToken: (authToken: string | null) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [authToken, setAuthTokenState] = useState<string | null>(null);

  // 统一的设置 token 函数，确保状态和 localStorage 同步
  const setAuthToken = useCallback((token: string | null) => {
    setAuthTokenState(token);
    if (token) {
      localStorage.setItem('authToken', token);
    } else {
      localStorage.removeItem('authToken');
    }
  }, []);

  const logout = useCallback(() => {
    setIsAuthenticated(false);
    setUser(null);
    setAuthToken(null);
    toast.success('已退出登录');
  }, [setAuthToken]);

  const verifyToken = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${GATEWAY_URL}/auth/token?token=${token}`);
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
        return true; // 验证成功
      } else {
        throw new Error('Token verification failed');
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      // Token 验证失败时，只清除认证状态，但保留 token 以便重试
      setIsAuthenticated(false);
      setUser(null);
      toast.error('会话已过期，请重新登录');
      return false; // 验证失败
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await fetch(`${GATEWAY_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const { authToken } = data.data;
          // 使用统一的 setAuthToken 函数
          setAuthToken(authToken);

          // 验证token - 直接调用，不依赖 useCallback 的依赖项
          const verificationSuccess = await verifyToken(authToken);
          if (verificationSuccess) {
            toast.success('登录成功');
            // 打印 authToken
            console.log('登录成功，authToken:', authToken);
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
  }, [setAuthToken, verifyToken]);

  useEffect(() => {
    // 检查是否有存储的authToken（用于页面刷新后恢复会话）
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setAuthTokenState(storedToken);
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