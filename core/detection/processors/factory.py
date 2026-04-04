"""堆垛处理器工厂：根据满层判断结果自动选择对应的处理模块"""

import logging
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
from ultralytics import YOLO
import cv2
import numpy as np

logger = logging.getLogger(__name__)

from .full_layer_detector import (
    FullLayerDetector, 
    CoverageBasedDetector
)
from .stack_processor import (
    FullStackProcessor,
    TemplateBasedFullProcessor,
    PartialStackProcessor,
    TemplateBasedPartialProcessor,
    SingleLayerProcessor,
    TemplateBasedSingleLayerProcessor
)

# 导入核心算法模块
from core.detection.utils.yolo_utils import extract_yolo_detections
from core.detection.core.scene_prepare import prepare_logic
from core.detection.core.layer_filter import remove_fake_top_layer
from core.detection.core.layer_clustering import cluster_layers_with_box_roi
from core.detection.utils.pile_db import PileTypeDatabase
from core.detection.utils.path_utils import ensure_output_dir

# 导入可视化模块
from core.detection.visualization import prepare_scene
from core.detection.core.layer_clustering import (
    visualize_layers,
    visualize_layers_with_roi,
    visualize_layers_with_box_roi,
    draw_layers_with_box_roi
)

# 导入深度处理模块
from core.detection.depth import DepthCalculator, DepthProcessor


