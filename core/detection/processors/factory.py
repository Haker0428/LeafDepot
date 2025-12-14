"""堆垛处理器工厂：根据满层判断结果自动选择对应的处理模块"""

from typing import Dict, List, Optional, Union
from pathlib import Path
from ultralytics import YOLO
import cv2
import numpy as np

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
        self.full_processor = full_processor or TemplateBasedFullProcessor(enable_debug=enable_debug)
        self.partial_processor = partial_processor or TemplateBasedPartialProcessor(enable_debug=enable_debug)
        self.single_layer_processor = single_layer_processor or TemplateBasedSingleLayerProcessor(enable_debug=enable_debug)
        self.enable_debug = enable_debug
        self.enable_visualization = enable_visualization
        self.confidence_threshold = confidence_threshold
        self.output_dir = output_dir
        
        # 初始化YOLO模型和pile数据库（如果提供了路径）
        self.model = None
        self.pile_db = None
        
        # 深度图数据（numpy数组）
        self.depth_image = None
        
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
        # 验证和初始化
        image_path = self._validate_inputs(image_path, depth_image_path)
        vis_output_dir = self._prepare_visualization_dir()
        
        # Step 1: YOLO检测
        detections = self._run_yolo_detection(image_path)
        if not detections:
            return 0
        
        # Step 2: 场景准备
        prepared = self._prepare_scene(detections, image_path, vis_output_dir)
        if not prepared:
            return 0
        boxes, pile_roi = prepared["boxes"], prepared["pile_roi"]
        
        # Step 3: 分层聚类
        layers = self._cluster_layers(boxes, pile_roi, image_path, vis_output_dir)
        if not layers:
            return 0
        
        # Step 4: 处理层（去误层、重新索引）
        layers = self._process_layers(layers)
        
        # Step 5: 获取模板配置
        template_layers = self._get_template_config(pile_id, layers)
        
        # 可视化：处理后的分层结果
        if self.enable_visualization:
            self._save_layer_visualization(image_path, boxes, pile_roi, layers, vis_output_dir)
        
        # Step 6: 处理堆垛（满层判断和计数）
        total_count = self.process(layers, template_layers, pile_roi)
        
        # 可视化：最终结果
        if self.enable_visualization:
            self._save_final_visualization(image_path, pile_roi, layers, vis_output_dir)
        
        return total_count
    
    def _validate_inputs(self, image_path: Union[str, Path], 
                        depth_image_path: Optional[Union[str, Path]]) -> Path:
        """验证输入并初始化资源"""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 处理深度图
        if depth_image_path is not None:
            depth_image_path = Path(depth_image_path)
            if not depth_image_path.exists():
                if self.enable_debug:
                    print(f"⚠️  深度图文件不存在: {depth_image_path}，忽略深度图")
                self.depth_image = None
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
                    else:
                        # 如果是彩色图像，转换为灰度图
                        if len(depth_img.shape) == 3:
                            depth_img = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)
                        self.depth_image = depth_img
                        if self.enable_debug:
                            print(f"✅ 深度图加载成功，尺寸: {self.depth_image.shape}")
                except Exception as e:
                    if self.enable_debug:
                        print(f"⚠️  加载深度图时出错: {e}，忽略深度图")
                    self.depth_image = None
        else:
            self.depth_image = None
        
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
            image_name = image_path.stem
            prepare_scene(
                image_path=str(image_path),
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
                       image_path: Path, vis_output_dir: Optional[Path]) -> List[Dict]:
        """分层聚类"""
        layer_result = cluster_layers_with_box_roi(boxes, pile_roi)
        layers = layer_result.get("layers", [])
        
        if not layers:
            if self.enable_debug:
                print("⚠️  无法进行分层聚类")
            return []
        
        # 可视化：分层聚类结果
        if self.enable_visualization:
            image_name = image_path.stem
            visualize_layers(
                image_path=str(image_path),
                boxes=boxes,
                pile_roi=pile_roi,
                save_path=f"{image_name}_step2_layers.jpg",
                gap_ratio=0.6,
                show=False,
                output_dir=vis_output_dir
            )
            visualize_layers_with_roi(
                image_path=str(image_path),
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
    
    def _save_layer_visualization(self, image_path: Path, boxes: List[Dict],
                                  pile_roi: Dict[str, float], layers: List[Dict],
                                  vis_output_dir: Path):
        """保存分层处理后的可视化结果"""
        image_name = image_path.stem
        visualize_layers_with_box_roi(
            image_path=str(image_path),
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
    
    def _save_final_visualization(self, image_path: Path, pile_roi: Dict[str, float],
                                  layers: List[Dict], vis_output_dir: Path):
        """保存最终结果的可视化"""
        image_name = image_path.stem
        layer_result_for_vis = {
            "layer_count": len(layers),
            "layers": layers
        }
        draw_layers_with_box_roi(
            img_path=str(image_path),
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
                pile_roi: Dict[str, float]) -> int:
        """
        处理堆垛：自动判断满层并选择对应处理模块
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param pile_roi: 堆垛ROI区域
        :return: 总箱数（烟箱数）
        """
        # Step 1: 满层判断
        detection_result = self.detector.detect(layers, template_layers, pile_roi, depth_image=self.depth_image)
        # 将pile_roi添加到detection_result中，供后续处理使用
        detection_result["pile_roi"] = pile_roi
        status = detection_result.get("status", "partial")  # 获取状态：'full', 'partial', 'single_layer'
        is_full = detection_result.get("full", False)  # 向后兼容

        # Step 2: 根据判断结果选择处理模块
        if status == "single_layer":
            if self.enable_debug:
                print("🔵 进入单层处理模块")
            processing_result = self.single_layer_processor.process(
                layers, template_layers, detection_result, depth_image=self.depth_image
            )
        elif status == "full" or is_full:
            if self.enable_debug:
                print("🟢 进入满层处理模块")
            processing_result = self.full_processor.process(
                layers, template_layers, detection_result, depth_image=self.depth_image
            )
        else:  # status == "partial"
            if self.enable_debug:
                print("🟡 进入非满层处理模块")
            processing_result = self.partial_processor.process(
                layers, template_layers, detection_result, depth_image=self.depth_image
            )
        
        # Step 3: 返回总箱数
        total_count = processing_result["total"]
        
        if self.enable_debug:
            status_emoji = {"full": "✅", "partial": "❌", "single_layer": "🔵"}
            status_text = status_emoji.get(status, "❓")
            print(f"🎯 处理完成: 总箱数={total_count}, 状态={status} {status_text}")
        
        return total_count


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

