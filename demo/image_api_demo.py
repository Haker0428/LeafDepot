"""
图片API Demo - 独立测试后端图片接口

使用方法:
    python demo/image_api_demo.py

然后访问 http://localhost:8001 查看前端页面
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入检测和条码识别模块
try:
    from core.detection import count_boxes
    from core.vision.barcode_recognizer import BarcodeRecognizer
except ImportError as e:
    print(f"警告: 无法导入模块 {e}")

app = FastAPI(title="图片API Demo")

# 配置CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录（用于前端页面）
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """返回前端页面"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "请创建 demo/static/index.html 文件"}


@app.get("/test_detect")
async def test_detect_page():
    """返回检测测试页面"""
    html_file = static_dir / "test_detect.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "请创建 demo/static/test_detect.html 文件"}


@app.get("/api/inventory/image")
async def get_inventory_image(
    taskNo: str,
    binLocation: str,
    cameraType: str,
    filename: str
):
    """
    获取盘点任务中的图片（与正式工程接口保持一致）
    
    Args:
        taskNo: 任务编号
        binLocation: 储位名称
        cameraType: 相机类型
        filename: 文件名
    """
    try:
        # 构建图片路径（使用测试图片目录）
        # 这里使用项目中的测试图片作为示例
        project_root = Path(__file__).parent.parent
        
        # 方式1: 尝试从output目录查找（模拟正式工程的路径结构）
        image_path = project_root / "output" / taskNo / binLocation / cameraType / filename
        
        # 方式2: 如果不存在，尝试从测试图片目录查找
        if not image_path.exists():
            # 使用测试图片目录
            test_images_dir = project_root / "tests" / "test_images" / "total" / "test01"
            
            # 根据filename映射到实际文件
            file_mapping = {
                "main.jpeg": "main.jpeg",
                "main_rotated.jpeg": "main.jpeg",  # 如果没有旋转版本，使用原图
                "fourth.jpeg": "fourth.jpeg",
                "depth.jpg": "depth.jpg" if (test_images_dir / "depth.jpg").exists() else "fourth.jpeg",
                "raw.jpg": "main.jpeg",  # raw.jpg映射到main.jpeg
            }
            
            actual_filename = file_mapping.get(filename, filename)
            image_path = test_images_dir / actual_filename
        
        # 方式3: 如果还是不存在，尝试从detection output目录查找
        if not image_path.exists():
            detection_output = project_root / "core" / "detection" / "output"
            image_path = detection_output / filename
        
        if not image_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"图片不存在: {filename} (taskNo={taskNo}, binLocation={binLocation}, cameraType={cameraType})"
            )
        
        # 读取图片文件
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 根据文件扩展名确定媒体类型
        media_type = "image/jpeg"
        if filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith(".gif"):
            media_type = "image/gif"
        
        return Response(content=image_data, media_type=media_type)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取图片失败: {str(e)}"
        )


@app.get("/api/demo/images/list")
async def list_available_images():
    """
    列出可用的测试图片（用于demo测试）
    """
    project_root = Path(__file__).parent.parent
    test_images_dir = project_root / "tests" / "test_images" / "total" / "test01"
    detection_output = project_root / "core" / "detection" / "output"
    
    images = []
    
    # 从测试图片目录获取
    if test_images_dir.exists():
        for img_file in test_images_dir.glob("*.jpeg"):
            images.append({
                "filename": img_file.name,
                "path": f"/api/inventory/image?taskNo=demo&binLocation=test01&cameraType=main&filename={img_file.name}",
                "type": "test_image"
            })
        for img_file in test_images_dir.glob("*.jpg"):
            images.append({
                "filename": img_file.name,
                "path": f"/api/inventory/image?taskNo=demo&binLocation=test01&cameraType=main&filename={img_file.name}",
                "type": "test_image"
            })
    
    # 从detection output目录获取
    if detection_output.exists():
        for img_file in detection_output.glob("*.jpg"):
            if img_file.name not in [img["filename"] for img in images]:
                images.append({
                    "filename": img_file.name,
                    "path": f"/api/inventory/image?taskNo=demo&binLocation=test01&cameraType=main&filename={img_file.name}",
                    "type": "detection_output"
                })
        for img_file in detection_output.glob("*.jpeg"):
            if img_file.name not in [img["filename"] for img in images]:
                images.append({
                    "filename": img_file.name,
                    "path": f"/api/inventory/image?taskNo=demo&binLocation=test01&cameraType=main&filename={img_file.name}",
                    "type": "detection_output"
                })
    
    return {
        "code": 200,
        "message": "获取图片列表成功",
        "data": images
    }


# 请求模型定义
class DetectRequest(BaseModel):
    image_path: str  # 路径格式: taskNo/binLocation/3d_camera/ 或完整路径
    pile_id: int = 1  # 堆垛ID，默认为1


class BarcodeRequest(BaseModel):
    image_path: str  # 路径格式: taskNo/binLocation/3d_camera/
    code_type: str = "ucc128"  # 条码类型，默认ucc128


