import os
import subprocess
import sys
import folder_paths

# 版本信息
__version__ = "1.0.0"

class LivePhotoConfig:
    # 使用属性装饰器来动态获取 ComfyUI 的标准目录
    @property
    def OUTPUT_DIR(self):
        return folder_paths.get_output_directory()
        
    @property
    def TEMP_DIR(self):
        return folder_paths.get_temp_directory()
    
    # 视频处理相关配置
    DEFAULT_FPS = 30
    MAX_DURATION = 5
    MIN_DURATION = 1
    DEFAULT_SCALE = "720:-1"
    
    # 文件格式
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.avi', '.mkv']
    OUTPUT_PHOTO_FORMAT = 'JPG'
    OUTPUT_VIDEO_FORMAT = 'MOV'
    
    # ffmpeg 配置
    FFMPEG_VIDEO_CODEC = 'h264'
    FFMPEG_AUDIO_CODEC = 'aac'
    
    # 临时文件配置
    TEMP_PREFIX = 'comfyui_live_photo_'

# 创建全局配置实例
config = LivePhotoConfig()

# 检查必要的依赖
def check_dependencies():
    missing_deps = []
    
    # 检查 Python 包依赖
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("pillow")
    
    # 检查 ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
    except FileNotFoundError:
        missing_deps.append("ffmpeg")
    
    return missing_deps

# 获取 web 目录
def get_web_path():
    """获取web目录的路径"""
    return os.path.dirname(os.path.realpath(__file__))

# 指定 web 目录
WEB_DIRECTORY = get_web_path()

# 执行初始化
print(f"Initializing Live Photo Nodes v{__version__}...")
print(f"Extension directory: {WEB_DIRECTORY}")

# 检查js文件是否存在
js_file = os.path.join(WEB_DIRECTORY, "js", "livephoto_preview.js")
if os.path.exists(js_file):
    print(f"Found JS file: {js_file}")
    # 检查文件权限
    try:
        with open(js_file, 'r') as f:
            print("JS file is readable")
    except Exception as e:
        print(f"Warning: Cannot read JS file: {e}")
else:
    print(f"Warning: JS file not found: {js_file}")

# 检查依赖
missing_deps = check_dependencies()
if missing_deps:
    print("Warning: Missing dependencies:")
    for dep in missing_deps:
        if dep == "ffmpeg":
            print(f"  - {dep} (Please install using your system package manager)")
        else:
            print(f"  - {dep} (Install using: pip install {dep})")

# 导入节点定义
from .livephoto_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 这些变量将被 ComfyUI 使用
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY', 'config']