class StackProcessorFactory:
    """
    堆垛处理器工厂
    
    工作流程：
    1. 使用满层判断模块判断堆垛状态（满层/非满层/单层）
    2. 根据判断结果选择对应的处理模块
       - 满层：使用满层处理器
       - 非满层：使用非满层处理器
       - 单层：使用单层处理器
    3. 执行处理并返回结果
    """
    
    def __init__(self,
                 detector: Optional[FullLayerDetector] = None,
                 full_processor: Optional[FullStackProcessor] = None,
                 partial_processor: Optional[PartialStackProcessor] = None,
                 single_layer_processor: Optional[SingleLayerProcessor] = None,
                 enable_debug: bool = True,
                 enable_visualization: bool = False,
                 model_path: Optional[Union[str, Path]] = None,
                 pile_config_path: Optional[Union[str, Path]] = None,
                 confidence_threshold: float = 0.65,
                 output_dir: Optional[Union[str, Path]] = None):
        """
        :param detector: 满层判断器（可选，默认使用 CoverageBasedDetector）
        :param full_processor: 满层处理器（可选，默认使用 TemplateBasedFullProcessor）
        :param partial_processor: 非满层处理器（可选，默认使用 TemplateBasedPartialProcessor）
        :param single_layer_processor: 单层处理器（可选，默认使用 TemplateBasedSingleLayerProcessor）
        :param enable_debug: 是否启用调试输出（打印日志）
        :param enable_visualization: 是否启用可视化（保存效果图到output目录）
        :param model_path: YOLO模型路径（可选，用于count方法）
        :param pile_config_path: 堆垛配置路径（可选，用于count方法）
        :param confidence_threshold: 置信度阈值（默认0.65）
        :param output_dir: 可视化输出目录（可选，默认使用 core/detection/output）
        """
        self.detector = detector or CoverageBasedDetector(enable_debug=enable_debug)
        self.enable_debug = enable_debug
        self.enable_visualization = enable_visualization
        self.confidence_threshold = confidence_threshold
        self.output_dir = output_dir
        
        # 初始化YOLO模型和pile数据库（如果提供了路径）
        self.model = None
        self.pile_db = None
        
        # 深度图数据（numpy数组）
        self.depth_image = None
        # 深度图路径（用于深度处理）
        self.depth_image_path_for_processing = None
        # 深度矩阵CSV路径（缓存文件）
        self.depth_matrix_csv_path = None
        # 原始图路径和目录（用于保存raw.jpg和depth.jpg）
        self.original_image_path = None
        self.original_image_dir = None
        # 深度计算器和处理器
        self.depth_calculator = DepthCalculator(enable_debug=enable_debug)
        self.depth_processor = DepthProcessor(enable_debug=enable_debug)
        
        # 创建处理器，传递深度计算器
        self.full_processor = full_processor or TemplateBasedFullProcessor(enable_debug=enable_debug)
        # 创建非满层处理器，传递深度计算器
        if partial_processor is None:
            self.partial_processor = TemplateBasedPartialProcessor(
                enable_debug=enable_debug,
                depth_calculator=self.depth_calculator
            )
        else:
            self.partial_processor = partial_processor
        self.single_layer_processor = single_layer_processor or TemplateBasedSingleLayerProcessor(enable_debug=enable_debug)
        
        if model_path is not None:
            self._init_model(model_path)
        if pile_config_path is not None:
            self._init_pile_db(pile_config_path)
    
    def _init_model(self, model_path: Union[str, Path]):
        """初始化YOLO模型"""
        if self.model is None:
            model_path = Path(model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"YOLO模型文件不存在: {model_path}")
            if self.enable_debug:
                print(f"加载YOLO模型: {model_path}")
            self.model = YOLO(str(model_path))
    
    def _init_pile_db(self, pile_config_path: Union[str, Path]):
        """初始化堆垛配置数据库"""
        if self.pile_db is None:
            pile_config_path = Path(pile_config_path)
            if not pile_config_path.exists():
                raise FileNotFoundError(f"堆垛配置文件不存在: {pile_config_path}")
            if self.enable_debug:
                print(f"加载堆垛配置: {pile_config_path}")
            self.pile_db = PileTypeDatabase(str(pile_config_path))
    
    def count(self, image_path: Union[str, Path], pile_id: int, 
              depth_image_path: Optional[Union[str, Path]] = None) -> int:
        """
        算法统一入口：从图片路径和pile_id计算总箱数
        
        :param image_path: 图片路径（RGB图片）
        :param pile_id: 堆垛ID
        :param depth_image_path: 深度图路径（可选，预留参数）
        :return: 总箱数（烟箱数）
        """
        # 确保 logging 配置了 handler（避免子模块 logger 无输出）
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO)

        logger.info(f"[Detection] ===== count_boxes 被调用 =====")
        logger.info(f"[Detection] image_path={image_path}, pile_id={pile_id}, depth_image_path={depth_image_path}")

        # 验证和初始化
        image_path = self._validate_inputs(image_path, depth_image_path)
        vis_output_dir = self._prepare_visualization_dir()
        
        # Step 0: 旋转原图（在YOLO检测之前）
        rotated_image_path = self._rotate_and_save_image(image_path, vis_output_dir)
        # 使用旋转后的图像进行后续处理
        processing_image_path = rotated_image_path if rotated_image_path else image_path

        # Step 1: YOLO检测（使用旋转后的图像）
        detections = self._run_yolo_detection(processing_image_path)
        if not detections:
            logger.warning("[Detection] YOLO未检测到任何目标")
            return 0

        logger.info(f"[Detection] YOLO检测到 {len(detections)} 个目标, 类别: {set(d.get('cls') for d in detections)}")

        # Step 1.5: 深度图处理（在 pile 检测之前，以便生成 depth_color.jpg）
        self._process_depth_image(processing_image_path, vis_output_dir)

        # Step 2: 场景准备（使用旋转后的图像）
        prepared = self._prepare_scene(detections, processing_image_path, vis_output_dir)
        if not prepared:
            logger.warning("[Detection] 场景准备失败，未检测到有效pile区域")
            return 0
        boxes, pile_roi = prepared["boxes"], prepared["pile_roi"]
        logger.info(f"[Detection] 场景准备成功: pile_roi={pile_roi}, pile内box数={len(boxes)}")

        # 添加图像尺寸信息到pile_roi（用于深度处理，使用旋转后的图像）
        img = cv2.imread(str(processing_image_path))
        if img is not None:
            pile_roi["image_width"] = img.shape[1]
            pile_roi["image_height"] = img.shape[0]

        # Step 3: 分层聚类（使用旋转后的图像）
        layers = self._cluster_layers(boxes, pile_roi, processing_image_path, vis_output_dir)
        if not layers:
            logger.warning("[Detection] 分层聚类失败，未提取到有效层")
            return 0

        logger.info(f"[Detection] 分层聚类完成: 层数={len(layers)}, 每层箱数={[len(l.get('boxes',[])) for l in layers]}")

        # Step 4: 处理层（去误层、重新索引）
        layers = self._process_layers(layers)

        # Step 5: 获取模板配置
        template_layers = self._get_template_config(pile_id, layers)
        pile_name = self.pile_db.get_pile(pile_id).get("name", str(pile_id)) if self.pile_db else str(pile_id)
        logger.info(f"[Detection] 使用垛型: pile_id={pile_id}({pile_name}), 期望层配置={template_layers}")

        # 可视化：处理后的分层结果（使用旋转后的图像）
        if self.enable_visualization:
            self._save_layer_visualization(processing_image_path, boxes, pile_roi, layers, vis_output_dir)

        # Step 6: 处理堆垛（满层判断和计数）
        # 传递原始YOLO检测结果，供单层处理器提取top类使用
        total_count = self.process(layers, template_layers, pile_roi,
                                  yolo_detections=detections,
                                  image_path=image_path,
                                  output_dir=vis_output_dir)

        logger.info(f"[Detection] ===== 识别结果汇总 =====")
        logger.info(f"[Detection] 最终计数: {total_count} 箱")
        logger.info(f"[Detection] 垛型: {pile_name}(pile_id={pile_id}), 期望层数={len(template_layers)}, 实际层数={len(layers)}")

        # 可视化：最终结果（使用旋转后的图像）
        if self.enable_visualization:
            self._save_final_visualization(processing_image_path, pile_roi, layers, vis_output_dir)
        
        return total_count
    
    def _find_image_files(self, input_path: Union[str, Path]) -> Tuple[Optional[Path], Optional[Path]]:
        """
        查找main.jpeg和fourth.jpeg文件
        
        :param input_path: 输入路径（可以是目录或文件路径）
        :return: (main_image_path, depth_image_path) 元组
        """
        input_path = Path(input_path)
        
        # 确定搜索目录
        if input_path.is_dir():
            search_dir = input_path
        elif input_path.is_file():
            search_dir = input_path.parent
        else:
            raise FileNotFoundError(f"输入路径不存在: {input_path}")
        
        # 查找main.jpeg和fourth.jpeg
        main_image_path = search_dir / "main.jpeg"
        depth_image_path = search_dir / "fourth.jpeg"
        
        # 如果main.jpeg不存在，尝试其他可能的扩展名
        if not main_image_path.exists():
            for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
                alt_path = search_dir / f"main{ext}"
                if alt_path.exists():
                    main_image_path = alt_path
                    break
        
        # 如果fourth.jpeg不存在，尝试其他可能的扩展名
        if not depth_image_path.exists():
            for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
                alt_path = search_dir / f"fourth{ext}"
                if alt_path.exists():
                    depth_image_path = alt_path
                    break
        
        return main_image_path if main_image_path.exists() else None, \
               depth_image_path if depth_image_path.exists() else None
    
    def _validate_inputs(self, image_path: Union[str, Path], 
                        depth_image_path: Optional[Union[str, Path]]) -> Path:
        """
        验证输入并初始化资源
        新的逻辑：自动查找main.jpeg作为原始图，fourth.jpeg作为深度图
        """
        input_path = Path(image_path)
        if not input_path.exists():
            raise FileNotFoundError(f"输入路径不存在: {input_path}")
        
        # 查找main.jpeg和fourth.jpeg
        main_image_path, found_depth_image_path = self._find_image_files(input_path)
        
        # 如果找到了main.jpeg，使用它作为原始图
        if main_image_path is not None:
            image_path = main_image_path
            if self.enable_debug:
                print(f"📸 找到原始图: {main_image_path}")
        else:
            # 如果没有找到main.jpeg，使用输入路径（向后兼容）
            if input_path.is_file():
                image_path = input_path
                if self.enable_debug:
                    print(f"⚠️  未找到main.jpeg，使用输入路径作为原始图: {image_path}")
            else:
                raise FileNotFoundError(f"未找到main.jpeg文件，且输入路径不是文件: {input_path}")
        
        # 验证原始图文件存在
        if not image_path.exists():
            raise FileNotFoundError(f"原始图文件不存在: {image_path}")
        
        # 保存原始图路径（用于后续保存raw.jpg和depth.jpg）
        self.original_image_path = image_path
        self.original_image_dir = str(image_path.parent)
        
        # 处理深度图：优先使用找到的fourth.jpeg，其次使用传入的depth_image_path参数
        if depth_image_path is None:
            depth_image_path = found_depth_image_path
        else:
            depth_image_path = Path(depth_image_path)
        
        # 加载深度图
        if depth_image_path is None or not depth_image_path.exists():
            if self.enable_debug:
                if depth_image_path is None:
                    print(f"⚠️  未找到fourth.jpeg文件，忽略深度图")
                else:
                    print(f"⚠️  深度图文件不存在: {depth_image_path}，忽略深度图")
            self.depth_image = None
            self.depth_image_path_for_processing = None
        else:
            if self.enable_debug:
                print(f"📊 加载深度图: {depth_image_path}")
            try:
                # 尝试使用cv2加载深度图（支持常见图像格式）
                depth_img = cv2.imread(str(depth_image_path), cv2.IMREAD_UNCHANGED)
                if depth_img is None:
                    if self.enable_debug:
                        print(f"⚠️  无法读取深度图: {depth_image_path}，忽略深度图")
                    self.depth_image = None
                    self.depth_image_path_for_processing = None
                else:
                    # 如果是彩色图像，转换为灰度图
                    if len(depth_img.shape) == 3:
                        depth_img = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)
                    self.depth_image = depth_img
                    if self.enable_debug:
                        print(f"✅ 深度图加载成功，尺寸: {self.depth_image.shape}")
                    
                    # 保存深度图路径，用于后续处理
                    self.depth_image_path_for_processing = depth_image_path
            except Exception as e:
                if self.enable_debug:
                    print(f"⚠️  加载深度图时出错: {e}，忽略深度图")
                self.depth_image = None
                self.depth_image_path_for_processing = None
        
        # 初始化模型和数据库（如果未初始化）
        if self.model is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            default_model_path = project_root / "shared" / "models" / "yolo" / "best.pt"
            self._init_model(default_model_path)
        
        if self.pile_db is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            default_config_path = project_root / "core" / "config" / "pile_config.json"
            self._init_pile_db(default_config_path)
        
        return image_path
    
    def _prepare_visualization_dir(self) -> Optional[Path]:
        """准备可视化输出目录"""
        if not self.enable_visualization:
            return None
        
        if self.output_dir:
            vis_output_dir = ensure_output_dir(self.output_dir)
        else:
            vis_output_dir = ensure_output_dir()
        
        if self.enable_debug:
            print(f"📁 可视化输出目录: {vis_output_dir}")
        
        return vis_output_dir
    
    def _run_yolo_detection(self, image_path: Path) -> List[Dict]:
        """运行YOLO检测"""
        if self.enable_debug:
            print(f"开始检测图片: {image_path}")
        
        results = self.model.predict(
            source=str(image_path),
            save=False,
            conf=self.confidence_threshold
        )
        detections = extract_yolo_detections(results)
        
        # 在debug模式下保存YOLO检测结果图
        if self.enable_debug and results:
            try:
                # 准备输出目录
                if self.output_dir:
                    output_dir = ensure_output_dir(self.output_dir)
                else:
                    output_dir = ensure_output_dir()
                
                # 确保image_path是Path对象
                image_path_obj = Path(image_path) if not isinstance(image_path, Path) else image_path
                image_stem = image_path_obj.stem
                yolo_output_path = output_dir / f"{image_stem}_yolo_detection.jpg"
                
                # 使用YOLO的plot方法生成带检测框的图像
                annotated_img = results[0].plot()
                cv2.imwrite(str(yolo_output_path), annotated_img)
                
                print(f"💾 已保存YOLO检测结果图: {yolo_output_path}")
                print(f"   检测到 {len(detections)} 个对象")
            except Exception as e:
                if self.enable_debug:
                    print(f"⚠️  保存YOLO检测结果图时出错: {e}")
                    import traceback
                    traceback.print_exc()
        
        if not detections and self.enable_debug:
            print("⚠️  未检测到任何对象")
        
        return detections
    
    def _prepare_scene(self, detections: List[Dict], image_path: Path,
                      vis_output_dir: Optional[Path]) -> Optional[Dict]:
        """场景准备"""
        prepared = prepare_logic(detections, conf_thr=self.confidence_threshold)
        
        if prepared is None:
            if self.enable_debug:
                print("⚠️  未检测到pile或pile内没有box")
            return None
        
        # 可视化：场景准备结果
        if self.enable_visualization:
            image_path_obj = Path(image_path) if isinstance(image_path, str) else image_path
            image_name = image_path_obj.stem
            prepare_scene(
                image_path=str(image_path_obj),
                yolo_output=detections,
                conf_thr=self.confidence_threshold,
                save_path=f"{image_name}_step1_scene_prepare.jpg",
                show=False,
                output_dir=vis_output_dir
            )
            if self.enable_debug:
                print(f"💾 已保存场景准备结果图")
        
        return prepared
    
    def _cluster_layers(self, boxes: List[Dict], pile_roi: Dict[str, float],
                       image_path: Union[str, Path], vis_output_dir: Optional[Path]) -> List[Dict]:
        """分层聚类"""
        layer_result = cluster_layers_with_box_roi(boxes, pile_roi)
        layers = layer_result.get("layers", [])
        
        if not layers:
            if self.enable_debug:
                print("⚠️  无法进行分层聚类")
            return []
        
        # 可视化：分层聚类结果
        if self.enable_visualization:
            image_path_obj = Path(image_path) if isinstance(image_path, str) else image_path
            image_name = image_path_obj.stem
            visualize_layers(
                image_path=str(image_path_obj),
                boxes=boxes,
                pile_roi=pile_roi,
                save_path=f"{image_name}_step2_layers.jpg",
                gap_ratio=0.6,
                show=False,
                output_dir=vis_output_dir
            )
            visualize_layers_with_roi(
                image_path=str(image_path_obj),
                boxes=boxes,
                pile_roi=pile_roi,
                save_path=f"{image_name}_step2_layers_roi.jpg",
                gap_ratio=0.6,
                padding_ratio=0.1,
                show=False,
                output_dir=vis_output_dir
            )
            if self.enable_debug:
                print(f"💾 已保存分层聚类结果图")
        
        return layers
    
    def _process_layers(self, layers: List[Dict]) -> List[Dict]:
        """处理层：去除误层并重新索引"""
        # 去除误层
        layers = remove_fake_top_layer(layers)
        
        # 重新索引层（最上层为1）
        layers = sorted(layers, key=lambda l: l["avg_y"])
        for i, layer in enumerate(layers, 1):
            layer["index"] = i
        
        return layers
    
    def _get_template_config(self, pile_id: int, layers: List[Dict]) -> List[int]:
        """获取模板配置"""
        template_layers = self.pile_db.get_template_layers(pile_id)
        
        if not template_layers:
            # 如果没有配置，使用检测到的层数，每层使用检测到的箱数
            template_layers = [len(layer["boxes"]) for layer in layers]
            if self.enable_debug:
                print(f"⚠️  未找到pile_id={pile_id}的配置，使用检测结果作为模板")
        
        return template_layers
    
    def _save_layer_visualization(self, image_path: Union[str, Path], boxes: List[Dict],
                                  pile_roi: Dict[str, float], layers: List[Dict],
                                  vis_output_dir: Path):
        """保存分层处理后的可视化结果"""
        image_path_obj = Path(image_path) if isinstance(image_path, str) else image_path
        image_name = image_path_obj.stem
        visualize_layers_with_box_roi(
            image_path=str(image_path_obj),
            boxes=boxes,
            pile_roi=pile_roi,
            save_path=f"{image_name}_step3_layers_boxes.jpg",
            show=False,
            target_layers=1,
            alpha=0.3,
            box_thickness=5,
            output_dir=vis_output_dir
        )
        if self.enable_debug:
            print(f"💾 已保存分层box ROI结果图")
    
    def _save_final_visualization(self, image_path: Union[str, Path], pile_roi: Dict[str, float],
                                  layers: List[Dict], vis_output_dir: Path):
        """保存最终结果的可视化"""
        image_path_obj = Path(image_path) if isinstance(image_path, str) else image_path
        image_name = image_path_obj.stem
        layer_result_for_vis = {
            "layer_count": len(layers),
            "layers": layers
        }
        draw_layers_with_box_roi(
            img_path=str(image_path_obj),
            pile_roi=pile_roi,
            layer_result=layer_result_for_vis,
            save_path=f"{image_name}_step4_final_result.jpg",
            target_layers=1,
            layer_color=(0, 0, 255),  # 红色阴影
            alpha=0.35,
            show=False,
            output_dir=vis_output_dir
        )
        if self.enable_debug:
            print(f"💾 已保存最终结果图")
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                pile_roi: Dict[str, float], 
                yolo_detections: Optional[List[Dict]] = None,
                image_path: Optional[Union[str, Path]] = None,
                output_dir: Optional[Union[str, Path]] = None) -> int:
        """
        处理堆垛：自动判断满层并选择对应处理模块
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param pile_roi: 堆垛ROI区域
        :param yolo_detections: 原始YOLO检测结果（可选，用于单层场景提取top类）
        :param image_path: 图像路径（可选，用于生成深度矩阵缓存）
        :param output_dir: 输出目录（可选，用于保存深度矩阵缓存）
        :return: 总箱数（烟箱数）
        """
        # Step 1: 满层判断
        detection_result = self.detector.detect(layers, template_layers, pile_roi, depth_image=self.depth_image)
        # 将pile_roi添加到detection_result中，供后续处理使用
        detection_result["pile_roi"] = pile_roi
        # 将原始YOLO检测结果添加到detection_result中，供单层处理器使用
        if yolo_detections is not None:
            detection_result["yolo_detections"] = yolo_detections
        status = detection_result.get("status", "partial")  # 获取状态：'full', 'partial', 'single_layer'
        is_full = detection_result.get("full", False)  # 向后兼容
        reason = detection_result.get("reason", "")
        top_layer = detection_result.get("top_layer") or {}

        # 深度矩阵缓存已经在满层判断之前生成（在count方法的Step 1.5中）
        # 这里只需要将深度数据传递给检测结果
        if self.depth_matrix_csv_path:
            detection_result["depth_matrix_csv_path"] = self.depth_matrix_csv_path

        # 打印满层判断详情
        status_emoji = {"full": "✅ 满层", "partial": "❌ 非满层", "single_layer": "🔵 单层"}
        status_text = status_emoji.get(status, "❓ 未知")
        expected = top_layer.get("expected", "?")
        observed = top_layer.get("observed", "?")
        logger.info(f"[Detection] 满层判断: {status_text}, 依据={reason}, 顶层期望={expected}箱, 顶层实际={observed}箱")
        if status == "partial":
            metrics = detection_result.get("metrics", {})
            logger.info(f"[Detection] 覆盖率指标: coverage={metrics.get('coverage', 0):.3f}, cv_gap={metrics.get('cv_gap', 0):.3f}, cv_width={metrics.get('cv_width', 0):.3f}")

        # Step 2: 根据判断结果选择处理模块
        if status == "single_layer":
            logger.info("[Detection] 进入单层处理模块")
            processing_result = self.single_layer_processor.process(
                layers, template_layers, detection_result, depth_image=self.depth_image
            )
        elif status == "full" or is_full:
            logger.info("[Detection] 进入满层处理模块")
            processing_result = self.full_processor.process(
                layers, template_layers, detection_result,
                depth_image=self.depth_image,
                depth_matrix_csv_path=self.depth_matrix_csv_path
            )
        else:  # status == "partial"
            logger.info("[Detection] 进入非满层处理模块")
            # 非满层处理时，传递图像路径和输出目录，让非满层处理器自己处理深度图
            processing_result = self.partial_processor.process(
                layers, template_layers, detection_result,
                depth_image=self.depth_image,
                depth_matrix_csv_path=self.depth_matrix_csv_path,
                image_path=image_path,
                output_dir=output_dir
            )

        # Step 3: 返回总箱数
        total_count = processing_result["total"]
        logger.info(f"[Detection] 处理模块返回: total={total_count}, status={status}")
        
        return total_count
    
    def _rotate_and_save_image(self, image_path: Union[str, Path],
                               output_dir: Optional[Union[str, Path]]) -> Optional[str]:
        """
        旋转原图并保存
        - debug模式下：保存到output目录，命名为 {原图名}_rotated.{扩展名}
        - 非debug模式下：保存到原图路径，命名为 raw.jpg 和 {原图名}_rotated.{扩展名}
        
        :param image_path: 输入图像路径
        :param output_dir: 输出目录（用于debug模式）
        :return: 旋转后的图像路径（如果成功），否则返回None
        """
        try:
            image_path = Path(image_path)
            image_stem = image_path.stem
            image_suffix = image_path.suffix
            
            # 确定原始图目录
            if hasattr(self, 'original_image_dir') and self.original_image_dir:
                original_dir = Path(self.original_image_dir)
            else:
                original_dir = image_path.parent
            
            # 确定旋转后的图像保存路径
            if self.enable_debug and output_dir is not None:
                # debug模式：保存到output目录
                output_dir = Path(output_dir)
                rotated_filename = f"{image_stem}_rotated{image_suffix}"
                rotated_path = output_dir / rotated_filename
            else:
                # 非debug模式：保存到原图路径，命名为 raw.jpg
                rotated_path = original_dir / "raw.jpg"
            
            # 使用深度计算器的旋转功能
            rotated_path_str = self.depth_calculator.rotate_image(
                str(image_path),
                rotation_angle=90,
                output_path=str(rotated_path),
                overwrite=True  # 允许覆盖
            )
            
            # 无论debug模式与否，都要保存 {原图名}_rotated.{扩展名} 到原始路径
            rotated_filename = f"{image_stem}_rotated{image_suffix}"
            rotated_path_original = original_dir / rotated_filename
            # 复制旋转后的图像到原始路径
            import shutil
            shutil.copy2(rotated_path_str, str(rotated_path_original))
            if self.enable_debug:
                print(f"✅ 已保存旋转图到原始路径: {rotated_path_original}")
            
            # 非debug模式下，还要保存 raw.jpg 到原始路径
            if not (self.enable_debug and output_dir is not None):
                raw_path = original_dir / "raw.jpg"
                if rotated_path != raw_path:  # 如果路径不同，才需要复制
                    shutil.copy2(rotated_path_str, str(raw_path))
                    if self.enable_debug:
                        print(f"✅ 已保存raw.jpg到原始路径: {raw_path}")
            
            if self.enable_debug:
                print(f"✅ 原图已旋转并保存至: {rotated_path_str}")
            else:
                print(f"✅ 原图已旋转并保存至: {rotated_path_str}")
            
            return rotated_path_str
            
        except Exception as e:
            if self.enable_debug:
                print(f"⚠️  旋转原图时出错: {e}")
            return None
    
    def _process_depth_image(self, image_path: Union[str, Path],
                             output_dir: Optional[Union[str, Path]]):
        """
        处理深度图：在满层判断之前生成深度矩阵缓存
        
        :param image_path: 原始图像路径（RGB图像，已旋转）
        :param output_dir: 输出目录（用于保存视差图可视化）
        """
        try:
            if self.enable_debug:
                print("\n" + "=" * 50)
                print("📊 开始处理深度图（在满层判断之前）...")
                print(f"   图像路径: {image_path}")
                print(f"   输出目录: {output_dir}")
                print(f"   深度图路径: {self.depth_image_path_for_processing}")
                print(f"   depth_calculator存在: {self.depth_calculator is not None}")
            
            # 检查是否有深度图路径
            if self.depth_image_path_for_processing is None:
                if self.enable_debug:
                    print("ℹ️  未找到深度图路径（depth_image_path_for_processing为None），跳过深度处理")
                    print("   提示：请确保深度图文件存在，或通过depth_image_path参数传入深度图路径")
                return
            
            # 检查深度计算器是否存在
            if self.depth_calculator is None:
                if self.enable_debug:
                    print("⚠️  depth_calculator未初始化，跳过深度处理")
                return
            
            # 准备输出目录
            if output_dir is None:
                output_dir = Path(image_path).parent
            else:
                output_dir = Path(output_dir)
            
            # 在debug模式下，保存深度图旋转前后的版本（用于调试对比）
            depth_image_path = self.depth_image_path_for_processing
            if self.enable_debug:
                depth_stem = Path(depth_image_path).stem
                depth_suffix = Path(depth_image_path).suffix
                
                # 保存加载的原始深度图（旋转前）
                original_depth_path = output_dir / f"{depth_stem}_loaded_original{depth_suffix}"
                cv2.imwrite(str(original_depth_path), self.depth_image)
                print(f"💾 已保存加载的原始深度图（旋转前）: {original_depth_path}")
                
                # 保存旋转后的深度图（仅用于调试对比，不用于处理）
                rotated_depth_filename = f"{depth_stem}_rotated_for_debug{depth_suffix}"
                rotated_depth_path = output_dir / rotated_depth_filename
                
                rotated_depth_path_str = self.depth_calculator.rotate_image(
                    str(depth_image_path),
                    rotation_angle=90,
                    output_path=str(rotated_depth_path),
                    overwrite=False
                )
                print(f"💾 已保存旋转后的深度图（仅用于调试）: {rotated_depth_path_str}")
                print(f"   注意：实际处理时使用原始深度图，不旋转")
            
            # 准备深度缓存目录
            depth_cache_dir = output_dir / "depth_cache"
            depth_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 计算深度矩阵（只对深度图进行split和处理，不旋转）
            # 视差图可视化保存到主output目录
            debug_output_dir = str(output_dir) if (self.enable_debug and output_dir) else None
            if self.enable_debug:
                print(f"📁 深度缓存目录: {depth_cache_dir}")
                print(f"📁 视差图可视化目录: {debug_output_dir if debug_output_dir else '未设置'}")
                print(f"   处理流程：直接对原始深度图进行split，不旋转")
            
            # 使用原始深度图进行处理（不旋转，直接split）
            # 传递原图目录，用于在非debug模式下保存depth.jpg
            original_image_dir = self.original_image_dir if hasattr(self, 'original_image_dir') else None
            depth_array, csv_path = self.depth_calculator.process_stereo_image(
                str(depth_image_path),  # 使用原始深度图，不旋转
                str(depth_cache_dir),
                debug_output_dir=debug_output_dir,
                skip_rotation=True,  # 跳过旋转
                original_image_dir=original_image_dir  # 传递原图目录
            )
            
            # 保存深度矩阵CSV路径
            self.depth_matrix_csv_path = csv_path
            
            # 同时保存深度图数组供后续使用
            self.depth_image = depth_array
            
            if self.enable_debug:
                print(f"✅ 深度矩阵缓存已生成: {csv_path}")
                print("=" * 50 + "\n")
                
        except Exception as e:
            if self.enable_debug:
                print(f"⚠️  处理深度图时出错: {e}")
                print("继续处理，但不使用深度数据...")
                import traceback
                traceback.print_exc()
            self.depth_matrix_csv_path = None
            self.depth_image = None


