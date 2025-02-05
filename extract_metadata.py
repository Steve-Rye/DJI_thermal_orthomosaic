import os
import pyexiv2
import shutil
import tempfile
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from tqdm import tqdm

"""
DJI 图像元数据提取工具

功能描述:
---------
从DJI相机拍摄的JPG图像中提取元数据，包括：
- GPS坐标信息
- 相机姿态信息（Yaw/Pitch/Roll）
- RTK精度信息

工作流程:
--------
1. 处理指定目录下所有子文件夹
2. 处理每个文件夹中的JPG图像
3. 提取XMP元数据
4. 生成标准格式的pos.txt文件

输出格式:
--------
pos.txt包含以下字段:
- 照片名称
- 纬度
- 经度
- 高度
- Yaw
- Pitch
- Roll
- 水平精度
- 垂直精度
"""

class MetadataProcessor:
    """图像元数据处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.temp_dir = self._create_temp_dir()
        self.fieldnames = [
            '照片名称', '纬度', '经度', '高度',
            'Yaw', 'Pitch', 'Roll',
            '水平精度', '垂直精度'
        ]

    def _create_temp_dir(self) -> Path:
        """
        创建临时工作目录
        
        Returns:
            Path: 临时目录路径
            
        Notes:
            - 优先使用系统临时目录
            - 如果系统临时目录不可用，则在当前目录创建
        """
        try:
            temp_base = Path(tempfile.gettempdir())
            temp_dir = temp_base / f'metadata_process_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir
        except Exception as e:
            print(f"警告: 无法使用系统临时目录 ({str(e)})")
            fallback_dir = Path.cwd() / f'temp_metadata_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir

    @staticmethod
    def _process_coordinate(value: str, is_latitude: bool = True) -> str:
        """
        处理GPS坐标值
        
        Args:
            value: 原始坐标值字符串
            is_latitude: 是否为纬度值（用于范围验证）
            
        Returns:
            str: 处理后的坐标值，无效则返回空字符串
            
        Notes:
            - 纬度范围: [-90, 90]
            - 经度范围: [-180, 180]
        """
        try:
            value = value.strip()
            if not value:
                return ''
                
            coord = float(value)
            valid_range = (-90, 90) if is_latitude else (-180, 180)
            
            return str(coord) if valid_range[0] <= coord <= valid_range[1] else ''
                
        except ValueError:
            return ''

    def extract_metadata(self, jpg_path: Union[str, Path]) -> Optional[Dict[str, str]]:
        """
        从单个JPG文件中提取元数据
        
        Args:
            jpg_path: JPG文件路径
            
        Returns:
            Optional[Dict[str, str]]: 提取的元数据字典，提取失败返回None
            
        Notes:
            - 使用临时文件避免中文路径问题
            - 自动处理RTK状态相关的精度信息
        """
        temp_jpg = None
        try:
            jpg_path = Path(jpg_path)
            temp_jpg = self.temp_dir / f"temp_{jpg_path.name}"
            
            # 复制到临时目录
            shutil.copy2(str(jpg_path), str(temp_jpg))
            
            with pyexiv2.Image(str(temp_jpg)) as img:
                xmp_data = img.read_xmp()
                
                # 根据RTK状态设置精度值
                rtk_std_lat = xmp_data.get('Xmp.drone-dji.RtkStdLat', '')
                horizontal_accuracy = 0.03 if rtk_std_lat else 2
                vertical_accuracy = 0.06 if rtk_std_lat else 10

                # 提取并处理坐标数据
                latitude = self._process_coordinate(
                    xmp_data.get('Xmp.drone-dji.GpsLatitude', ''), True)
                longitude = self._process_coordinate(
                    xmp_data.get('Xmp.drone-dji.GpsLongitude', ''), False)

                metadata = {
                    '照片名称': jpg_path.name,
                    '纬度': latitude,
                    '经度': longitude,
                    '高度': xmp_data.get('Xmp.drone-dji.AbsoluteAltitude', '').lstrip('+'),
                    'Yaw': xmp_data.get('Xmp.drone-dji.GimbalYawDegree', '').lstrip('+'),
                    'Pitch': xmp_data.get('Xmp.drone-dji.GimbalPitchDegree', '').lstrip('+'),
                    'Roll': xmp_data.get('Xmp.drone-dji.GimbalRollDegree', '').lstrip('+'),
                    '水平精度': horizontal_accuracy,
                    '垂直精度': vertical_accuracy
                }
                
                # 验证数据有效性
                if all(value == '' for key, value in metadata.items() if key != '照片名称'):
                    print(f"警告: {jpg_path.name} 未找到有效元数据")
                    return None
                    
                return metadata
                
        except Exception as e:
            print(f"错误: 处理 {jpg_path.name} 时出错 ({str(e)})")
            return None
        finally:
            if temp_jpg and temp_jpg.exists():
                try:
                    temp_jpg.unlink()
                except Exception:
                    pass

    def save_to_txt(self, data: List[Dict[str, str]], folder_path: Union[str, Path]) -> None:
        """
        将元数据保存为pos.txt文件
        
        Args:
            data: 元数据列表
            folder_path: 输出文件夹路径
            
        Notes:
            - 使用固定的pos.txt文件名
            - UTF-8编码保存
            - CSV格式（逗号分隔）
        """
        if not data:
            return
            
        output_path = Path(folder_path) / "pos.txt"
        
        with output_path.open('w', encoding='utf-8') as txtfile:
            # 写入表头
            txtfile.write(','.join(self.fieldnames) + '\n')
            
            # 写入数据行
            for row in data:
                if row:
                    line = ','.join(str(row[field]) for field in self.fieldnames)
                    txtfile.write(line + '\n')
        
        print(f"已生成: {output_path}")

    @staticmethod
    def find_subfolders(base_dir: Union[str, Path]) -> List[Path]:
        """
        查找所有子文件夹
        
        Args:
            base_dir: 基础目录路径
            
        Returns:
            List[Path]: 找到的子文件夹路径列表
        """
        subfolders = []
        base_dir = Path(base_dir)
        
        if not base_dir.is_dir():
            return subfolders
        
        try:
            for item in base_dir.iterdir():
                if item.is_dir():
                    subfolders.append(item)
        except Exception as e:
            print(f"警告: 搜索文件夹时出错 ({str(e)})")
        
        return subfolders

    def process_folder(self, folder_path: Union[str, Path]) -> None:
        """
        处理单个文件夹中的所有JPG文件
        
        Args:
            folder_path: 待处理的文件夹路径
        """
        folder_path = Path(folder_path)
        
        if not folder_path.is_dir():
            print(f"错误: {folder_path} 不是有效目录")
            return
        
        # 收集所有JPG文件
        jpg_files = list(folder_path.glob('*.jpg')) + list(folder_path.glob('*.JPG'))
        
        if not jpg_files:
            print(f"警告: {folder_path} 中未找到JPG文件")
            return
            
        print(f"\n处理文件夹: {folder_path.name}")
        metadata_list = []
        
        # 使用进度条处理文件
        for jpg_file in tqdm(jpg_files, desc="提取元数据"):
            metadata = self.extract_metadata(jpg_file)
            if metadata:
                metadata_list.append(metadata)
                
        if metadata_list:
            self.save_to_txt(metadata_list, folder_path)
        else:
            print(f"警告: {folder_path.name} 中未提取到有效元数据")

    def process_all(self, root_dir: str = "main") -> None:
        """
        处理指定目录下所有子文件夹
        
        Args:
            root_dir: 根目录路径，默认为'main'
        """
        try:
            root_path = Path(root_dir)
            if not root_path.exists():
                print(f"错误: 未找到目录 - {root_dir}")
                return
                
            subfolders = self.find_subfolders(root_path)
            
            if not subfolders:
                print("未找到任何子文件夹")
                return
                
            print(f"找到 {len(subfolders)} 个子文件夹")
            
            for folder in subfolders:
                self.process_folder(folder)
                
            print("\n处理完成!")
            
        except Exception as e:
            print(f"错误: {str(e)}")
        finally:
            # 清理临时目录
            try:
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"警告: 清理临时文件失败 ({str(e)})")

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="DJI图像元数据提取工具")
    parser.add_argument("-d", "--directory",
                      default="main",
                      help="指定要处理的根目录路径（默认为'main'）")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print("DJI图像元数据提取工具")
    print("==================")
    print(f"处理目录: {args.directory}")
    
    processor = MetadataProcessor()
    processor.process_all(args.directory)

if __name__ == "__main__":
    main()