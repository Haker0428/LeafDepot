<!--
 * @Author: big box big box@qq.com
 * @Date: 2025-12-14 15:55:40
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2026-05-31
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
├── systemd/           # systemd unit 模板（install.sh 自动生成）
└── scripts/           # 启动脚本
```

---

## 服务管理（systemd）

所有服务通过 systemd 管理，支持开机自启、崩溃自动恢复、每日凌晨 4 点定时重启。

### 涉及的 5 个服务

| 服务 | 端口 | 说明 |
|------|------|------|
| leafdepot-gateway | 8000 | API 网关 |
| leafdepot-worker  | -     | 盘点任务后台处理 |
| leafdepot-lms     | 6000 | LMS 模拟服务 |
| leafdepot-rcs     | 4001 | RCS 模拟服务 |
| leafdepot-web     | 5173 | 前端界面 |

---

## 部署步骤

### 首次部署（新机器）

#### 1. 安装 conda 环境

```bash
# 创建并激活 conda 环境
conda env create -f environment.yml
conda activate tobacco_env

# 通过 conda 安装 pnpm（Node.js 工具，非 conda 包）
npm install -g pnpm
```

#### 2. 修改配置

编辑 `config.json`，将 `host` 改为服务器 IP：

```json
{
  "host": "10.16.82.95",
  "is_sim": false,
  ...
}
```

- `is_sim: true` = 模拟模式（不连真实机器人）
- `is_sim: false` = 真实模式

#### 3. 部署 systemd 服务

```bash
./install.sh
```

`install.sh` 会自动检测 conda、pnpm、node 路径，生成所有 systemd unit 文件并启用服务。

#### 4. 启动所有服务

```bash
sudo systemctl start leafdepot-gateway leafdepot-worker leafdepot-lms leafdepot-rcs leafdepot-web
```

---

### 更新配置后重新部署

修改了配置或更新了代码后，重新运行：

```bash
./install.sh
```

会重新生成所有 systemd unit 文件并重启对应服务。

---

### 日常运维命令

```bash
# 启动
sudo systemctl start leafdepot-gateway leafdepot-worker leafdepot-lms leafdepot-rcs leafdepot-web

# 停止
sudo systemctl stop leafdepot-gateway leafdepot-worker leafdepot-lms leafdepot-rcs leafdepot-web

# 查看状态
sudo systemctl status leafdepot-gateway
sudo systemctl status leafdepot-worker

# 查看所有服务状态
sudo systemctl list-units 'leafdepot-*'

# 查看定时器（每日凌晨4点重启）
sudo systemctl list-timers | grep leafdepot

# 查看日志
tail -f /root/LDUI/software/LeafDepot/logs/gateway_systemd.log
```

---

## 脚本说明

| 脚本 | 用途 | 使用频率 |
|------|------|---------|
| `install.sh` | 生成并安装 systemd unit 文件 | 首次部署 + 更新时 |

**为什么用 systemd 而不是其他方式？**

systemd 是 Linux 标准服务管理方式，支持：
- 开机自启
- 进程崩溃自动恢复（Restart=always）
- 每日定时重启（timer，清除内存积累）
- 统一日志（journalctl）

`install.sh` 生成的 unit 文件路径为相对路径（基于脚本所在目录），可在任意目录下运行。

---

## 验证

```bash
# 确认所有端口在监听
ss -tlnp | grep -E '8000|6000|4001|5173'

# 测试 API
curl http://10.16.82.95:8000/docs

# 浏览器访问
http://10.16.82.95:5173
```

默认登录信息：
- 用户名：`admin`
- 密码：`admin`

---

## 维护

### 更新 Python 依赖

```bash
# 导出 conda 环境（推荐，只导出显式安装的包）
conda env export --from-history > environment.yml

# 完整导出
conda env export > environment.yml
```

---

## 详细文档

- [启动和验证指南](docs/STARTUP_GUIDE.md) - 完整的启动步骤和验证方法
- [架构文档](ARCHITECTURE_REFACTOR.md) - 项目架构说明
- [重构总结](docs/REFACTOR_SUMMARY.md) - 架构重构详情
