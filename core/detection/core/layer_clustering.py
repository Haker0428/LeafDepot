"""分层聚类：根据box位置进行分层处理"""

import cv2
import numpy as np
from typing import Dict, List, Union
from pathlib import Path

from core.detection.utils.path_utils import get_output_path


def cluster_layers(boxes: List[Dict], pile_roi: Dict[str, float], gap_ratio: float = 0.6) -> Dict:
    """
    根据 box 的中心 y 坐标进行分层聚类（自动层数）
    """
    if not boxes:
        return {"layer_count": 0, "layers": []}

    centers = []
    for b in boxes:
        yc = 0.5 * (b["y1"] + b["y2"])
        h = abs(b["y2"] - b["y1"])
        centers.append((yc, h, b))
    centers.sort(key=lambda x: x[0])  # 从上到下排序

    avg_h = np.mean([c[1] for c in centers])
    threshold = avg_h * gap_ratio

    layers, current = [], [centers[0]]
    for i in range(1, len(centers)):
        gap = centers[i][0] - centers[i-1][0]
        if gap > threshold:
            layers.append(current)
            current = [centers[i]]
        else:
            current.append(centers[i])
    layers.append(current)

    layer_info = []
    for idx, layer in enumerate(layers, start=1):
        boxes_in_layer = [c[2] for c in layer]
        avg_y = np.mean([c[0] for c in layer])
        layer_info.append({
            "index": idx,
            "avg_y": round(float(avg_y), 2),
            "boxes": boxes_in_layer
        })

    return {
        "layer_count": len(layer_info),
        "layers": layer_info
    }


def cluster_layers_with_roi(
    boxes: List[Dict],
    pile_roi: Dict[str, float],
    gap_ratio: float = 0.6,
    padding_ratio: float = 0.1
) -> Dict:
    """
    分层聚类 + 每层ROI提取
    """
    if not boxes:
        return {"layer_count": 0, "layers": []}

    centers = []
    for b in boxes:
        yc = 0.5 * (b["y1"] + b["y2"])
        h = abs(b["y2"] - b["y1"])
        centers.append((yc, h, b))
    centers.sort(key=lambda x: x[0])

    avg_h = np.mean([c[1] for c in centers])
    threshold = avg_h * gap_ratio

    layers, current = [], [centers[0]]
    for i in range(1, len(centers)):
        gap = centers[i][0] - centers[i-1][0]
        if gap > threshold:
            layers.append(current)
            current = [centers[i]]
        else:
            current.append(centers[i])
    layers.append(current)

    layer_info = []
    for idx, layer in enumerate(layers, start=1):
        boxes_in_layer = [c[2] for c in layer]
        avg_y = np.mean([c[0] for c in layer])
        y_tops = [b["y1"] for b in boxes_in_layer]
        y_bottoms = [b["y2"] for b in boxes_in_layer]
        y_top = max(pile_roi["y1"], min(y_tops) - avg_h * padding_ratio)
        y_bottom = min(pile_roi["y2"], max(y_bottoms) + avg_h * padding_ratio)

        layer_info.append({
            "index": idx,
            "avg_y": round(float(avg_y), 2),
            "roi": {
                "y_top": round(float(y_top), 2),
                "y_bottom": round(float(y_bottom), 2)
            },
            "boxes": boxes_in_layer
        })

    return {
        "layer_count": len(layer_info),
        "layers": layer_info
    }


def cluster_layers_with_box_roi(
    boxes: List[Dict],
    pile_roi: Dict[str, float],
    gap_ratio: float = 0.6,
    padding_ratio: float = 0.1
) -> Dict:
    """
    分层聚类 + 每层ROI + 每个box的ROI信息
    """
    if not boxes:
        return {"layer_count": 0, "layers": []}

    centers = []
    for b in boxes:
        yc = 0.5 * (b["y1"] + b["y2"])
        h = abs(b["y2"] - b["y1"])
        centers.append((yc, h, b))
    centers.sort(key=lambda x: x[0])

    avg_h = np.mean([c[1] for c in centers])
    threshold = avg_h * gap_ratio

    # 聚类逻辑
    layers, current = [], [centers[0]]
    for i in range(1, len(centers)):
        gap = centers[i][0] - centers[i-1][0]
        if gap > threshold:
            layers.append(current)
            current = [centers[i]]
        else:
            current.append(centers[i])
    layers.append(current)

    # 输出层结构
    layer_info = []
    for idx, layer in enumerate(layers, start=1):
        boxes_in_layer = []
        for j, c in enumerate(layer, start=1):
            b = c[2]
            x1, y1, x2, y2 = map(float, [b["x1"], b["y1"], b["x2"], b["y2"]])
            area = (x2 - x1) * (y2 - y1)
            boxes_in_layer.append({
                "id": j,
                "roi": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "conf": round(float(b["conf"]), 4),
                "area": round(area, 2)
            })

        avg_y = np.mean([c[0] for c in layer])
        y_tops = [b["y1"] for b in [c[2] for c in layer]]
        y_bottoms = [b["y2"] for b in [c[2] for c in layer]]
        y_top = max(pile_roi["y1"], min(y_tops) - avg_h * padding_ratio)
        y_bottom = min(pile_roi["y2"], max(y_bottoms) + avg_h * padding_ratio)

        layer_info.append({
            "index": idx,
            "avg_y": round(float(avg_y), 2),
            "roi": {
                "y_top": round(float(y_top), 2),
                "y_bottom": round(float(y_bottom), 2)
            },
            "boxes": boxes_in_layer
        })

    return {
        "layer_count": len(layer_info),
        "layers": layer_info
    }


