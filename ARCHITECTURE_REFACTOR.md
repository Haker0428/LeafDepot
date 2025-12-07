# 架构重构方案

## 📋 当前架构问题分析

### 1. 目录结构混乱
- `Intergration/` 目录名拼写错误（应为 `Integration`）
- 功能分散：YOLO检测代码在多个地方（`BoxDetect/`, `Intergration/app/`, `Yolo2BarCode/`）
- 工具重复：`BarcodeReaderCLI` 在多个目录中都有副本
- 缺少统一的共享模块目录

### 2. 模块职责不清
- `Yolo2BarCode/` - 早期原型代码，功能已被集成到主系统
- `Intergration/app/yolo_detection.py` 和 `Intergration/app/barcode_recognizer.py` - 应该属于核心检测模块
- `BoxDetect/` - 核心算法模块，但与其他模块耦合度低

### 3. 依赖管理问题
- 模型权重文件分散（`yolo_model_weight/`, `yolo_weights/`）
- 工具可执行文件重复
- 配置文件分散

## 🏗️ 新架构设计

### 目录结构

```
LeafDepot/
├── README.md                          # 项目总说明
├── environment.yml                    # Conda 环境配置
├── requirements.txt                   # Python 依赖（可选）
│
├── core/                              # 核心算法模块
│   ├── __init__.py
│   ├── README.md
│   │
│   ├── detection/                     # 检测算法（原 BoxDetect/src）
│   │   ├── __init__.py
│   │   ├── detection/                 # 检测核心逻辑
│   │   │   ├── scene_prepare.py
│   │   │   ├── layer_clustering.py
│   │   │   ├── full_layer_detector.py
│   │   │   ├── full_stack_processor.py
│   │   │   ├── partial_stack_processor.py
│   │   │   └── stack_processor_factory.py
│   │   ├── visualization/             # 可视化
│   │   │   └── scene_visualize.py
│   │   └── utils/                     # 工具函数
│   │       ├── exceptions.py
│   │       ├── path_utils.py
│   │       ├── pile_db.py
│   │       └── yolo_utils.py
│   │
│   ├── vision/                        # 视觉处理模块（整合 YOLO 和条形码）
│   │   ├── __init__.py
│   │   ├── yolo_detector.py          # YOLO 目标检测（来自 Intergration/app/yolo_detection.py）
│   │   ├── barcode_recognizer.py     # 条形码识别（来自 Intergration/app/barcode_recognizer.py）
│   │   └── image_processor.py        # 图像预处理工具
│   │
│   └── config/                        # 配置文件
│       ├── pile_config.json
│       └── detection_config.yaml
│
├── services/                          # 服务层（原 Intergration/app）
│   ├── __init__.py
│   ├── README.md
│   │
│   ├── api/                           # API 服务
│   │   ├── __init__.py
│   │   ├── gateway.py                 # 主网关服务
│   │   ├── routers/                   # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # 认证相关
│   │   │   ├── lms.py                 # LMS 接口
│   │   │   └── rcs.py                 # RCS 接口
│   │   └── middleware/                # 中间件
│   │       └── cors.py
│   │
│   ├── utils/                         # 服务工具
│   │   ├── __init__.py
│   │   ├── compression.py             # 数据压缩（原 custom_utils.py）
│   │   └── encryption.py              # 加密工具（原 passwd_encryptor）
│   │
│   └── sim/                           # 模拟服务
│       ├── __init__.py
│       ├── lms/                       # LMS 模拟服务
│       │   ├── sim_lms_server.py
│       │   └── start_sim_lms_server.sh
│       ├── rcs/                       # RCS 模拟服务
│       │   ├── sim_rcs_server.py
│       │   └── start_sim_rcs_server.sh
│       └── cam_sys/                   # 相机系统模拟
│           └── sim_cam_sys.py
│
├── web/                               # 前端应用（原 Intergration/ui）
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── contexts/
│       └── config/
│
├── hardware/                          # 硬件接口（原 Intergration/app/cam_sys）
│   ├── __init__.py
│   ├── README.md
│   ├── cam_sys/                       # 相机系统
│   │   ├── CMakeLists.txt
│   │   ├── config.json
│   │   ├── src/                       # C++ 源码
│   │   ├── include/                   # 头文件
│   │   └── lib/                       # 库文件
│   └── README.md
│
├── shared/                            # 共享资源和工具
│   ├── models/                        # 模型权重（统一管理）
│   │   ├── yolo/
│   │   │   ├── best.pt
│   │   │   └── data.yaml
│   │   └── README.md
│   │
│   ├── tools/                         # 第三方工具（统一管理）
│   │   ├── BarcodeReaderCLI/
│   │   │   ├── bin/
│   │   │   │   └── BarcodeReaderCLI
│   │   │   └── examples/
│   │   └── README.md
│   │
│   └── data/                          # 共享数据
│       ├── test_images/               # 测试图片
│       └── templates/                 # 模板文件
│
├── tests/                             # 测试文件（统一测试目录）
│   ├── unit/                          # 单元测试
│   ├── integration/                   # 集成测试
│   ├── test_images/                   # 测试图片（原 BoxDetect/tests）
│   │   ├── full/
│   │   ├── partial/
│   │   └── special/
│   └── README.md
│
├── tools/                             # 开发工具脚本
│   ├── prepare_images_for_labeling.py
│   └── README.md
│
├── docs/                              # 文档目录
│   ├── ARCHITECTURE.md                # 架构文档
│   ├── API.md                         # API 文档
│   ├── DEPLOYMENT.md                  # 部署文档
│   └── DEVELOPMENT.md                 # 开发指南
│
├── scripts/                           # 启动脚本
│   ├── start_gateway.sh
│   ├── start_lms_sim.sh
│   └── start_all.sh
│
├── output/                            # 输出目录（运行时生成，gitignore）
│   └── .gitkeep
│
└── archive/                           # 归档旧代码（可选）
    └── Yolo2BarCode/                  # 早期原型代码
```

