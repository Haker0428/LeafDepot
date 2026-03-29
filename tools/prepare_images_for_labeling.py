import os
from PIL import Image

input_dir = 'raw_images'  # 原始图像目录
output_dir = 'images_for_label'  # 输出目录

os.makedirs(output_dir, exist_ok=True)

for idx, fname in enumerate(sorted(os.listdir(input_dir))):
    if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        img = Image.open(os.path.join(input_dir, fname)).convert('RGB')
        img = img.resize((1280, 1280))  # YOLO推荐输入尺寸
        new_name = f"img{idx:05d}.jpg"
        img.save(os.path.join(output_dir, new_name))

print("✅ 图像预处理完成，统一尺寸和命名")
