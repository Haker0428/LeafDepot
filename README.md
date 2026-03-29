<!--
 * @Author: big box big box@qq.com
 * @Date: 2025-12-14 15:55:40
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-14 16:15:05
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

## 快速开始

### 1. 环境准备

```bash
# 创建并激活 Conda 环境
conda env create -f environment.yml
conda activate tobacco_env

# 安装 Python 依赖
pip install fastapi uvicorn requests python-multipart
pip install ultralytics opencv-python
```

### 2. 启动服务

```bash
# 启动 LMS 模拟服务（端口 6000）
./scripts/start_lms_sim.sh

# 启动网关服务（端口 8000）- 新终端
./scripts/start_gateway.sh

# 启动前端服务（端口 3000）- 新终端
cd web && pnpm install && pnpm run dev
```

### 3. 验证

```bash
# 运行验证脚本
./scripts/verify.sh
```

访问：
- 前端界面：http://localhost:3000
- 网关 API 文档：http://localhost:8000/docs
- LMS API 文档：http://localhost:6000/docs

默认登录信息：
- 用户名：`admin`
- 密码：`admin`

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