@app.post("/api/demo/detect")
async def run_detect(request: DetectRequest = Body(...)):
    """
    运行Detect模块进行检测
    
    Args:
        request: DetectRequest对象，包含image_path和pile_id
    """
    try:
        project_root = Path(__file__).parent.parent
        
        # 处理路径：如果路径是相对路径（任务号/库位号/3d_camera/），则拼接output目录
        if "/" in request.image_path and not os.path.isabs(request.image_path):
            # 相对路径，拼接output目录
            image_dir = project_root / "output" / request.image_path
        else:
            # 绝对路径，直接使用
            image_dir = Path(request.image_path)
        
        # 查找目录中的图片文件（优先查找常见的图片文件名）
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []
        
        # 优先查找常见文件名
        common_names = ['main', 'raw', 'image', 'img', 'photo']
        for name in common_names:
            for ext in image_extensions:
                common_file = image_dir / f"{name}{ext}"
                if common_file.exists():
                    image_files.append(common_file)
                common_file_upper = image_dir / f"{name}{ext.upper()}"
                if common_file_upper.exists():
                    image_files.append(common_file_upper)
        
        # 如果没找到常见文件名，查找所有图片
        if not image_files:
            for ext in image_extensions:
                image_files.extend(list(image_dir.glob(f"*{ext}")))
                image_files.extend(list(image_dir.glob(f"*{ext.upper()}")))
        
        # 如果还是没找到，递归查找子目录
        if not image_files:
            for ext in image_extensions:
                image_files.extend(list(image_dir.rglob(f"*{ext}")))
                image_files.extend(list(image_dir.rglob(f"*{ext.upper()}")))
                if image_files:
                    break
        
        # 如果还是找不到图片，尝试使用测试图片
        if not image_files:
            test_images_dir = project_root / "tests" / "test_images" / "total" / "test01"
            if test_images_dir.exists():
                test_images = list(test_images_dir.glob("*.jpeg")) + list(test_images_dir.glob("*.jpg"))
                if test_images:
                    image_path = str(test_images[0])
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"在路径 {image_dir} 中未找到图片文件，且测试图片目录为空"
                    )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"在路径 {image_dir} 中未找到图片文件"
                )
        else:
            # 使用找到的第一张图片
            image_path = str(image_files[0])
        
        # 调用detect模块
        try:
            total_count = count_boxes(
                image_path=image_path,
                pile_id=request.pile_id,
                enable_debug=True,
                enable_visualization=True
            )
            
            return JSONResponse({
                "code": 200,
                "message": "Detect模块执行成功",
                "data": {
                    "image_path": image_path,
                    "pile_id": request.pile_id,
                    "total_count": total_count,
                    "image_dir": str(image_dir)
                }
            })
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Detect模块执行失败: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理请求失败: {str(e)}"
        )


@app.post("/api/demo/barcode")
async def run_barcode(request: BarcodeRequest = Body(...)):
    """
    运行Barcode模块进行条码识别
    
    Args:
        request: BarcodeRequest对象，包含image_path和code_type
    """
    try:
        project_root = Path(__file__).parent.parent
        
        # 处理路径：如果路径是相对路径（任务号/库位号/3d_camera/），则拼接output目录
        if "/" in request.image_path and not os.path.isabs(request.image_path):
            # 相对路径，拼接output目录
            image_dir = project_root / "output" / request.image_path
        else:
            # 绝对路径，直接使用
            image_dir = Path(request.image_path)
        
        # 检查目录是否存在
        if not image_dir.exists() or not image_dir.is_dir():
            # 尝试使用测试图片目录
            test_images_dir = project_root / "tests" / "test_images" / "total" / "test01"
            if test_images_dir.exists():
                image_dir = test_images_dir
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"路径不存在: {image_dir}"
                )
        
        # 初始化条码识别器
        try:
            recognizer = BarcodeRecognizer(code_type=request.code_type)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"初始化条码识别器失败: {str(e)}"
            )
        
        # 调用条码识别模块
        try:
            results = recognizer.process_folder(input_dir=str(image_dir))
            
            return JSONResponse({
                "code": 200,
                "message": "Barcode模块执行成功",
                "data": {
                    "image_path": str(image_dir),
                    "code_type": request.code_type,
                    "results": results,
                    "total_images": len(results),
                    "successful": sum(1 for r in results if r.get("output")),
                    "failed": sum(1 for r in results if r.get("error") and not r.get("output"))
                }
            })
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Barcode模块执行失败: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理请求失败: {str(e)}"
        )


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 图片API Demo 服务启动")
    print("=" * 60)
    print("📡 API地址: http://localhost:8001")
    print("🌐 前端页面: http://localhost:8001")
    print("🔍 检测测试页面: http://localhost:8001/test_detect")
    print("📸 图片列表API: http://localhost:8001/api/demo/images/list")
    print("🔬 Detect模块API: http://localhost:8001/api/demo/detect")
    print("📊 Barcode模块API: http://localhost:8001/api/demo/barcode")
    print("=" * 60)
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")

