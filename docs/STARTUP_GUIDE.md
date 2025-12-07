# 启动和验证指南

## 📋 前置条件

### 1. 环境准备

```bash
# 1. 确保已安装 Conda
conda --version

# 2. 创建并激活环境
conda env create -f environment.yml
conda activate tobacco_env

# 3. 安装 Python 依赖（如果还没有）
pip install fastapi uvicorn requests python-multipart
pip install ultralytics opencv-python
```

### 2. 检查模型和工具

```bash
# 检查 YOLO 模型是否存在
ls -lh shared/models/yolo/best.pt

# 检查条形码识别工具是否存在
ls -lh shared/tools/BarcodeReaderCLI/bin/BarcodeReaderCLI

# 检查配置文件
ls -lh core/config/pile_config.json
```

## 🚀 启动步骤

### 步骤 1：启动 LMS 模拟服务（端口 6000）

```bash
# 在项目根目录执行
conda activate tobacco_env
./scripts/start_lms_sim.sh

# 或者手动启动
cd services/sim/lms
uvicorn sim_lms_server:app --host 0.0.0.0 --port 6000 --reload
```

**验证**：访问 http://localhost:6000/docs 应该能看到 Swagger API 文档

### 步骤 2：启动网关服务（端口 8000）

在新的终端窗口：

```bash
# 在项目根目录执行
conda activate tobacco_env
./scripts/start_gateway.sh

# 或者手动启动
cd services/api
uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload
```

**验证**：访问 http://localhost:8000/docs 应该能看到 Swagger API 文档

### 步骤 3：（可选）启动 RCS 模拟服务（端口 4001）

如果需要测试 RCS 功能：

```bash
# 在项目根目录执行
conda activate tobacco_env
./scripts/start_rcs_sim.sh

# 或者手动启动
cd services/sim/rcs
uvicorn sim_rcs_server:app --host 0.0.0.0 --port 4001 --reload
```

### 步骤 4：启动前端服务（端口 3000）

在新的终端窗口：

```bash
# 进入前端目录
cd web

# 安装依赖（如果还没有）
pnpm install
# 或者
npm install

# 启动开发服务器
pnpm run dev
# 或者
npm run dev
```

**验证**：访问 http://localhost:3000 应该能看到前端界面

## ✅ 验证步骤

### 1. 验证后端服务

#### 测试 LMS 模拟服务
```bash
# 测试登录接口
curl -X GET "http://localhost:6000/login?userCode=admin&password=admin"

# 应该返回 JSON 格式的响应，包含 authToken
```

#### 测试网关服务
```bash
# 测试登录接口（通过网关）
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 应该返回成功响应和 token
```

#### 测试网关文档
访问 http://localhost:8000/docs，应该能看到：
- 所有 API 端点列表
- 可以尝试调用 API
- 看到请求/响应格式

### 2. 验证核心检测模块

```bash
# 在项目根目录
conda activate tobacco_env
cd core/detection

# 运行测试脚本（如果有）
python predict.py

# 或者使用 Python 交互式测试
python
```

```python
# Python 交互式测试
from core.detection import prepare_logic, cluster_layers
from core.detection.utils import extract_yolo_detections
from ultralytics import YOLO

# 测试导入是否正常
print("✅ 核心模块导入成功")
```

### 3. 验证视觉处理模块

```python
# Python 交互式测试
from core.vision import YoloDetection, BarcodeRecognizer

# 测试 YOLO 检测器
detector = YoloDetection(model_path="../../shared/models/yolo/best.pt")
print("✅ YOLO 检测器初始化成功")

# 测试条形码识别器
recognizer = BarcodeRecognizer()
print("✅ 条形码识别器初始化成功")
```

### 4. 验证前端

1. **访问前端界面**
   - 打开浏览器访问 http://localhost:3000
   - 应该能看到登录页面

2. **测试登录**
   - 用户名：`admin`
   - 密码：`admin`
   - 点击登录，应该能成功进入系统

3. **检查网络请求**
   - 打开浏览器开发者工具（F12）
   - 查看 Network 标签
   - 登录时应该能看到请求发送到 `http://localhost:8000/login`

## 🔍 常见问题排查

### 问题 1：端口被占用

```bash
# 检查端口占用
lsof -i :8000  # 网关端口
lsof -i :6000  # LMS端口
lsof -i :3000  # 前端端口

# 杀死进程
kill -9 <PID>
```

### 问题 2：导入错误

```bash
# 确保在项目根目录，Python 能找到模块
cd /Users/hepeng/Project/LeafDepot
python -c "from core.detection import prepare_logic; print('OK')"

# 如果失败，检查 PYTHONPATH
export PYTHONPATH=/Users/hepeng/Project/LeafDepot:$PYTHONPATH
```

### 问题 3：模型文件不存在

```bash
# 检查模型路径
ls -lh shared/models/yolo/best.pt

# 如果不存在，需要从其他地方复制或下载
# 原始位置可能在 archive/ 目录中
```

### 问题 4：前端无法连接后端

1. 检查 `web/src/config/ip_address.ts` 中的 `GATEWAY_URL` 是否正确
2. 确保后端服务正在运行
3. 检查浏览器控制台的错误信息

### 问题 5：CORS 错误

如果前端请求出现 CORS 错误，检查 `services/api/gateway.py` 中的 `origins` 配置：

```python
origins = [
    "http://localhost",
    "http://localhost:3000",  # 前端地址
    # ...
]
```

## 📊 完整验证清单

- [ ] Conda 环境已激活
- [ ] LMS 模拟服务运行在 6000 端口
- [ ] 网关服务运行在 8000 端口
- [ ] 前端服务运行在 3000 端口
- [ ] 可以访问 http://localhost:6000/docs
- [ ] 可以访问 http://localhost:8000/docs
- [ ] 可以访问 http://localhost:3000
- [ ] 前端可以成功登录
- [ ] 核心检测模块可以正常导入
- [ ] 视觉处理模块可以正常初始化
- [ ] API 调用返回预期结果

## 🎯 快速验证脚本

创建一个快速验证脚本：

```bash
#!/bin/bash
# 快速验证所有服务

echo "🔍 检查服务状态..."

# 检查端口
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "✅ 端口 $1 正在监听"
    else
        echo "❌ 端口 $1 未监听"
    fi
}

check_port 6000  # LMS
check_port 8000  # Gateway
check_port 3000  # Frontend

echo ""
echo "📡 测试 API..."

# 测试网关健康检查
curl -s http://localhost:8000/docs > /dev/null && echo "✅ 网关 API 文档可访问" || echo "❌ 网关 API 文档不可访问"

echo ""
echo "✅ 验证完成！"
```

保存为 `scripts/verify.sh`，然后：

```bash
chmod +x scripts/verify.sh
./scripts/verify.sh
```

