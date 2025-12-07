"""
箱体计数服务
功能：
1. 拷贝图片到工作目录
2. 调用 boxdetect 算法进行检测
3. 返回实际箱体数量
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from ultralytics import YOLO
import logging

from core.detection.utils.yolo_utils import extract_yolo_detections
from core.detection.detection.scene_prepare import prepare_logic, remove_fake_top_layer
from core.detection.detection.layer_clustering import cluster_layers_with_box_roi
from core.detection.detection.stack_processor_factory import StackProcessorFactory
from core.detection.utils.pile_db import PileTypeDatabase

logger = logging.getLogger(__name__)


class BoxCountService:
    """箱体计数服务类"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        pile_config_path: Optional[str] = None,
        work_dir: Optional[str] = None,
        confidence_threshold: float = 0.65
    ):
        """
        初始化箱体计数服务
        
        :param model_path: YOLO模型路径，默认使用 shared/models/yolo/best.pt
        :param pile_config_path: 堆垛配置路径，默认使用 core/config/pile_config.json
        :param work_dir: 工作目录，用于保存临时图片和处理结果
        :param confidence_threshold: 置信度阈值
        """
        # 设置默认路径
        if model_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            model_path = project_root / "shared" / "models" / "yolo" / "best.pt"
        self.model_path = str(model_path)
        
        if pile_config_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            pile_config_path = project_root / "core" / "config" / "pile_config.json"
        self.pile_config_path = str(pile_config_path)
        
        if work_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            work_dir = project_root / "output" / "box_count"
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.confidence_threshold = confidence_threshold
        
        # 初始化模型和数据库
        logger.info(f"加载YOLO模型: {self.model_path}")
        self.model = YOLO(self.model_path)
        
        logger.info(f"加载堆垛配置: {self.pile_config_path}")
        self.pile_db = PileTypeDatabase(self.pile_config_path)
        
        # 初始化处理器工厂
        self.processor_factory = StackProcessorFactory(enable_debug=False)
        
        logger.info("BoxCountService 初始化完成")
    
    def fetch_image(
        self,
        task_id: str,
        bin_code: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> str:
        """
        从相机系统拉取图片（预留接口，待实现）
        
        :param task_id: 任务ID
        :param bin_code: 库位代码（可选）
        :param auth_token: 认证令牌（可选）
        :return: 拉取后的图片保存路径
        :raises: NotImplementedError 当前为预留接口，需要后续实现
        """
        # TODO: 实现图片拉取逻辑
        # 1. 根据 task_id 和 bin_code 从相机系统拉取图片
        # 2. 可以调用相机系统API（如 services/sim/cam_sys 或 hardware/cam_sys）
        # 3. 将图片保存到工作目录
        # 4. 返回保存后的图片路径
        
        raise NotImplementedError(
            "fetch_image 方法待实现。需要根据 task_id 和 bin_code 从相机系统拉取图片。"
            f"参数: task_id={task_id}, bin_code={bin_code}"
        )
    
    def copy_image(self, source_path: str, task_id: str, bin_code: Optional[str] = None) -> str:
        """
        拷贝图片到工作目录
        
        :param source_path: 源图片路径
        :param task_id: 任务ID，用于命名
        :param bin_code: 库位代码（可选）
        :return: 拷贝后的图片路径
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"源图片不存在: {source_path}")
        
        # 生成目标文件名
        if bin_code:
            filename = f"{task_id}_{bin_code}_{source_path.name}"
        else:
            filename = f"{task_id}_{source_path.name}"
        
        target_path = self.work_dir / filename
        
        # 拷贝文件
        shutil.copy2(source_path, target_path)
        logger.info(f"图片已拷贝: {source_path} -> {target_path}")
        
        return str(target_path)
    
    def count_boxes(
        self,
        image_path: str,
        pile_id: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        对图片进行箱体计数
        
        :param image_path: 图片路径
        :param pile_id: 堆垛ID（用于获取模板配置），如果为None则自动判断
        :param task_id: 任务ID（用于日志记录）
        :return: 检测结果字典，包含：
            - success: bool 是否成功
            - total_count: int 总箱数
            - status: str 状态信息（"success" 或错误信息）
        """
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"图片不存在: {image_path}")
            
            logger.info(f"开始检测图片: {image_path} (任务ID: {task_id})")
            
            # Step 1: YOLO 检测
            results = self.model.predict(
                source=str(image_path),
                save=False,
                conf=self.confidence_threshold
            )
            
            # Step 2: 提取检测结果
            detections = extract_yolo_detections(results)
            logger.info(f"YOLO检测到 {len(detections)} 个对象")
            
            if not detections:
                return {
                    "success": False,
                    "total_count": 0,
                    "status": "未检测到任何对象"
                }
            
            # Step 3: 场景准备（过滤并找到pile）
            prepared = prepare_logic(detections, conf_thr=self.confidence_threshold)
            if prepared is None:
                return {
                    "success": False,
                    "total_count": 0,
                    "status": "未检测到pile或pile内没有box"
                }
            
            boxes = prepared["boxes"]
            pile_roi = prepared["pile_roi"]
            
            logger.info(f"场景准备完成: 检测到 {len(boxes)} 个box")
            
            # Step 4: 分层聚类
            layer_result = cluster_layers_with_box_roi(boxes, pile_roi)
            layers = layer_result.get("layers", [])
            
            if not layers:
                return {
                    "success": False,
                    "total_count": 0,
                    "status": "无法进行分层聚类"
                }
            
            # Step 5: 去除误层
            layers = remove_fake_top_layer(layers)
            
            # Step 6: 重新索引层（最上层为1）
            layers = sorted(layers, key=lambda l: l["avg_y"])
            for i, layer in enumerate(layers, 1):
                layer["index"] = i
            
            # Step 7: 获取模板配置
            if pile_id is None:
                # 自动判断：使用第一个可用的pile配置（或根据实际情况判断）
                pile_id = 1
                logger.warning(f"未指定pile_id，使用默认值: {pile_id}")
            
            template_layers = self.pile_db.get_template_layers(pile_id)
            if not template_layers:
                # 如果没有配置，使用检测到的层数，每层使用检测到的箱数
                template_layers = [len(layer["boxes"]) for layer in layers]
                logger.warning(f"未找到pile_id={pile_id}的配置，使用检测结果作为模板")
            
            # Step 8: 处理堆垛（满层判断和计数）
            result = self.processor_factory.process(layers, template_layers, pile_roi)
            
            total_count = result.get("total", 0)
            is_full = result.get("full", False)
            
            logger.info(f"检测完成: 总箱数={total_count}, 是否满层={is_full}")
            
            return {
                "success": True,
                "total_count": total_count,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"箱体计数失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "total_count": 0,
                "status": str(e)
            }
    
    def process_image(
        self,
        task_id: str,
        bin_code: Optional[str] = None,
        pile_id: Optional[int] = None,
        auth_token: Optional[str] = None
    ) -> Dict:
        """
        完整流程：拉取图片 + 计数
        
        :param task_id: 任务ID（必需）
        :param bin_code: 库位代码（可选）
        :param pile_id: 堆垛ID（可选，默认1）
        :param auth_token: 认证令牌（可选，用于拉取图片）
        :return: 检测结果字典
        """
        try:
            # Step 1: 从相机系统拉取图片
            logger.info(f"开始拉取图片: task_id={task_id}, bin_code={bin_code}")
            image_path = self.fetch_image(task_id, bin_code, auth_token)
            logger.info(f"图片拉取成功: {image_path}")
            
            # Step 2: 计数
            result = self.count_boxes(image_path, pile_id, task_id)
            return result
            
        except NotImplementedError as e:
            logger.error(f"图片拉取功能未实现: {str(e)}")
            return {
                "success": False,
                "total_count": 0,
                "status": f"图片拉取功能未实现: {str(e)}"
            }
        except Exception as e:
            logger.error(f"处理图片失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "total_count": 0,
                "status": str(e)
            }


# 全局单例实例（可选）
_box_count_service: Optional[BoxCountService] = None


def get_box_count_service() -> BoxCountService:
    """获取全局BoxCountService实例（单例模式）"""
    global _box_count_service
    if _box_count_service is None:
        _box_count_service = BoxCountService()
    return _box_count_service

