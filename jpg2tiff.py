import os
import shutil
import platform
import subprocess
import argparse
from typing import Dict, List, Optional
from PIL import Image
import piexif
from tqdm import tqdm
import numpy as np

"""
DJI 图像批处理工具 - 精简版
自动处理DJI相机拍摄的图像数据:
1. JPG转TIFF格式转换
2. 文件分类整理
"""

class ImageProcessor:
    """图像处理器"""
    
    # 目录名称常量
    INPUT_DIR_NAME = "input_dir"  # 存放原始图像
    OUTPUT_DIR_NAME = "out_dir"   # 存放转换后的图像
    TEMP_DIR_NAME = "temp_dir"   # 临时文件目录
    
    # 支持的图像格式
    SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
    
    # 测量参数默认值（用于DJI SDK）
    DEFAULT_MEASURE_PARAMS = {
        "distance": 5,      # 测量距离(米)
        "humidity": 50,     # 相对湿度(%)
        "emissivity": 0.95, # 发射率
        "reflection": 25    # 反射温度(℃)
    }

    def __init__(self):
        """初始化处理器，确定运行平台"""
        self.platform = platform.system()

    def process_subfolders(self, parent_dir: str = "main") -> None:
        """处理指定父目录下所有子文件夹"""
        if not os.path.exists(parent_dir):
            raise FileNotFoundError(f"未找到父目录: {parent_dir}")

        subfolders = [f for f in os.listdir(parent_dir)
                     if os.path.isdir(os.path.join(parent_dir, f))]
        
        if not subfolders:
            print(f"在{parent_dir}中未找到子文件夹")
            return
            
        for subfolder in subfolders:
            subfolder_path = os.path.join(parent_dir, subfolder)
            print(f"\n处理: {subfolder}")
            self._process_single_folder(subfolder_path)

    def _process_single_folder(self, folder_path: str) -> None:
        """处理单个红外文件夹"""
        # 创建所需的子目录
        input_dir = self._create_directory(folder_path, self.INPUT_DIR_NAME)
        output_dir = self._create_directory(folder_path, self.OUTPUT_DIR_NAME)
        temp_dir = self._create_directory(folder_path, self.TEMP_DIR_NAME)

        try:
            # 整理文件并处理
            self._move_files_and_process(folder_path, input_dir, output_dir, temp_dir)
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _create_directory(self, parent_path: str, dir_name: str) -> str:
        """创建目录，如果已存在则先删除"""
        dir_path = os.path.join(parent_path, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path)
        return dir_path

    def _move_files_and_process(self, src_dir: str, input_dir: str, output_dir: str, 
                             temp_dir: str) -> None:
        """移动文件并进行处理"""
        # 移动图像文件
        image_files = [f for f in os.listdir(src_dir) 
                      if f.lower().endswith(self.SUPPORTED_IMAGE_EXTENSIONS)]
        for filename in image_files:
            shutil.move(os.path.join(src_dir, filename), 
                       os.path.join(input_dir, filename))
            
        # 处理图像
        if image_files:
            pbar = tqdm(image_files, desc="转换进度")
            for filename in pbar:
                input_path = os.path.join(input_dir, filename)
                raw_path = os.path.join(temp_dir, f"{os.path.splitext(filename)[0]}.raw")
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.tiff")
                
                # 隐藏DJI SDK的输出
                devnull = subprocess.DEVNULL if self.platform == "Windows" else os.devnull
                self._convert_with_dji_sdk(input_path, raw_path, devnull)
                self._process_raw_image(raw_path, output_path, input_path)

    def _convert_with_dji_sdk(self, input_path: str, raw_path: str, devnull) -> None:
        """使用DJI Thermal SDK转换图像"""
        sdk_command = (
            "dji_thermal_sdk_v1.5_20240507/utility/bin/windows/release_x64/dji_irp.exe "
            f"-s {input_path} -a measure -o {raw_path}"
        )
        
        if self.platform == "Windows":
            powershell = r"C:\WINDOWS\system32\WindowsPowerShell\v1.0\powershell.exe"
            subprocess.run([powershell, sdk_command], 
                         stdout=devnull, 
                         stderr=devnull,
                         check=True)
        else:
            subprocess.run(sdk_command, 
                         shell=True, 
                         stdout=devnull,
                         stderr=devnull,
                         check=True)

    def _process_raw_image(self, raw_path: str, output_path: str, original_image_path: str) -> None:
        """处理RAW格式的温度数据并保存为TIFF"""
        with Image.open(original_image_path) as img:
            width, height = img.size

        img_data = np.fromfile(raw_path, dtype='int16')
        img_data = img_data.reshape(height, width) / 10  # 转换为摄氏度

        # 保留GPS信息
        exif_dict = piexif.load(original_image_path)
        new_exif = {
            '0th': {},
            'Exif': {},
            'GPS': exif_dict['GPS'],
            'Interop': {},
            '1st': {},
            'thumbnail': exif_dict['thumbnail']
        }
        exif_bytes = piexif.dump(new_exif)
        
        Image.fromarray(img_data).save(output_path, exif=exif_bytes)

if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="DJI 图像批处理工具 - 精简版")
    parser.add_argument("-d", "--directory",
                      default="main",
                      help="指定要处理的根目录路径（默认为'main'）")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    processor = ImageProcessor()
    try:
        print(f"\n处理目录: {args.directory}")
        processor.process_subfolders(args.directory)
        print("\n完成")
    except Exception as e:
        print(f"\n错误: {str(e)}")