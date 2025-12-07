# 服务层

此目录包含所有的后端服务和API。

## 目录结构

- `api/` - API 服务
  - `gateway.py` - 主网关服务（FastAPI）
  - `routers/` - API 路由（待拆分）

- `utils/` - 服务工具
  - `compression.py` - 数据压缩编码工具

- `sim/` - 模拟服务
  - `lms/` - LMS 模拟服务
  - `rcs/` - RCS 模拟服务
  - `cam_sys/` - 相机系统模拟

## 启动服务

```bash
# 启动网关服务
cd services/api
python gateway.py

# 或使用脚本
../../scripts/start_gateway.sh
```

## API 文档

启动服务后访问：http://localhost:8000/docs

