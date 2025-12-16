import os
from PIL import Image

# 定义支持的图像格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

# 获取当前文件夹路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 遍历当前文件夹所有文件
for filename in os.listdir(current_dir):
    # 检查文件扩展名
    ext = os.path.splitext(filename)[1].lower()
    if ext in SUPPORTED_FORMATS:
        file_path = os.path.join(current_dir, filename)
        
        try:
            # 打开图像并顺时针旋转90度
            with Image.open(file_path) as img:
                rotated = img.rotate(-90, expand=True)  # 负数表示顺时针旋转
                
                # 处理PNG图像透明度通道问题
                if ext == '.png' and img.mode == 'RGBA':
                    rotated.save(file_path, 'PNG', quality=100)
                # 处理JPEG质量保留
                elif ext in ('.jpg', '.jpeg'):
                    rotated.save(file_path, 'JPEG', quality=95, optimize=True, progressive=True)
                # 其他格式
                else:
                    rotated.save(file_path)
                    
            print(f"已旋转: {filename}")
            
        except Exception as e:
            print(f"处理 {filename} 时出错: {str(e)}")

print("操作完成！")
