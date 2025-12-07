# BoxDetect 可扩展架构说明

## 📋 架构概述

新架构将满层判断和处理逻辑分离，采用**策略模式**设计，方便后续扩展和调试。

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│              StackProcessorFactory (工厂)                │
│  根据满层判断结果自动选择对应的处理模块                      │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│ FullLayerDetector│          │  Processing       │
│  (满层判断模块)    │          │  (处理模块)        │
└──────────────────┘          └──────────────────┘
        │                               │
        │                               ├──► FullStackProcessor
        │                               │    (满层处理)
        │                               │
        │                               └──► PartialStackProcessor
        │                                    (非满层处理)
        │
        └──► CoverageBasedDetector
             (基于覆盖率的判断器)
```

## 📦 核心模块

### 1. 满层判断模块 (`full_layer_detector.py`)

**职责**：判断堆垛是否满层

**接口**：
- `FullLayerDetector` (抽象基类)
- `CoverageBasedDetector` (默认实现)
- `detect_full_layer()` (便捷函数)

**特点**：
- ✅ 可独立调试
- ✅ 可自定义判断逻辑
- ✅ 输出详细的调试信息

### 2. 满层处理模块 (`full_stack_processor.py`)

**职责**：处理满层堆垛的计数逻辑

**接口**：
- `FullStackProcessor` (抽象基类)
- `TemplateBasedFullProcessor` (默认实现)
- `process_full_stack()` (便捷函数)

**特点**：
- ✅ 可自定义处理策略
- ✅ 支持多种满层场景

### 3. 非满层处理模块 (`partial_stack_processor.py`)

**职责**：处理非满层堆垛的计数逻辑

**接口**：
- `PartialStackProcessor` (抽象基类)
- `TemplateBasedPartialProcessor` (默认实现)
- `process_partial_stack()` (便捷函数)

**特点**：
- ✅ 可自定义处理策略
- ✅ 支持复杂的非满层场景

### 4. 处理器工厂 (`stack_processor_factory.py`)

**职责**：根据满层判断结果自动选择对应的处理模块

**接口**：
- `StackProcessorFactory` (工厂类)
- `process_stack()` (便捷函数)

**工作流程**：
1. 使用满层判断模块判断是否满层
2. 根据判断结果选择对应的处理模块（满层/非满层）
3. 执行处理并返回结果

## 🚀 使用方式

### 方式1：使用工厂模式（推荐）

```python
from detection import StackProcessorFactory

# 创建工厂（使用默认配置）
factory = StackProcessorFactory(enable_debug=True)

# 处理堆垛（自动判断满层并选择处理模块）
result = factory.process(layers, template_layers, pile_roi)

print(f"是否满层: {result['full']}")
print(f"总箱数: {result['total']}")
```

### 方式2：自定义判断器

```python
from detection import CoverageBasedDetector, StackProcessorFactory

# 创建自定义判断器（调整阈值）
custom_detector = CoverageBasedDetector(
    coverage_threshold=0.85,  # 降低覆盖率阈值
    cv_gap_threshold=0.5,     # 提高间距变异系数阈值
    enable_debug=True
)

# 使用自定义判断器
factory = StackProcessorFactory(
    detector=custom_detector,
    enable_debug=True
)

result = factory.process(layers, template_layers, pile_roi)
```

### 方式3：自定义处理模块

```python
from detection import (
    TemplateBasedFullProcessor,
    TemplateBasedPartialProcessor,
    StackProcessorFactory
)

# 继承并实现自定义处理器
class MyFullProcessor(TemplateBasedFullProcessor):
    def process(self, layers, template_layers, detection_result):
        # 自定义处理逻辑
        result = super().process(layers, template_layers, detection_result)
        # 添加额外处理
        return result

# 使用自定义处理器
factory = StackProcessorFactory(
    full_processor=MyFullProcessor(),
    partial_processor=MyPartialProcessor(),
    enable_debug=True
)

result = factory.process(layers, template_layers, pile_roi)
```

### 方式4：分步骤使用（独立调试）

```python
from detection import (
    CoverageBasedDetector,
    TemplateBasedFullProcessor,
    TemplateBasedPartialProcessor
)

# Step 1: 独立判断满层（可调试）
detector = CoverageBasedDetector(enable_debug=True)
detection_result = detector.detect(layers, template_layers, pile_roi)

# Step 2: 根据判断结果选择处理模块
if detection_result["full"]:
    processor = TemplateBasedFullProcessor(enable_debug=True)
    result = processor.process(layers, template_layers, detection_result)
else:
    processor = TemplateBasedPartialProcessor(enable_debug=True)
    result = processor.process(layers, template_layers, detection_result)
```

### 方式5：向后兼容（原有代码无需修改）

```python
from detection import verify_full_stack

# 原有接口仍然可用，内部使用新架构
result = verify_full_stack(layers, template_layers, pile_roi)

print(f"是否满层: {result['full']}")
print(f"总箱数: {result['total']}")
```

## 🔧 扩展指南

### 扩展满层判断逻辑

1. 继承 `FullLayerDetector` 基类
2. 实现 `detect()` 方法
3. 在工厂中使用自定义判断器

```python
class MyCustomDetector(FullLayerDetector):
    def detect(self, layers, template_layers, pile_roi):
        # 实现自定义判断逻辑
        return {
            "full": True/False,
            "reason": "custom_reason",
            "top_layer": {...},
            "metrics": {...}
        }
```

### 扩展满层处理逻辑

1. 继承 `FullStackProcessor` 基类
2. 实现 `process()` 方法
3. 在工厂中使用自定义处理器

```python
class MyFullProcessor(FullStackProcessor):
    def process(self, layers, template_layers, detection_result):
        # 实现自定义处理逻辑
        return {
            "total": 100,
            "strategy": "custom_strategy",
            "details": {...}
        }
```

### 扩展非满层处理逻辑

1. 继承 `PartialStackProcessor` 基类
2. 实现 `process()` 方法
3. 在工厂中使用自定义处理器

```python
class MyPartialProcessor(PartialStackProcessor):
    def process(self, layers, template_layers, detection_result):
        # 实现自定义处理逻辑
        return {
            "total": 50,
            "strategy": "custom_strategy",
            "details": {...}
        }
```

## 📊 返回结果格式

### 工厂处理结果

```python
{
    "full": bool,              # 是否满层
    "total": int,               # 总箱数
    "detection": {              # 满层判断结果
        "full": bool,
        "reason": str,
        "top_layer": {...},
        "metrics": {...}
    },
    "processing": {             # 处理结果
        "total": int,
        "strategy": str,
        "details": {...}
    },
    "top_layer": {...},         # 顶层信息
    "reason": str               # 判断依据
}
```

## ✅ 优势

1. **模块化设计**：判断和处理逻辑分离，职责清晰
2. **易于调试**：每个模块可独立调试，输出详细信息
3. **易于扩展**：通过继承基类即可扩展新功能
4. **向后兼容**：原有代码无需修改即可使用
5. **灵活配置**：可自定义判断器和处理器

## 📝 注意事项

1. 所有模块都支持 `enable_debug` 参数，可控制调试输出
2. 自定义判断器和处理器需要遵循接口规范
3. 工厂模式会自动选择对应的处理模块，无需手动判断
4. 原有 `verify_full_stack()` 函数仍然可用，内部使用新架构

