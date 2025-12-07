"""YOLO检测结果处理工具"""

from typing import Dict, Iterable, List, Optional

from ultralytics.engine.results import Results


def extract_yolo_detections(
    results: Iterable[Results],
    accept_classes: Optional[Iterable[str]] = None,
) -> List[Dict]:
    """
    将 YOLO 的推理结果转换为统一字典列表。

    Args:
        results: YOLO 推理结果对象列表 (来自 model(img))
        accept_classes: 指定需要保留的类别名称集合

    Returns:
        检测框数据列表
    """
    if not results:
        return []

    accept_set = set(accept_classes) if accept_classes else None
    yolo_dicts: List[Dict] = []

    for res in results:
        model_names = getattr(res, "names", None) or getattr(getattr(res, "boxes", None), "names", None)
        boxes = getattr(res, "boxes", None)
        if boxes is None:
            continue
        for b in boxes:
            cls_id = int(b.cls)
            cls_name = model_names[cls_id] if model_names and cls_id in model_names else str(cls_id)
            if accept_set and cls_name not in accept_set:
                continue
            conf = float(b.conf)
            x1, y1, x2, y2 = map(float, b.xyxy[0])
            yolo_dicts.append(
                {"cls": cls_name, "conf": conf, "x1": x1, "y1": y1, "x2": x2, "y2": y2}
            )

    return yolo_dicts

