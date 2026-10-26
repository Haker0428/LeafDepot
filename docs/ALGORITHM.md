# LeafDepot 算法与实现逻辑说明

> 本文档基于 **2026-10-24 工作区当前代码**（含未提交修改）梳理，描述系统各算法的输入、处理逻辑与输出。
> 行号引用以当前工作区为准，后续代码改动可能使行号偏移。

---

## 目录

1. [系统总览](#1-系统总览)
2. [烟箱计数检测算法（core/detection）](#2-烟箱计数检测算法)
3. [条码识别与垛型解析链路](#3-条码识别与垛型解析链路)
4. [检测配置文件详解](#4-检测配置文件详解)
5. [盘点任务编排算法（services）](#5-盘点任务编排算法)
6. [结果回写与报表生成](#6-结果回写与报表生成)
7. [RCS 机器人交互协议](#7-rcs-机器人交互协议)
8. [库存数据同步与每日维护](#8-库存数据同步与每日维护)
9. [关键参数速查表](#9-关键参数速查表)
10. [当前未启用/遗留逻辑说明](#10-当前未启用遗留逻辑说明)

---

## 1. 系统总览

LeafDepot 是一套**基于计算机视觉的烟箱数量自动盘点系统**：AMR 机器人载相机逐垛位拍照，算法识别每个储位垛堆的烟箱数量与品规，与系统库存比对生成差异报表。

### 1.1 服务组成

| 进程 | 文件 | 端口 | 职责 |
|---|---|---|---|
| Gateway | `services/api/gateway.py` | 8000 | FastAPI 聚合层：任务编排、拍照、RCS 交互、前端接口 |
| Worker | `services/worker/inventory_worker.py` | — | Redis 队列消费者，只做重量级检测（不拍照） |
| Sim RCS | `services/sim/rcs/sim_rcs_server.py` | 4001 | 模拟机器人调度（is_sim=true 时使用） |
| Sim LMS | `services/sim/lms/sim_lms_server.py` | 6000 | 模拟库管系统（储位/用户数据源） |
| camsys | `hardware/cam_sys/` | — | 海康相机 SDK 封装（C++ .so + Python 抓图脚本） |
| Web | `web/src/` | 5173 | React 前端 |

### 1.2 核心数据流

```
                      ┌─────────── is_sim=true ───────────┐
                      │  sim_rcs_server 模拟 AMR 行走/到位 │
真实 RCS (10.16.82.90)┘                                   │
        │  submit/continue        回调 start/outbin/end    │
        ▼                                                  ▼
┌──────────────────────── Gateway (execute_inventory_workflow) ───────────────────────┐
│  逐储位下发 RCS → 等 AMR 到位(END回调) → 触发相机拍照 → 推 Redis 单bin队列 → 提前下发 │
└──────────┬───────────────────────────────────────────────────────────────┬──────────┘
           │ 拍照落盘                                                        │
           │ capture_img/{taskNo}/{bin}/3d_camera/{main,depth}.jpg          │
           ▼                                                               │
   Redis: inventory:single_bin_queue ──► Worker: BRPOP                      │
           │                                                               │
           ▼                                                               │
┌──────────────────────── Worker (run_barcode_and_detect) ──────────────────┐
│ ① 条码识别: 条码→6位码→Excel查表→品名+垛型→pile_id                        │
│ ② 数量检测: count_boxes(main.jpg, depth.jpg, pile_id) ──► 烟箱总数        │
└──────────┬────────────────────────────────────────────────────────────────┘
           ▼
   Redis: inventory:task:results:{task_no} ──► Gateway 汇总
           ▼
   差异报表 output/history_data/{taskNo}.xlsx + 前端展示
           ▼
   完成确认 → update-bins-data 回写本地库存 bins_data.xlsx
```

核心设计（"**3 队列 + 2 集合**"）：Gateway 负责拍照与 RCS 交互，Worker 只做检测，两者通过 Redis 解耦，使 **AMR 移动与算法检测并行流水线化**。

---

## 2. 烟箱计数检测算法

**算法本质一句话**：YOLO 提供"看见了几个框、每个框多宽"，双目 SGBM 深度提供"每个框离相机多远"，`pile_ID_*.json` 配置把（归一化宽度序列, 深度序列）映射到真实箱数；顶层用该 pattern 匹配计数，下层用垛型模板补齐。

### 2.1 输入

每个储位 3D 相机产出两张关键图（相机横装，原始 2560×2160）：

| 文件 | 内容 |
|---|---|
| `main.jpg` | 垛堆正面 RGB 图 |
| `depth.jpg` | **2×2 四象限立体合成图**（左上=左目、右上=右目；不是现成深度图，深度由算法自己算） |

另有两路扫码相机图片（条码链路用，见第 3 节）。

### 2.2 统一入口与流水线

入口：`count_boxes()`（[core/detection/processors/factory.py:814](../core/detection/processors/factory.py#L814)）→ `StackProcessorFactory.count()`（[factory.py:153](../core/detection/processors/factory.py#L153)），流水线步骤：

```
Step 0  图像旋转矫正     main.jpg 逆时针旋转 90°（相机横装矫正）→ 2160×2560 竖图
Step 1  YOLO 目标检测    pile+box.pt, conf=0.65 → 垛堆框(pile) + 烟箱框(box)列表
Step 1.5 深度矩阵生成    depth.jpg 四象限拆分 → SGBM 立体匹配 → 深度矩阵(毫米)
Step 2  场景准备         用 pile 框做 ROI，中心点过滤出属于本垛的箱框
Step 3  分层聚类         按 y 中心一维间隙分裂 → 层列表（自动定层数）
Step 4  层整理           按 avg_y 升序排列（y 小 = 物理上层），index=1..N
Step 5  加载垛型模板     pile_config.json 取该 pile_id 的每层期望箱数
Step 6  计数             满层判断 → 选择处理器 → 顶层 pattern 匹配 + 下层模板 → 总数
```

输出：**一个整数**（该储位烟箱总数）。

**识别流水线全景图：**

```
main.jpg(横图) ──逆时针90°──► 竖图 ──► YOLO 推理 (pile+box.pt, conf=0.65)
                                            │
                  ┌─────────────────────────┼──────────────────┐
                  ▼                         ▼                  ▼
             pile 框(整垛ROI)           box 框列表          top类(未用)
                  │                         │
                  │  无 pile 框 → total=0   │
                  └───────────┬─────────────┘
                              ▼
           场景准备：箱中心点落在 pile 矩形内？ ──否──► 剔除（邻垛/背景误检）
                              ▼
           分层聚类：按中心 y 排序，相邻 gap 超过 0.6×平均箱高 → 开新层
                              ▼
           层整理：avg_y 升序 → index=1..N（1=最上层）
                              ▼
           满层判断：恒 full（顶层高度过滤：剔除小于 5%×最大箱高 的误检小框）
                              │
depth.jpg(四象限) ─► 拆左上/右上 → SGBM 视差 → depth=768000/d → 深度矩阵(mm)
                              │
                              ▼
           顶层 pattern 匹配（pile_ID_{pile_id}_*.json）
             ├─ 命中 → count = pattern_id 末尾数字
             │        （反推垛型 ≠ 条码垛型 → 用反推垛型重取模板）
             └─ 未命中 → 回落 = 过滤后顶层框数（YOLO 计数）
                              ▼
           total = 顶层 count + sum(模板前 N-1 层) → 写回 Redis 结果队列
```

### 2.3 Step 0：旋转矫正

`_rotate_and_save_image`（[factory.py:642](../core/detection/processors/factory.py#L642)）：`PIL rotate(90)` 正角=逆时针，把横装相机原图转成竖图。深度矩阵生成时同样逆时针旋转 90°，保证两套坐标系一致。

### 2.4 Step 1：YOLO 检测

`_run_yolo_detection`（[factory.py:387](../core/detection/processors/factory.py#L387)）：ultralytics `YOLO("shared/models/yolo/pile+box.pt").predict(conf=0.65)`。类别定义（`pile+box.yaml`）：`box`（烟箱）、`pile`（整垛）、`top`（顶层，当前未用）。

### 2.5 Step 1.5：双目深度计算（SGBM）

`DepthCalculator`（[core/detection/depth/depth_calculator.py](../core/detection/depth/depth_calculator.py)），**项目自算深度，非相机点云**：

1. **拆图**：depth.jpg（2560×2160）按中线切 4 块（每块 1280×1080），取**左上=左目、右上=右目**；
2. **SGBM 立体匹配**求视差 d：`window_size=11, num_disp=128, P1=8·3·11², P2=32·3·11², disp12MaxDiff=10, uniquenessRatio=20, speckleWindowSize=200, speckleRange=2`；
3. **三角测量**：`depth_mm = f·B / d = 6400px × 120mm / d = 768000 / d`（焦距 6400px、基线 120mm）；
4. 视差图逆时针旋转 90°（与 RGB 对齐）→ 深度矩阵存 `depth_cache/depth_matrix.csv`（行=y 列=x，值=毫米，0=无效）。

工作距离约 9.2m～22m。

### 2.6 Step 2：场景准备（ROI 过滤）

`prepare_logic`（[core/detection/core/scene_prepare.py:6](../core/detection/core/scene_prepare.py#L6)）：

1. 取置信度最高的 `pile` 检测框作为垛堆 ROI；无 pile 框 → 直接返回 0 箱；
2. 对每个检测框，**判断其中心点是否落在 pile 矩形内**（不是 IoU）：在 → 保留；不在 → 剔除（背景误检、邻垛箱）。

### 2.7 Step 3：分层聚类（一维间隙分裂）

`cluster_layers_with_box_roi`（[core/detection/core/layer_clustering.py:122](../core/detection/core/layer_clustering.py#L122)）。**不用 KMeans/DBSCAN**，层数自动产生：

```
1. 每个箱取 (yc = (y1+y2)/2,  h = 框高)，按 yc 升序排序（y 小 = 图像上方 = 垛上层）
2. avg_h = 所有箱高度均值
3. 顺序扫描：相邻两箱中心距 gap = yc[i] - yc[i-1]
     gap > threshold → 开新层；否则归入当前层
   自适应阈值（_adaptive_gap_threshold, :11-19）：
     箱总数 < 3 → threshold = 0.8 × avg_h   （箱太少时放宽，避免拆层）
     否则      → threshold = 0.6 × avg_h   （gap_ratio=0.6）
4. 每层输出：index（1=最上层）、avg_y、层 ROI（箱并集上下各外扩 10%·avg_h，裁剪到 pile ROI 内）
```

**物理依据**：层间距≈一个烟箱高度，同层箱 y 中心基本对齐；两箱中心 y 距离超过平均箱高的 60% 即认为跨层。

### 2.8 Step 6a：满层判断（当前策略：恒满层）

`CoverageBasedDetector.detect`（[core/detection/processors/full_layer_detector.py:131](../core/detection/processors/full_layer_detector.py#L131)）。设计上实现了三个指标（现在**只打日志不参与判定**）：

- **coverage**：顶层箱横向区间并集长度 / pile 宽度（区间排序后做经典区间合并）；
- **cv_gap**：箱中心 x 相邻间距的变异系数（std/mean）；
- **cv_width**：箱宽变异系数。

同时做一件**仍然生效**的事：**顶层高度过滤**——删除高度 < 5%·最大箱高的误检小框，并回写顶层箱列表（后续计数用的是过滤后的箱）。

**当前判定逻辑**（工作区版本）：

- 层数 = 1 → `status="full"`（`reason="single_layer_always_proceed"`）；
- 层数 > 1 → `status="full"`（`reason="always_proceed"`）——**顶层无论如何都进入深度比对，不在此处做满层判断**。

连锁影响：非满层处理器和单层处理器分支当前**不可达**，所有垛都走满层处理器（见 2.9）。

### 2.9 Step 6b：计数（当前唯一实际路径：TemplateBasedFullProcessor）

`process`（[core/detection/processors/stack_processor.py:202](../core/detection/processors/stack_processor.py#L202)）：

```
n_detected = 检测到的层数
顶层 = layers[0]（y 最小）
top_count = _calculate_top_layer_count_with_depth(顶层箱, pile_roi, pile_id, 深度矩阵)   ← 见 2.10
若 pattern 反推出的垛型 ≠ 条码给的 pile_id → 用反推垛型重新取模板（条码认错时的兜底）
lower_sum = sum(模板前 n_detected-1 层)        ← 检测 N 层 → 下 N-1 层按模板补齐
total = lower_sum + top_count
```

**计数公式（日志原文）**：`总箱数 = 顶层深度算法箱数 + 下层模板之和`。

例：3×10 垛检测到 3 层、顶层 pattern 命中 10 箱 → `total = 10 + 10 + 10 = 30`。

模板取值方向：第 2 可见层用 `template_layers[0]`、第 3 可见层用 `template_layers[1]`……（顶层永远交给 pattern 匹配，模板只补下层）。

### 2.10 核心子算法：顶层 pattern 匹配

`_calculate_top_layer_count_with_depth`（[stack_processor.py:54-200](../core/detection/processors/stack_processor.py#L54-L200)）：

```
输入：顶层箱（已按中心 x 从左到右排序）、pile_roi、pile_id、深度矩阵

① 逐箱提取特征：
     norm_width = 箱像素宽 / pile_roi 像素宽          ← 归一化宽度（0~1，透视线索：越近越宽）
     depth_mm   = 深度矩阵在箱中心归一化坐标处的值
                 （cy_n = cy/图高 + 0.1 纵向标定偏移：深度图与可见光 FOV 垂直不重叠的硬件错位补偿）
                 （采样：5×5 邻域中位数，|值-中位数|≤500mm 过滤离群点，取均值）
② 误检过滤：depth_mm > 21950mm（≈22m）的箱剔除
③ pattern 匹配（按 pile 优先级遍历 pile_ID_*.json 里的每条 pattern）：
     要求：pattern 的 width_ranges / depth_ranges 数组长度 == 顶层箱数
     对第 j 个箱（从左到右）逐一校验：
        width_ranges[j][0] ≤ norm_width_j ≤ width_ranges[j][1]
        depth_ranges[j][0]  ≤ depth_j     ≤ depth_ranges[j][1]
     全部通过 → count = pattern_id 末尾的数字，返回 {count, matched_pile_id}
④ 全不匹配 → 回落 YOLO 计数（= 过滤后的顶层箱数）
```

**为什么"1 个检测框能数出 5 箱"**：正面视角下多个烟箱侧面纹理被 YOLO 融合/漏检成一个宽框；一个检测框覆盖的**宽度比例**（近大远小的透视由深度补偿）对应确定的物理箱数——这正是 `pile_ID_*.json` 表达的知识。

### 2.11 深度采样细节

`DepthProcessor.extract_depth_at_position`（[core/detection/depth/depth_processor.py:51](../core/detection/depth/depth_processor.py#L51)）：归一化坐标 → 矩阵像素坐标 → 取 5×5 邻域 → 跳过 ≤0 无效值 → 中位数 ±500mm 一轮过滤 → 剩余 <5 点时 mean±2σ 二轮宽松过滤 → 返回均值（毫米）。

---

## 3. 条码识别与垛型解析链路

发生在 `run_barcode_and_detect`（[services/api/inventory/service.py:950](../services/api/inventory/service.py#L950)），先于计数：

```
扫码相机图片 (scan_camera_1/2)
  → BarcodeRecognizer (shared/models/yolo/barcode.pt, 类别 barcode/QR)   core/vision/barcode_recognizer.py
  → 条码文本，如 "91102345..."
  → TobaccoCaseInfoResolver.resolve(): 去掉 (91)/91 前缀 → 正则提取 6 位数字
  → 查 shared/data/烟箱信息汇总完整版.xlsx（精确→模糊匹配）
       → 品名、烟草内部代号、垛型字符串（如 "3*10"）
  → config.py:186  STACK_TYPE_TO_CODE        {"5*8":0, "5*6":1, "5*5":2, "3*10":3, "4*7+2":4}
  → config.py:195  STACK_TYPE_CODE_TO_PILE_ID {0:2, 1:3, 2:5, 3:1, 4:4}   （未知 → 1）
  → pile_id（供计数算法选 pattern 表与模板）
```

条码识别失败 → `actualSpec="未识别"` 且 **actualQuantity 强制 0**（[detection_runner.py:139-148](../services/api/shared/detection_runner.py#L139-L148)）。

**条码链路容错分支图：**

```
扫码图片×2 ──► BarcodeRecognizer (barcode.pt)
                   │
             识别到条码文本？
             ├─ 是 → 去 (91) 前缀 → 提取 6 位数字 → 查《烟箱信息汇总》Excel
             │       ├─ 命中（精确→模糊）→ 品名 + 垛型串 → pile_id
             │       │        └─ pattern 匹配限定 pile_ID_{pile_id}_*.json
             │       └─ 未命中 → 垛型未知 → pile_id=1（默认）→ 遍历全部 pattern 表
             └─ 否/解析失败 → actualSpec="未识别"，actualQuantity 强制 0
```

---

## 4. 检测配置文件详解

### 4.1 `core/config/pile_config.json` —— 垛型模板

```json
{"piles": [{"id": 1, "name": "3*10", "layers": [{"index": 1, "count": 10}, ...]}, ...]}
```

| 字段 | 含义 |
|---|---|
| `id` | 垛型编号（pile_id，1~5） |
| `name` | 垛型名，`层数*每层箱数`：`3*10`=3 层×10 箱；`4*7+2`=4 层×7 箱 + 1 层×2 箱 |
| `layers[].count` | 自上而下每层期望箱数（供下层模板补齐） |

五种垛型：`3*10`(30) / `5*8`(40) / `5*6`(30) / `4*7+2`(30) / `5*5`(25)。

**与储位的映射**不是坐标映射，而是**条码→垛型**：每个储位盘点时扫条码 → 6 位码查表 → 垛型 → pile_id。储位坐标（"排-列-层"）只用于机器人路径排序（见 5.4）。

### 4.2 `core/config/pile_ID_X_*.json` —— 顶层 pattern 匹配表

每个文件是 JSON 数组，每条 pattern：

```json
{
  "pattern_id": "double_l_8",
  "visible_count": 2,
  "match": {
    "width_ranges": [[0.4174, 0.5], [0.2852, 0.35]],
    "depth_ranges": [[9200, 11950], [14450, 16950]]
  },
  "result_ids": [0, 7]
}
```

| 字段 | 含义 |
|---|---|
| `pattern_id` | 命名 `{框型组合}_{箱数}`：`single_l_5`=1 个长框→5 箱；`double_s_5`=2 短框→5 箱；`longshort_4`=1 长 1 短→4 箱；`doubles_long_10`=1 长 2 短→10 箱。**末尾数字 = 最终计数**（代码 `re.findall(r'\d+', pid)[-1]`） |
| `visible_count` | 该 pattern 对应的 YOLO 可见检测框数（= width_ranges 数组长度） |
| `width_ranges[j]` | 第 j 个检测框（从左到右）的**归一化宽度区间**（框像素宽 / pile_roi 像素宽，无量纲 0~1） |
| `depth_ranges[j]` | 第 j 个检测框中心点的**深度区间（毫米）**（双目 SGBM 深度，工作距离 9.2~22m） |
| `result_ids` | 各框对应的储位列号（保留字段，主流程未消费） |

后缀约定：`_mir` = 镜像摆放（左右颠倒的同一种垛型）；`_t/_d/_e` = 同箱数不同深度位置的变体。

各文件规模：ID_1(3x10) 45 条 / ID_2(5x8) 20 条 / ID_3(5x6) 22 条 / ID_4(4x7+2) 31 条 / ID_5(5x5) 17 条。

---

## 5. 盘点任务编排算法

### 5.1 任务号生成

`_get_next_task_no`（[service.py:105](../services/api/inventory/service.py#L105)）：格式 `HS{YYYYMMDD}{NN}`（如 `HS2026062801`）。持久化计数器 `logs/task_no_counter.txt`（`日期:计数`，`fcntl.flock` 跨进程互斥），日期变更自动归零。另有 RCS 请求号 `TASK_` + 12 位十六进制（`logs/request_id_counter.txt`）。

### 5.2 任务生命周期

```
创建（前端勾选仓库/储区/位号 → start-inventory）
  │   全局并发互斥：内存 + task_state.json 双查，running/completed/partial 占用时 409
  ▼
execute_inventory_workflow (service.py:1435) 后台任务
  ├─ 初始化状态 → running → 写 task_state.json
  ├─ 预检：RCS TCP 探活 + 三台相机探活（离线 → failed，error_type=rcs|camera）
  ├─ 寻路排序 sort_bins_by_path（见 5.4）
  ├─ 逐 bin 主循环（每 bin 超时 300s）：
  │    ① 下发单 bin 给 RCS → 登记 rt_code → append 进 submitted_bins
  │    ② wait_for_robot_status("end")  等 AMR 到位回调
  │       超时无 END 且未取消 → 跳过该 bin（不发 continue，见 5.6）
  │    ③ 拍照（gateway 触发三相机脚本，重试 5 轮，只重试失败相机）
  │    ④ 推 Redis 单 bin 队列（触发 worker 检测，不等 continue）
  │    ⑤ 提前下发：先 submit 下一个 bin 存 pending → 给上一个 bin 发 continue 让车走
  │       → 下一轮直接消费 pending 等 END（AMR 移动与检测并行）
  ├─ 等 worker：轮询 worker_completed 集合计数 ≥ len(submitted_bins)
  ├─ 汇总：逐 bin 取回检测结果，与系统库存按 locationName 匹配
  │        bin_result = {actualQuantity, actualSpec, systemQuantity, difference=实际-系统, ...}
  ├─ 终态判定：全成功=completed / 全失败=failed / 混合=partial → 写 task_state.json + WebSocket 广播
  └─ 自动保存 Excel（有效状态=无效，防 gateway 重启丢数据；用户确认后再存"有效"版）
```

### 5.3 Redis 队列结构（"3 队列 + 2 集合"）

| Key | 类型 | 方向 | 内容 |
|---|---|---|---|
| `inventory:single_bin_queue` | List | gateway→worker | `{task_no, bin_location}`，worker BRPOP |
| `inventory:task:results:{task_no}` | List | worker→gateway | 检测结果（数量/品规/照片路径），gateway LREM 消费 |
| `inventory:pending_queue` | List | （已废弃） | 旧批量队列，仅保留兼容 |
| `inventory:task:rcs_completed:{task_no}` | Set | gateway 写 | 收到 RCS END 的 bin（进度上半段） |
| `inventory:task:worker_completed:{task_no}` | Set | worker 写 | 检测完成的 bin（进度下半段） |

任务结束 DEL 结果表；取消时同时清两个集合并从队列逐条滤出本任务条目（`flush_single_bin_queue_by_task`）。

### 5.4 寻路排序算法

`sort_bins_by_path`（[service.py:135](../services/api/inventory/service.py#L135)）：

1. bin 名解析为 `(row, col, layer)`（"排-列-层"）；
2. **加权距离**：`|Δrow|×1000 + |Δcol|×10 + |Δlayer|`（跨排代价远高于列/层移动）；
3. 从 row 最小的 bin 起，**贪心最近邻**逐个选下一个。

目的：机器人行走路径最优。

### 5.5 取消机制（秒级退出）

`cancel-inventory`（[router.py:1056](../services/api/inventory/router.py#L1056)）：

1. 清 task_state.json；运行中任务只置 `cancelled` 标志（工作流在多个检查点自然退出）；
2. 对未收到 END 的 bin 给 RCS 发 `continue`（让 AMR 离开垛位防锁死）；
3. **注入假 END** 到状态队列唤醒阻塞中的 `wait_for_robot_status`；
4. 清 worker 队列中本任务条目 + 两个 Redis 完成集合；
5. 终态任务取消 → 结果写"无效"Excel + 清内存；WebSocket 广播 `task_cancelled`。

### 5.6 超时与提前下发的协作逻辑

- **提前下发**：END 到达 → 拍照 → 推检测 → 先 submit 下一个 bin（存 `pending_next_bin`）→ 才给当前 bin 发 continue。AMR 在 worker 检测的数十秒里已在去下一垛位的路上；
- **超时不发 continue**：等 END 超 300s 时先倒查队列有无迟到 END；确认没有且未取消 → **直接跳过该 bin，不发 continue**（RCS 侧任务节点可能已清理，发了无意义）。

### 5.7 submitted_bins 机制

工作流内的局部列表，记录"已下发 RCS 且需要收集检测结果的 bin"。三个维护点：正常下发 append、消费提前下发的 pending 时 append（此处曾漏掉导致结果缺行，commit a7907a8 修复）、取消提前退出时 pop 最后一项。用途：worker 完成等待的计数上限 + 最终结果收集的遍历范围。

### 5.8 recount 重新盘点

前端勾选异常库位 → 生成独立任务号 `{taskNo}_R{随机}`（独立存储键，不受并发互斥限制）→ 走完整流程 → 完成后**只取 recount 集合内的结果覆盖原 inventoryItems** → 以 `merge:true` 把重盘结果按"储位名称"列**合并写回原任务号的 Excel**。

### 5.9 进度统计算法

`/progress` 接口（[router.py:293](../services/api/inventory/router.py#L293)）：

```
completed_count = max(rcs_completed 集合数, worker_completed 集合数)
                 （RCS END 到达即计入，worker 完成后覆盖；两者为 0 时回退内存状态计数）
progress = completed / total × 100%
```

前端 1s 轮询；差异统计中"异常项" = 数量不等 或 品规未识别 或 品规与系统不一致（人工校准过的豁免）。

### 5.10 小车交互时序图（含提前下发流水线）

```
Gateway               RCS / AMR              相机×3            Redis→Worker
  │                      │                     │                   │
  │ submit(bin_i) 单储位 │                     │                   │
  ├─────────────────────►│                     │                   │
  │◄──────── start 回调 ─┤ 车开始移动          │                   │
  │                      │    ……AMR 行走……     │                   │
  │◄──────── outbin 回调─┤ 到位出舱            │                   │
  │◄──────── end 回调 ───┤                     │                   │
  │  （END 入 deque + Event 唤醒等待方）        │                   │
  │                      │                     │                   │
  │ 触发拍照 ──────────────────────────────────►│                   │
  │                      │    3 脚本并发；失败相机重试，最多 5 轮    │
  │                      │                     │                   │
  │ push 单bin 队列 ──────────────────────────────────────────────►│
  │                      │                     │             条码+计数检测
  │                      │                     │             （数十秒，异步）
  │ submit(bin_i+1) ★提前下发（存 pending，不等检测完成）            │
  ├─────────────────────►│                     │                   │
  │ continue(bin_i) ★放行当前车离开垛位        │                   │
  ├─────────────────────►│                     │                   │
  │                      │   ……AMR 去 bin_i+1……│                   │
  │◄──────── end 回调(bin_i+1) ────────────────┤ 下一轮直接消费 pending
  │                      │                     │                   │
  │◄─ 检测结果 LPUSH results 队列（worker 完成即回，无需等 continue）┤
```

流水线收益：AMR 去下一个垛位的行走时间与 Worker 检测上一个垛位的时间**完全重叠**。

### 5.11 END 等待与超时分支图

```
wait_for_robot_status("end", timeout=300s)
        │
        ▼
   收到 END？ ──是──► 拍照 → 推检测队列 → 提前下发下一个 → continue → 循环
        │ 否（300s 到）
        ▼
   倒查队列：有迟到的 END？ ──有──► 当正常处理（走上图流程）
        │ 无
        ▼
   任务已取消？ ──是──► 给当前 rt_code 发 continue → 退出循环
        │ 否
        ▼
   ★跳过该 bin：不发 continue（RCS 侧任务节点可能已清理，发了无意义）
        → i+=1 → 处理下一个 bin
```

### 5.12 取消流程图（秒级退出）

```
用户点击取消 → POST /api/inventory/cancel-inventory
        │
        ├─► 清 task_state.json
        ├─► 内存任务置 cancelled（工作流在循环检查点自然退出）
        ├─► 对未收到 END 的 bin 发 continue（让车离开垛位，防锁死）
        ├─► 注入假 END → 唤醒阻塞中的 wait_for_robot_status（秒级退出）
        ├─► flush Redis 队列中本任务条目 + 清 rcs/worker 两个完成集合
        ├─► WebSocket 广播 task_cancelled（全部前端弹窗）
        └─► 若已是终态：结果写"无效" Excel + 清内存
```

### 5.13 任务与储位状态机

```
【任务级】  init ──► running ──┬──► completed   全部 bin 成功
                              ├──► partial     部分成功
                              ├──► failed      全部失败（error_type=rcs/camera/other）
                              └──► cancelled   运行中取消
            completed/partial ──用户确认保存──► confirmed（写"有效"Excel，清状态文件）
            终态后取消 ──► 写"无效"Excel + 清内存

【储位级】  pending ──► running ──┬──► completed  检测成功
                                 └──► failed     检测异常（数量-1）
            超时跳过的 bin 停在 running、无检测结果 → 汇总时按失败呈现

【持久化】  output/task_state.json 跟踪任务状态；
            gateway 重启 → on_server_startup 清掉一切非 confirmed/cancelled
            记录（中断任务即放弃，回到干净态）
```

### 5.14 重试与容错策略总览

| 环节 | 容错策略 | 位置 |
|---|---|---|
| RCS HTTP（submit/continue） | 失败重试 3 次，退避 (n+1)×2s；业务失败（success=false）不重试 | service.py |
| 等 AMR 到位 END | 300s 超时 → 倒查迟到 END → 跳过该 bin 不发 continue | service.py:1610 |
| 相机拍照 | 失败相机重试最多 5 轮；先 ping 探活；任一相机成功即通过（允许 partial） | service.py:800 |
| WMS 库存拉取 | 重试 2 次，间隔 60s；失败保留旧 bins_data.xlsx | daily_task.sh |
| Worker 检测异常 | 不重推，直接写 status=异常、数量 -1 兜底 | inventory_worker.py:99 |
| Redis 连接失败 | 30s 内不重试（防雪崩） | redis_queue.py:24 |
| 条码识别失败 | actualSpec=未识别、数量强制 0 | detection_runner.py:139 |
| 垛型未知 | pile_id=1 兜底，pattern 遍历全部表 | config.py:195 |
| pattern 未命中 | 回落 YOLO 计数（过滤后框数） | stack_processor.py |
| gateway 重启 | 中断任务清除；已保存结果从"有效"Excel 恢复 | task_state.py / router.py |
| WebSocket 掉线 | 前端 30s 轮询 running-task 兜底 | App.tsx |

---

## 6. 结果回写与报表生成

### 6.1 update-bins-data 匹配算法（库存回写）

`/api/inventory/update-bins-data`（[router.py:925-993](../services/api/inventory/router.py#L925-L993)）：

1. 读 `shared/data/烟箱信息汇总完整版.xlsx` 构建 **品名→品规代码** 映射表；
2. 待更新数据按 `locationName`（储位名称）组织：数量 = actualQuantity、品名 = actualSpec（人工校准值优先）、品规代码 = 查表；
3. 写回 `services/sim/lms/bins_data.xlsx`：遍历数据行，**按 E 列（储位名称）字符串相等匹配**，命中则更新 **H 列（数量）**、**J 列（品规名称）**、**I 列（品规代码）**。

该文件同时是任务创建时的库存数据源 → 本地库存闭环（盘后库存立即生效于下次任务）。

### 6.2 Excel 报表

`output/history_data/{taskNo}.xlsx`（[excel_writer.py](../services/api/shared/excel_writer.py)），单 sheet"盘点结果"，16 列：任务编号 / 序号 / 下发时间 / 操作员 / 品规名称(系统) / 储位名称 / 实际品规 / 库存数量(系统) / 实际数量 / **差异** / 修改记录 / 有效状态 / 照片1-4 路径。

**差异列判定顺序**：实际品规非空且≠系统品规且≠"未识别" → "品规不一致"；="未识别" → "品规不一致"；否则数量差≠0 → 数字差值；否则 "一致"。

**有效状态**："有效"= 用户确认保存；"无效"= 自动保存/取消（gateway 重启后 `/results` 按有效 Excel 恢复）。

---

## 7. RCS 机器人交互协议

公共：headers `X-App-Id/X-Sign/X-Timestamp/X-LR-REQUEST-ID`；失败重试 3 次（退避 (n+1)×2s）；业务失败（success=false）不重试。

| 动作 | is_sim=true（本地 sim_rcs_server:4001） | is_sim=false（真实 RCS 10.16.82.90:443） |
|---|---|---|
| 下发 submit | `/api/robot/controller/task/submit`，单 bin 的 targetRoute | 同 URL，body 增加 `autoStart:1, interrupt:0, extra:{}...` |
| 继续 continue | `/task/extend/continue`（sim 侧实质 no-op） | 同 URL，`triggerType:"TASK"` —— **释放 AMR 离开垛位，流水线关键** |
| 回调上报 | 两者共用 `POST {gateway}/api/robot/reporter/task`；method ∈ start/outbin/**end** | sim 的 extra 是 JSON 字符串 list，real 是 dict |

sim 模式模拟逻辑：submit 立即返回 → start 回调 → sleep 15s 模拟行走 → outbin → end 回调。END 回调入 deque 并 set 事件唤醒 `wait_for_robot_status`。

---

## 8. 库存数据同步与每日维护

**库存数据全生命周期图：**

```
════════════ ① 每日定时拉取（daily_task.sh，04:00 触发）════════════
WMS 服务器                     bins_data.xlsx               sim LMS 进程
10.16.82.150:8082              （本地库存底座）               （内存）
     │                                │                         │
     │ GET /web/api/wh/reqWmsStock    │                         │
     │◄───────────────────────────────┤ fetch_wms_stock --once  │
     │ （timeout 30s）                │ （runuser 降权执行）     │
     │                                │                         │
     │ 200 JSON ──► 转11列格式 ──► temp写+rename 原子覆盖 ──────►│
     │ 失败 ──60s──► 重试（共2次）──仍失败──► 保留旧文件 + WARN   │
     │ is_sim=true ──► 只打日志不写文件                          │
     │                                │                         │
     │                    重启 leafdepot-lms ───────────────────►│ 启动时一次性
     │                                │                         │ 重载进内存 ★

════════════ ② 任务创建时读取 ════════════
前端 InventoryStart ──GET /lms/getLmsBin?useLocal=true──► Gateway
     └─► useLocal=true 或 LMS 不可用 → 直接读 bins_data.xlsx（本地兜底）

════════════ ③ 盘点完成后回写（本地闭环）════════════
前端确认保存 ──POST /update-bins-data──► 品名→品规代码（查烟箱信息表）
     └─► 按 E列（储位名称）精确匹配 → 更新 H数量 / I代码 / J品名
         → 下次任务创建用的就是盘后库存

★ 关键点：bins_data.xlsx 只在 LMS 重启时进内存；每日拉取是全量覆盖，
  会冲掉盘点回写但尚未同步回 WMS 的修改 → 拉取安排在凌晨无人作业时段
```

`daily_task.sh`（项目根）由 `leafdepot-daily.timer` 每天 04:00 触发（systemd，`Persistent=true` 关机错过则开机补跑）：

`daily_task.sh`（项目根）由 `leafdepot-daily.timer` 每天 04:00 触发（systemd，`Persistent=true` 关机补跑）：

```
① 拉取 WMS 库存（runuser 降权执行 services/sim/lms/fetch_wms_stock.py --once，
   重试 2 次间隔 60s；从 http://10.16.82.150:8082/web/api/wh/reqWmsStock 拉取 → 原子写
   bins_data.xlsx；失败保留旧文件）
② 重启 5 个服务（gateway/worker/lms/rcs/web）
   → sim LMS 重启时把新 bins_data.xlsx 重载进内存
   → log_wrapper.sh 为每个服务生成当日新日志文件（logs/<svc>_YYYYMMDD.log）
③ 逐服务核对（is-active / PID / 端口监听 / HTTP 探活 / 当日日志存在），写
   logs/daily_task_YYYYMMDD.log
```

三功能闭环：**定时重启 = 每日新日志 = 每日新数据的生效条件**（LMS 内存重载）。

---

## 9. 关键参数速查表

| 参数 | 值 | 位置 | 作用 |
|---|---|---|---|
| YOLO conf | 0.65 | factory.py | 目标置信度阈值 |
| 层分裂阈值 | 0.6×avg_h（<3 箱时 0.8） | layer_clustering.py | 中心 y 间距超此值开新层 |
| 层 ROI 外扩 | 0.1×avg_h | layer_clustering.py | 层边界上下 padding |
| 顶层高度过滤 | 0.05×最大箱高 | full_layer_detector.py | 剔除误检小框 |
| 原 coverage/cv_gap 阈值 | 0.9 / 0.4 | full_layer_detector.py | （当前恒满层，仅保留参数） |
| 深度误检上限 | 21950 mm | stack_processor.py | 顶层箱深度超限剔除 |
| 深度采样 y 偏移 | +0.10 | stack_processor.py | 深度图与可见光 FOV 垂直错位补偿（x 同相机天然对齐） |
| 深度采样窗口 | 5×5 邻域，±500mm | depth_processor.py | 中位数过滤取均值 |
| 焦距/基线 | 6400px / 120mm | depth_calculator.py | depth = 768000 / disparity |
| 每 bin 超时 | 300 s | service.py | 等 AMR 到位 END |
| 拍照重试 | 5 轮 | service.py | 只重试失败相机 |
| 寻路权重 | row×1000, col×10, layer×1 | service.py | 跨排代价最高 |

---

## 10. 当前未启用/遗留逻辑说明

以下代码存在于代码库但**当前主流程不生效**（阅读代码时注意区分）：

| 项 | 位置 | 状态 |
|---|---|---|
| 非满层/单层处理器 | stack_processor.py | 满层判断恒 full 后不可达（单层处理器还有 dict/int 返回值不匹配的潜在 bug，因死分支未暴露） |
| `remove_fake_top_layer` 伪顶层删除 | layer_filter.py | factory 中注释禁用（宽度判断逻辑有 bug 会误删真顶层） |
| `filter_rear_boxes_if_multilayer` 前排过滤 | layer_filter.py | 未启用 |
| YOLO `top` 类别 | pile+box.yaml | 主流程未用 |
| `result_ids` / `visible_count` 字段 | pile_ID_*.json | 匹配时仅用数组长度，字段值未消费 |
| `POST /lms/setTaskResults` | lms/router.py | 已实现，前端无调用点（本地提交由 update-bins-data 完成） |
| `abort_inventory_task` RCS 取消 | service.py | 已实现未接线（等 RCS 提供 cancel API） |
| 旧批量队列 `inventory:pending_queue` | redis_queue.py | 已被单 bin 队列取代 |
| `services/vision/box_count_service.py` | — | 旧平行检测路径，主链路不经过 |
| `core/detection/depth/calculator.py` | — | 旧副本（f=11000/B=60），未被导出使用 |
| `scripts/fetch_wms_stock.py` | scripts/ | 测试用原型（真代码在 services/sim/lms/） |
