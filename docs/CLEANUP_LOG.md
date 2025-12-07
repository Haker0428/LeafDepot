# 清理日志

## 删除的废弃目录

### 2024-12-07

1. **BoxDetect/** (36M)
   - 状态：✅ 已删除
   - 原因：核心检测模块已迁移到 `core/detection/`
   - 迁移位置：
     - `BoxDetect/src/detection/*` → `core/detection/detection/`
     - `BoxDetect/src/utils/*` → `core/detection/utils/`
     - `BoxDetect/src/visualization/*` → `core/detection/visualization/`
     - `BoxDetect/src/pile_config.json` → `core/config/pile_config.json`
     - `BoxDetect/tests/*` → `tests/test_images/`
     - `BoxDetect/yolo_weights/*` → `shared/models/yolo/`

2. **Intergration/** (718M)
   - 状态：✅ 已删除
   - 原因：所有功能已迁移到新架构
   - 迁移位置：
     - `Intergration/app/gateway.py` → `services/api/gateway.py`
     - `Intergration/app/yolo_detection.py` → `core/vision/yolo_detector.py`
     - `Intergration/app/barcode_recognizer.py` → `core/vision/barcode_recognizer.py`
     - `Intergration/app/custom_utils.py` → `services/utils/compression.py`
     - `Intergration/app/sim/*` → `services/sim/`
     - `Intergration/app/cam_sys/*` → `hardware/cam_sys/`
     - `Intergration/ui/*` → `web/`
     - `Intergration/utils/BarcodeReaderCLI/*` → `shared/tools/BarcodeReaderCLI/`
     - `Intergration/yolo_model_weight/*` → `shared/models/yolo/`

3. **Yolo2BarCode/**
   - 状态：✅ 已归档（未删除）
   - 位置：`archive/Yolo2BarCode/`
   - 原因：早期原型代码，保留作为参考

## 当前项目结构

```
LeafDepot/
├── core/              # 核心算法模块
├── services/          # 服务层
├── web/               # 前端应用
├── hardware/          # 硬件接口
├── shared/            # 共享资源
├── tests/             # 测试
├── tools/             # 开发工具
├── docs/              # 文档
├── scripts/           # 启动脚本
└── archive/           # 归档旧代码（包含 Yolo2BarCode）
```

## 注意事项

- 所有功能已完整迁移到新架构
- 所有导入路径已更新
- 启动脚本已更新
- 如有需要，可以从 Git 历史恢复旧目录

