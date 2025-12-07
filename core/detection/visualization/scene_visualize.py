"""场景可视化：绘制pile、box、barcode"""

import cv2
from typing import Dict
from pathlib import Path

from core.detection.detection.scene_prepare import prepare_logic
from core.detection.utils.path_utils import get_output_path


def visualize_pile_scene(
    image_path: str,
    prepared_data: Dict,
    save_path: str = "annotated.jpg",
    show: bool = True,
    output_dir: Path = None
) -> str:
    """
    将 prepare_core 输出的数据在图像上进行可视化
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"未找到图像: {image_path}")

    pile_roi = prepared_data["pile_roi"]
    boxes = prepared_data["boxes"]
    barcodes = prepared_data["barcodes"]

    # 绘 pile (蓝框)
    cv2.rectangle(img, (pile_roi["x1"], pile_roi["y1"]), (pile_roi["x2"], pile_roi["y2"]),
                  (255, 0, 0), 6)
    cv2.putText(img, "PILE", (pile_roi["x1"] + 20, pile_roi["y1"] + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 5)

    # 绘 box (绿框)
    for b in boxes:
        x1, y1, x2, y2 = map(int, [b["x1"], b["y1"], b["x2"], b["y2"]])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 4)
        cv2.putText(img, f"Box {b['conf']:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)

    # 绘 barcode (红框)
    for b in barcodes:
        x1, y1, x2, y2 = map(int, [b["x1"], b["y1"], b["x2"], b["y2"]])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(img, "QR", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # 数量显示
    text = f"Boxes: {len(boxes)} | Barcodes: {len(barcodes)}"
    cv2.putText(img, text, (pile_roi["x1"] + 20, pile_roi["y2"] - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    if show:
        cv2.imshow("Pile Visualization", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        # 使用统一的输出目录
        output_path = get_output_path(save_path, output_dir)
        cv2.imwrite(output_path, img)
        print(f"✅ 可视化保存到: {output_path}")
        return output_path
    return save_path


def prepare_scene(
    image_path: str,
    yolo_output: list,
    conf_thr: float = 0.6,
    save_path: str = "annotated.jpg",
    show: bool = False,
    output_dir: Path = None
):
    """
    一站式预处理接口：
    - 过滤 + ROI 确定
    - 可视化输出
    """
    prepared = prepare_logic(yolo_output, conf_thr=conf_thr)
    if not prepared:
        return None
    annotated_path = visualize_pile_scene(
        image_path=image_path,
        prepared_data=prepared,
        save_path=save_path,
        show=show,
        output_dir=output_dir
    )
    prepared["annotated_path"] = annotated_path
    return prepared