## 📦 模块职责说明

### 1. `core/` - 核心算法模块
- **detection/** - 堆垛检测算法核心，包含分层、聚类、满层判断等
- **vision/** - 视觉处理，包括 YOLO 检测和条形码识别
- **config/** - 核心配置文件

**特点**：
- 不依赖外部服务
- 可独立测试和使用
- 可以被其他模块导入

### 2. `services/` - 服务层
- **api/** - FastAPI 网关服务和路由
- **utils/** - 服务层工具函数
- **sim/** - 模拟服务，用于开发和测试

**特点**：
- 依赖 `core/` 模块
- 提供 HTTP API 接口
- 处理业务逻辑和数据转换

### 3. `web/` - 前端应用
- React + TypeScript 前端界面

### 4. `hardware/` - 硬件接口
- 相机系统 C++ 代码和库文件

### 5. `shared/` - 共享资源
- **models/** - 模型权重文件（统一管理）
- **tools/** - 第三方工具（如 BarcodeReaderCLI）
- **data/** - 共享数据文件

### 6. `tests/` - 测试
- 统一的测试目录，包含各种测试文件和测试图片

### 7. `tools/` - 开发工具
- 各种辅助脚本和工具

### 8. `docs/` - 文档
- 统一的文档目录

## 🔄 迁移计划

### 阶段 1：创建新目录结构
1. 创建所有新目录
2. 创建必要的 `__init__.py` 和 `README.md` 文件

### 阶段 2：迁移核心模块
1. 迁移 `BoxDetect/src/*` → `core/detection/`
2. 整合 YOLO 检测和条形码识别到 `core/vision/`
3. 迁移配置文件到 `core/config/`

### 阶段 3：迁移服务层
1. 重构 `Intergration/app/gateway.py` → `services/api/gateway.py`
2. 拆分路由到 `services/api/routers/`
3. 迁移工具函数到 `services/utils/`
4. 迁移模拟服务到 `services/sim/`

### 阶段 4：迁移其他资源
1. 迁移前端到 `web/`
2. 迁移硬件代码到 `hardware/`
3. 统一模型权重到 `shared/models/`
4. 统一工具到 `shared/tools/`
5. 迁移测试文件到 `tests/`

### 阶段 5：更新导入路径
1. 更新所有 Python 文件的导入路径
2. 更新配置文件中的路径引用
3. 更新启动脚本

### 阶段 6：归档旧代码
1. 将 `Yolo2BarCode/` 移动到 `archive/`
2. 可选：删除旧目录结构

## ⚠️ 注意事项

1. **保持向后兼容**：在迁移过程中，确保现有功能不受影响
2. **路径更新**：所有相对路径和绝对路径都需要更新
3. **配置文件**：更新所有配置文件中的路径引用
4. **启动脚本**：更新所有启动脚本的工作目录
5. **文档更新**：同步更新所有文档中的路径说明

## 📝 后续改进建议

1. **统一依赖管理**：创建 `requirements.txt` 和 `requirements-dev.txt`
2. **添加 CI/CD**：配置自动化测试和部署
3. **模块化配置**：使用配置文件管理不同环境
4. **API 文档**：使用 OpenAPI/Swagger 自动生成 API 文档
5. **日志系统**：统一日志格式和配置
6. **错误处理**：统一异常处理和错误码

## ❓ 待确认问题

1. 是否需要保留 `Yolo2BarCode/` 作为参考？建议移动到 `archive/`
2. 是否需要同时支持新旧两种目录结构一段时间？
3. 测试策略：是否需要迁移后立即运行完整测试？
4. 模型权重文件大小：是否需要 Git LFS？

