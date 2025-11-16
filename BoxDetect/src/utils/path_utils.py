"""路径工具：统一管理输出目录"""

from pathlib import Path
from typing import Union


# 默认输出目录
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def ensure_output_dir(base_dir: Union[str, Path] = None) -> Path:
    """
    确保输出目录存在，如果不存在则创建
    
    Args:
        base_dir: 基础目录路径，默认为 src/output
        
    Returns:
        输出目录的 Path 对象
    """
    if base_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    else:
        output_dir = Path(base_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_output_path(filename: str, base_dir: Union[str, Path] = None) -> str:
    """
    获取输出文件的完整路径
    
    Args:
        filename: 文件名（如 "annotated.jpg"）
        base_dir: 基础目录路径，默认为 src/output
        
    Returns:
        完整的文件路径字符串
    """
    output_dir = ensure_output_dir(base_dir)
    return str(output_dir / filename)

