import os
import torch
import numpy as np
import cv2
import json
import shutil
from PIL import Image
import subprocess
from datetime import datetime
import uuid
from server import PromptServer
import folder_paths
from . import config

def get_output_dir():
    """获取 Live Photo 专用的输出目录"""
    base_output_dir = folder_paths.get_output_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_output_dir, f"livephoto_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

class LivePhotoCreator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),  # 接收图片序列
                "key_frame_index": ("INT", {  # 选择关键帧的索引
                    "default": 0,
                    "min": 0,
                    "step": 1,
                }),
                "duration": ("FLOAT", {
                    "default": 3.0,
                    "min": config.MIN_DURATION,
                    "max": config.MAX_DURATION,
                    "step": 0.1
                }),
                "fps": ("FLOAT", {
                    "default": config.DEFAULT_FPS,
                    "min": 1.0,
                    "max": 60.0,
                    "step": 1.0
                })
            },
            "optional": {
                "audio": ("AUDIO",),  # 可选的音频输入
            }
        }
    
    RETURN_TYPES = ("IMAGE", "VIDEO", "STRING")  # 返回静态图片、视频路径和输出目录
    RETURN_NAMES = ("photo", "video", "output_path")
    FUNCTION = "create_live_photo"
    CATEGORY = "image/animation"

    def tensor_to_pil(self, img_tensor):
        # 将tensor转换为PIL图像
        i = 255. * img_tensor.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        return img

    def tensor_to_cv2(self, img_tensor):
        # 将tensor转换为OpenCV格式图像
        img_np = (255. * img_tensor.cpu().numpy()).astype(np.uint8)
        if img_np.shape[-1] == 3:  # 如果是RGB，转换为BGR
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return img_np

    def save_audio(self, audio_obj, output_path):
        """保存音频对象到WAV文件"""
        try:
            # 检查音频对象是否有filepath属性（可能是文件路径）
            if hasattr(audio_obj, 'filepath') and os.path.exists(audio_obj.filepath):
                shutil.copy2(audio_obj.filepath, output_path)
                return True
            
            # 如果有to_wav方法，使用它来保存
            if hasattr(audio_obj, 'to_wav'):
                audio_obj.to_wav(output_path)
                return True
                
            # 如果有save方法，使用它来保存
            if hasattr(audio_obj, 'save'):
                audio_obj.save(output_path)
                return True
                
            # 如果有write方法，使用它来保存
            if hasattr(audio_obj, 'write'):
                audio_obj.write(output_path)
                return True

            # 如果音频对象可以直接转换为numpy数组
            if hasattr(audio_obj, 'numpy') or hasattr(audio_obj, '__array__'):
                import scipy.io.wavfile as wav
                audio_data = np.array(audio_obj)
                if hasattr(audio_obj, 'sample_rate'):
                    sample_rate = audio_obj.sample_rate
                else:
                    sample_rate = 44100  # 默认采样率
                wav.write(output_path, sample_rate, audio_data)
                return True

            return False
        except Exception as e:
            print(f"Error saving audio: {str(e)}")
            return False

    def create_live_photo(self, images, key_frame_index, duration, fps, audio=None):
        # 使用 ComfyUI 的临时目录
        temp_dir = os.path.join(config.TEMP_DIR, f"live_photo_{str(uuid.uuid4())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 获取专用的输出目录
            output_dir = get_output_dir()
            
            # 验证关键帧索引
            if key_frame_index >= len(images):
                key_frame_index = len(images) - 1
            
            # 保存关键帧作为静态图片
            key_frame = images[key_frame_index]
            key_frame_path = os.path.join(temp_dir, "key_photo.jpg")
            # 将tensor转换为PIL图像并保存
            key_frame_pil = self.tensor_to_pil(key_frame)
            key_frame_pil.save(key_frame_path, quality=95)

            # 创建临时视频文件
            temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
            
            # 准备视频写入器
            height, width = images[0].shape[:2]
            writer = cv2.VideoWriter(
                temp_video_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps,
                (width, height)
            )

            # 写入所有帧
            for image in images:
                frame = self.tensor_to_cv2(image)
                writer.write(frame)
            
            writer.release()

            # 准备最终的视频输出路径
            output_video_path = os.path.join(temp_dir, "video.mov")

            # 构建ffmpeg命令
            ffmpeg_command = [
                'ffmpeg', '-i', temp_video_path
            ]

            # 如果有音频，尝试添加音频
            if audio is not None:
                audio_path = os.path.join(temp_dir, "audio.wav")
                if self.save_audio(audio, audio_path):
                    ffmpeg_command.extend(['-i', audio_path])
                    ffmpeg_command.extend(['-c:a', config.FFMPEG_AUDIO_CODEC])
                else:
                    print("Warning: Failed to process audio, continuing without audio")

            # 添加其他参数
            ffmpeg_command.extend([
                '-t', str(duration),
                '-vf', f'scale={config.DEFAULT_SCALE}',
                '-c:v', config.FFMPEG_VIDEO_CODEC,
                '-strict', 'experimental',
                output_video_path
            ])

            # 执行ffmpeg命令
            subprocess.run(ffmpeg_command, check=True)

            # 创建最终输出文件
            final_photo_path = os.path.join(output_dir, f"IMG.JPG")
            final_video_path = os.path.join(output_dir, f"IMG.MOV")
            
            shutil.copy2(key_frame_path, final_photo_path)
            shutil.copy2(output_video_path, final_video_path)

            # 确保文件在输出目录中
            if not os.path.exists(final_photo_path) or not os.path.exists(final_video_path):
                raise Exception("Failed to save output files")

            # 返回单帧图像、视频路径和输出目录
            key_frame_tensor = images[key_frame_index:key_frame_index+1]  # 取单帧并保持维度
            return (key_frame_tensor, final_video_path, output_dir)

        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e

class LivePhotoPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
            }
        }
    
    RETURN_TYPES = ()
    FUNCTION = "preview"
    CATEGORY = "image"
    OUTPUT_NODE = True

    def preview(self, video):
        # 确保视频路径是字符串
        if isinstance(video, (list, tuple)):
            video = ''.join(video)
            
        # 确保路径包含 IMG.MOV
        if not video.endswith('IMG.MOV'):
            video = os.path.join(video, 'IMG.MOV')
            
        # 确保路径存在
        if not os.path.exists(video):
            print(f"[LivePhotoPreview] Warning: Video file not found: {video}")
            
        print(f"[LivePhotoPreview] Executing with video path: {video}")
        return {"ui": {"video": video}}

NODE_CLASS_MAPPINGS = {
    "LivePhotoCreator": LivePhotoCreator,
    "LivePhotoPreview": LivePhotoPreview
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LivePhotoCreator": "Create Live Photo",
    "LivePhotoPreview": "Preview Live Photo"
}