def draw_layers_on_image(
    image_path: str,
    pile_roi: Dict[str, float],
    layer_result: Dict,
    save_path: str = "annotated_layers.jpg",
    show: bool = False,
    output_dir: Path = None
) -> str:
    """
    根据 layer_core 的结果在图像上绘制分层信息。
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"未找到图像: {image_path}")

    layers = layer_result["layers"]
    # 绘制每个 box
    for l in layers:
        for b in l["boxes"]:
            x1, y1, x2, y2 = map(int, [b["x1"], b["y1"], b["x2"], b["y2"]])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # 绘制层中心线和文本
    for l in layers:
        y = int(l["avg_y"])
        cv2.line(img, (int(pile_roi["x1"]), y), (int(pile_roi["x2"]), y), (0, 255, 255), 2)
        text = f"Layer {l['index']} | {len(l['boxes'])} boxes"
        cv2.putText(img, text, (int(pile_roi["x1"]) + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

    # 绘制 pile 外框
    cv2.rectangle(img,
                  (int(pile_roi["x1"]), int(pile_roi["y1"])),
                  (int(pile_roi["x2"]), int(pile_roi["y2"])),
                  (255, 0, 0), 3)

    if show:
        cv2.imshow("Layer Clustering", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        output_path = get_output_path(save_path, output_dir)
        cv2.imwrite(output_path, img)
        print(f"✅ 分层可视化完成：{output_path}")
        return output_path
    return save_path


def draw_layers_with_roi(
    image_path: str,
    pile_roi: Dict[str, float],
    layer_result: Dict,
    save_path: str = "annotated_layers_roi.jpg",
    show: bool = False,
    output_dir: Path = None
) -> str:
    """
    可视化：绘制层中心线 + 层ROI矩形 + 层号文字
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"未找到图像: {image_path}")

    layers = layer_result["layers"]

    # 绘制 pile 框（蓝色）
    cv2.rectangle(img,
                  (int(pile_roi["x1"]), int(pile_roi["y1"])),
                  (int(pile_roi["x2"]), int(pile_roi["y2"])),
                  (255, 0, 0), 3)

    for l in layers:
        y_top = int(l["roi"]["y_top"])
        y_bottom = int(l["roi"]["y_bottom"])
        color = (0, 255, 255)  # 黄色线

        # 层矩形ROI
        cv2.rectangle(img,
                      (int(pile_roi["x1"]), y_top),
                      (int(pile_roi["x2"]), y_bottom),
                      (0, 255, 255), 2)

        # 层中心线
        y_mid = int(l["avg_y"])
        cv2.line(img, (int(pile_roi["x1"]), y_mid), (int(pile_roi["x2"]), y_mid), color, 2)

        # 标注层号 + 数量
        text = f"L{l['index']} | {len(l['boxes'])} boxes"
        cv2.putText(img, text, (int(pile_roi["x1"] + 20), y_mid - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

        # 绘制 box
        for b in l["boxes"]:
            x1, y1, x2, y2 = map(int, [b["x1"], b["y1"], b["x2"], b["y2"]])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    if show:
        cv2.imshow("Layer ROI Visualization", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        output_path = get_output_path(save_path, output_dir)
        cv2.imwrite(output_path, img)
        print(f"✅ 层ROI可视化完成：{output_path}")
        return output_path
    return save_path


def draw_layers_with_box_roi(
    img_path: str,
    pile_roi: Dict[str, float],
    layer_result: Dict,
    save_path: str = "annotated_layers_green.jpg",
    show: bool = False,
    target_layers: Union[int, List[int], None] = None,
    alpha: float = 0.3,          # 透明度
    layer_color=(0, 255, 0),    # 层ROI绿色
    box_color=(0, 200, 255),    # box框青橙色
    box_thickness: int = 5,     # 边框粗度
    output_dir: Path = None
):
    """
    分层+Box可视化：
    层ROI使用绿色半透明背景，Box使用粗边框
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"未找到图像: {img_path}")

    overlay = img.copy()  # 用于绘制半透明层

    # 统一 target_layers 格式
    if isinstance(target_layers, int):
        target_layers = [target_layers]
    if target_layers is not None:
        target_layers = set(target_layers)

    # 🟦 绘制 pile 外框（蓝色）
    cv2.rectangle(
        img,
        (int(pile_roi["x1"]), int(pile_roi["y1"])),
        (int(pile_roi["x2"]), int(pile_roi["y2"])),
        (255, 0, 0),
        4,
    )

    # 🟩 绘制每一层 ROI 和 box
    for layer in layer_result["layers"]:
        idx = layer["index"]
        if target_layers and idx not in target_layers:
            continue

        y_top = int(layer["roi"]["y_top"])
        y_bottom = int(layer["roi"]["y_bottom"])
        y_mid = int(layer["avg_y"])

        # 层ROI绿色半透明背景
        cv2.rectangle(
            overlay,
            (int(pile_roi["x1"]), y_top),
            (int(pile_roi["x2"]), y_bottom),
            layer_color,
            -1,  # 填充模式
        )

        # 层中心线
        cv2.line(
            img,
            (int(pile_roi["x1"]), y_mid),
            (int(pile_roi["x2"]), y_mid),
            (0, 255, 255),
            2,
        )

        # 层文本
        text = f"L{idx} | {len(layer['boxes'])} boxes"
        cv2.putText(
            img,
            text,
            (int(pile_roi["x1"]) + 15, y_mid - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3,
        )

        # 绘每个 box 边框
        for b in layer["boxes"]:
            x1, y1, x2, y2 = map(
                int, [b["roi"]["x1"], b["roi"]["y1"], b["roi"]["x2"], b["roi"]["y2"]]
            )
            cv2.rectangle(img, (x1, y1), (x2, y2), box_color, box_thickness)
            cv2.putText(
                img,
                f"B{b['id']}",
                (x1 + 5, y1 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                box_color,
                2,
            )

    # ⚙️ 将 overlay 与原图融合
    img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

    # 保存 / 显示
    if show:
        cv2.imshow("Layer + Box ROI", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        output_path = get_output_path(save_path, output_dir)
        cv2.imwrite(output_path, img)
        print(f"✅ 可视化完成：{output_path}")
        return output_path
    return save_path


def visualize_layers(
    image_path: str,
    boxes: list,
    pile_roi: dict,
    save_path: str = "annotated_layers.jpg",
    gap_ratio: float = 0.6,
    show: bool = False,
    output_dir: Path = None
):
    """
    一站式调用：分层聚类 + 可视化绘制
    """
    layer_result = cluster_layers(boxes, pile_roi, gap_ratio=gap_ratio)
    annotated_path = draw_layers_on_image(
        image_path=image_path,
        pile_roi=pile_roi,
        layer_result=layer_result,
        save_path=save_path,
        show=show,
        output_dir=output_dir
    )
    layer_result["annotated_path"] = annotated_path
    return layer_result


def visualize_layers_with_roi(
    image_path: str,
    boxes: list,
    pile_roi: dict,
    save_path: str = "annotated_layers_roi.jpg",
    gap_ratio: float = 0.6,
    padding_ratio: float = 0.1,
    show: bool = False,
    output_dir: Path = None
):
    """
    一站式接口：分层聚类 + 层ROI计算 + 可视化
    """
    layer_result = cluster_layers_with_roi(boxes, pile_roi, gap_ratio, padding_ratio)
    annotated_path = draw_layers_with_roi(
        image_path=image_path,
        pile_roi=pile_roi,
        layer_result=layer_result,
        save_path=save_path,
        show=show,
        output_dir=output_dir
    )
    layer_result["annotated_path"] = annotated_path
    return layer_result


def visualize_layers_with_box_roi(
    image_path: str,
    boxes: list,
    pile_roi: dict,
    save_path: str = "annotated_layers_boxes.jpg",
    gap_ratio: float = 0.6,
    padding_ratio: float = 0.1,
    show: bool = False,
    target_layers: Union[int, List[int], None] = None,   # 👈 新增参数
    alpha=0.35,              # 阴影透明度
    layer_color=(0, 255, 0), # 绿色层背景
    box_color=(0, 0, 255), # 明亮橙色box框
    box_thickness=7,        # 边框更粗
    output_dir: Path = None
):
    """
    一站式接口：分层 + 层ROI + Box ROI 可视化
    """
    result = cluster_layers_with_box_roi(boxes, pile_roi, gap_ratio, padding_ratio)
    annotated_path = draw_layers_with_box_roi(
        img_path=image_path,
        pile_roi=pile_roi,
        layer_result=result,
        save_path=save_path,
        show=show,
        target_layers=target_layers,
        alpha=alpha,
        layer_color=layer_color,
        box_color=box_color,
        box_thickness=box_thickness,
        output_dir=output_dir
    )
    result["annotated_path"] = annotated_path
    return result

