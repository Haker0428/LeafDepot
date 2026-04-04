<!--
 * @Author: big box big box@qq.com
 * @Date: 2025-12-14 15:55:40
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2026-04-04
 * @FilePath: /gateway/home/ubuntu/Projects/LeafDepot/README.md
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
-->
# LeafDepot

本项目致力于开发一套自动识别烟箱数量的视觉算法，用于烟草仓储场景，替代人工统计方式，从而提升仓储效率并减少差错率。

## 主要功能

- 基于计算机视觉的烟箱数量自动识别
- 适应不同堆叠方式和光照条件
- 提供高准确率和实时识别能力
- 可与仓储管理系统（WMS）对接使用

## 项目结构

```
LeafDepot/
├── core/              # 核心算法模块（检测、视觉处理）
├── services/          # 服务层（API、模拟服务）
├── web/               # 前端应用
├── hardware/          # 硬件接口
├── shared/            # 共享资源（模型、工具）
├── tests/             # 测试
├── tools/             # 开发工具
├── docs/              # 文档
└── scripts/           # 启动脚本
```

## 首次部署配置

**所有服务地址统一从 `config.json` 管理，只需修改 `host` 字段即可全局生效。**

### 1. 修改主机地址

编辑 `config.json`，将 `host` 改为您部署服务器的 IP：

```json
{
  "host": "10.16.82.95",   ← 修改这里，其他地址自动派生
  "ports": {
    "gateway": 8000,
    "lms": 6000,
    "rcs": 4001,
    "camsys": 5000
  },
  "frontend_port": 5173,
  ...
}
```

修改后，Gateway、LMS、RCS 的 URL 全部自动派生：
- Gateway: `http://{host}:8000`
- LMS: `http://{host}:6000`
- RCS: `http://{host}:4001`
- CamSys: `http://{host}:5000`

### 2. 修改运行模式

```json
{
  "is_sim": true,      // true = 模拟模式（不连真实机器人），false = 真实模式
  "with_camera": false // 模拟模式下是否执行真实相机脚本（跳过等待机器人）
}
```

### 3. 编译相机驱动（如需真实相机）

编辑 `hardware/cam_sys/CMakeLists.txt`，修改 Python 路径为本地 conda 环境路径（第 106-107 行）：

```cmake
# 根据您的 conda 环境修改以下两行
set (Python_ROOT_DIR     "/your/conda/env/tobacco_env/bin/python3.10")
set(pybind11_DIR        "/your/conda/env/tobacco_env/lib/python3.10/site-packages/pybind11/share/cmake/pybind11")
```

然后编译：

```bash
cd hardware/cam_sys/build
cmake ..
make -j$(nproc)
```

如不编译，盘点将使用模拟图片数据。

### 4. 启动服务

```bash
# 启动 LMS 模拟服务（端口 6000）
./scripts/start_lms_sim.sh

# 启动网关服务（端口 8000）- 新终端
./scripts/start_gateway.sh

# 启动前端服务（端口 5173）- 新终端
cd web && pnpm install && pnpm run dev
```

### 5. 验证

```bash
./scripts/verify.sh
```

访问：
- 前端界面：`http://{host}:5173`
- 网关 API 文档：`http://{host}:8000/docs`
- LMS API 文档：`http://{host}:6000/docs`

默认登录信息：
- 用户名：`admin`
- 密码：`admin`

## 快速开始（本地开发）

如在本地机器直接运行（不连接真实机器人），服务均以 localhost 运行：

```bash
# 1. config.json 中 host 保持默认，is_sim 设为 true
# 2. 启动服务
./scripts/start_lms_sim.sh
./scripts/start_gateway.sh
cd web && pnpm install && pnpm run dev
# 3. 浏览器访问 http://localhost:5173
```

## 详细文档

- [启动和验证指南](docs/STARTUP_GUIDE.md) - 完整的启动步骤和验证方法
- [架构文档](ARCHITECTURE_REFACTOR.md) - 项目架构说明
- [重构总结](docs/REFACTOR_SUMMARY.md) - 架构重构详情

## 维护

后续如果有更新python库，在根目录使用如下命令:
```bash
conda env export --from-history > environment.yml(只更新conda包)
conda env export > environment.yml(更新conda包和pip包)
```