def count_boxes(image_path: Union[str, Path], pile_id: int,
                depth_image_path: Optional[Union[str, Path]] = None,
                model_path: Optional[Union[str, Path]] = None,
                pile_config_path: Optional[Union[str, Path]] = None,
                enable_debug: bool = False,
                enable_visualization: bool = False,
                output_dir: Optional[Union[str, Path]] = None) -> int:
    """
    算法统一入口（便捷函数）：从图片路径和pile_id计算总箱数
    
    :param image_path: 图片路径（RGB图片）
    :param pile_id: 堆垛ID
    :param depth_image_path: 深度图路径（可选，预留参数）
    :param model_path: YOLO模型路径（可选，默认使用 shared/models/yolo/best.pt）
    :param pile_config_path: 堆垛配置路径（可选，默认使用 core/config/pile_config.json）
    :param enable_debug: 是否启用调试输出（打印日志）
    :param enable_visualization: 是否启用可视化（保存效果图到output目录）
    :param output_dir: 可视化输出目录（可选，默认使用 core/detection/output）
    :return: 总箱数（烟箱数）
    
    示例:
        >>> from core.detection.processors import count_boxes
        >>> total = count_boxes("path/to/image.jpg", pile_id=1)
        >>> print(f"总箱数: {total}")
        
        >>> # 启用可视化调试（保存效果图）
        >>> total = count_boxes("path/to/image.jpg", pile_id=1, 
        ...                     enable_visualization=True)
        
        >>> # 使用深度图（预留功能）
        >>> total = count_boxes("path/to/image.jpg", pile_id=1, 
        ...                     depth_image_path="path/to/depth.png")
    """
    factory = StackProcessorFactory(
        enable_debug=enable_debug,
        enable_visualization=enable_visualization,
        model_path=model_path,
        pile_config_path=pile_config_path,
        output_dir=output_dir
    )
    return factory.count(image_path, pile_id, depth_image_path=depth_image_path)

