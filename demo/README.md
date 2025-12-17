# 图片API Demo

这是一个独立的demo测试项目，用于测试后端图片API接口和前端显示功能。

## 功能说明

- ✅ 独立的FastAPI后端服务，不耦合正式工程
- ✅ 提供与正式工程相同的API接口格式
- ✅ 简单的前端页面，展示图片加载效果
- ✅ 支持自动加载可用图片列表
- ✅ 支持手动测试指定图片

## 使用方法

### 1. 启动后端服务

```bash
# 进入项目根目录
cd /Users/hepeng/Project/lead_depot/LeafDepot

# 运行demo服务
python demo/image_api_demo.py
```

服务将在 `http://localhost:8001` 启动

### 2. 访问前端页面

在浏览器中打开：
```
http://localhost:8001
```

### 3. API接口说明

#### 获取图片（与正式工程接口一致）

```
GET /api/inventory/image?taskNo={taskNo}&binLocation={binLocation}&cameraType={cameraType}&filename={filename}
```

**参数说明：**
- `taskNo`: 任务编号（demo中使用 "demo"）
- `binLocation`: 储位名称（demo中使用 "test01"）
- `cameraType`: 相机类型（demo中使用 "main"）
- `filename`: 文件名（如 "main.jpeg", "depth.jpg" 等）

**示例：**
```
http://localhost:8001/api/inventory/image?taskNo=demo&binLocation=test01&cameraType=main&filename=main.jpeg
```

#### 获取可用图片列表（demo专用）

```
GET /api/demo/images/list
```

返回所有可用的测试图片列表。

## 文件结构

```
demo/
├── image_api_demo.py    # 后端API服务
├── static/
│   └── index.html       # 前端测试页面
└── README.md           # 本文件
```

## 图片路径查找逻辑

后端会按以下顺序查找图片：

1. `output/{taskNo}/{binLocation}/{cameraType}/{filename}` - 正式工程的路径结构
2. `tests/test_images/total/test01/{filename}` - 测试图片目录
3. `core/detection/output/{filename}` - 检测输出目录

## 注意事项

- 这是一个独立的demo项目，不会影响正式工程
- 前端调用方式与正式工程保持一致
- 可以用于测试和调试图片API功能
- 生产环境请使用正式工程的API服务

## 停止服务

按 `Ctrl+C` 停止服务

