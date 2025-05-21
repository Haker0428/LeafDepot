import cv2
import numpy as np

# 空间感知去除重复框（保留相距较远的多个条码）
def suppress_near_duplicates(boxes, min_dist_thresh=15):
    if len(boxes) == 0:
        return []

    kept = []
    for box in boxes:
        x1, y1, w1, h1 = box
        cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2

        too_close = False
        for kx, ky, kw, kh in kept:
            cx2, cy2 = kx + kw // 2, ky + kh // 2
            dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            if dist < min_dist_thresh:
                too_close = True
                break
        if not too_close:
            kept.append(box)

    return kept

# 条形码检测主函数
def detect_barcode(image_path, draw_result=True, save_crops=False, padding=0.2):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mser = cv2.MSER_create()
    mser.setMinArea(100)
    mser.setMaxArea(3000)

    regions, _ = mser.detectRegions(gray)
    img_h, img_w = img.shape[:2]

    candidates = []

    for region in regions:
        x, y, w, h = cv2.boundingRect(region)

        if y < img_h * 0.3:
            continue

        aspect_ratio = w / float(h)
        area = w * h

        if not (1.8 < aspect_ratio < 6 and 500 < area < 10000):
            continue

        roi = gray[y:y+h, x:x+w]
        if roi.size == 0:
            continue

        # 1. 平滑区域过滤（空区域）
        roi_std = np.std(roi)
        if roi_std < 25:
            continue

        # 2. 梯度方向性分析（图标 vs 条形码）
        sobelx = cv2.Sobel(roi, cv2.CV_64F, 1, 0)
        sobely = cv2.Sobel(roi, cv2.CV_64F, 0, 1)
        v_std = np.std(sobelx)
        h_std = np.std(sobely)
        if v_std < 20 or v_std < h_std * 1.2:
            continue

        # 3. 灰度均值过滤（极亮/极暗误检）
        mean_intensity = np.mean(roi)
        if mean_intensity < 50 or mean_intensity > 220:
            continue

        # 4. 边缘密度过滤（防止空框）
        edge_count = np.count_nonzero(cv2.Canny(roi, 50, 150))
        if edge_count < roi.shape[0] * roi.shape[1] * 0.05:
            continue

        candidates.append((x, y, w, h))

    # 空间感知去除重复框
    final_boxes = suppress_near_duplicates(candidates, min_dist_thresh=15)

    for i, (x, y, w, h) in enumerate(final_boxes):
        # 扩大ROI
        x_pad = max(0, x - int(w * padding))
        y_pad = max(0, y - int(h * padding))
        w_pad = min(img_w - x_pad, int(w * (1 + 2 * padding)))
        h_pad = min(img_h - y_pad, int(h * (1 + 2 * padding)))

        # 绘制和保存
        cv2.rectangle(img, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 255, 0), 2)

        if save_crops:
            crop = img[y_pad:y_pad + h_pad, x_pad:x_pad + w_pad]
            cv2.imwrite(f"barcode_v5_{i}.png", crop)

    if draw_result:
        cv2.imshow("Barcode Detection", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return final_boxes

boxes = detect_barcode(
    "raw_img/img04.png",
    draw_result=True,
    save_crops=True,
    padding=0.2  # 调整为 0.3 可更宽松
)
print(f"最终检测到条形码数量: {len(boxes)}")
