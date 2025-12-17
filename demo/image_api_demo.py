"""
图片API Demo - 独立测试后端图片接口

使用方法:
    python demo/image_api_demo.py

然后访问 http://localhost:8001 查看前端页面
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn

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


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 图片API Demo 服务启动")
    print("=" * 60)
    print("📡 API地址: http://localhost:8001")
    print("🌐 前端页面: http://localhost:8001")
    print("📸 图片列表API: http://localhost:8001/api/demo/images/list")
    print("=" * 60)
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")

