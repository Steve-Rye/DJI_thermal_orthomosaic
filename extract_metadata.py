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
- 所有包含'dji'、'GPS'、'image'或'rtk'关键字的XMP和EXIF标签（不区分大小写）
- 将所有匹配的标签及其值导出到txt文件，文件名作为第一列
"""

class MetadataProcessor:
    """图像元数据处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.temp_dir = self._create_temp_dir()
        # 用于存储所有发现的标签名称
        self.all_tags = set(['ImageName'])  # 始终包含图片名称
        
    def _create_temp_dir(self) -> Path:
        """
        创建临时工作目录
        
        返回值:
            Path: 临时目录路径
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

    def extract_metadata(self, jpg_path: Union[str, Path]) -> Optional[Dict[str, str]]:
        """
        从单个JPG文件中提取元数据
        
        参数:
            jpg_path: JPG文件路径
            
        返回值:
            Optional[Dict[str, str]]: 提取的元数据字典，提取失败返回None
        """
        temp_jpg = None
        try:
            jpg_path = Path(jpg_path)
            temp_jpg = self.temp_dir / f"temp_{jpg_path.name}"
            
            # 复制到临时目录
            shutil.copy2(str(jpg_path), str(temp_jpg))
            
            with pyexiv2.Image(str(temp_jpg)) as img:
                xmp_data = img.read_xmp()
                exif_data = img.read_exif()
                
                # 初始化元数据字典，添加图片名称
                metadata = {'ImageName': jpg_path.name}
                
                # 筛选关键字
                keywords = ['dji', 'gps', 'image', 'rtk']  # 添加rtk关键字
                
                # 处理XMP标签
                for tag, value in xmp_data.items():
                    tag_lower = tag.lower()
                    if any(keyword in tag_lower for keyword in keywords):
                        metadata[tag] = str(value).lstrip('+')  # 移除可能的前导加号
                        self.all_tags.add(tag)  # 记录标签名称

                # 处理EXIF标签
                for tag, value in exif_data.items():
                    tag_lower = tag.lower()
                    if any(keyword in tag_lower for keyword in keywords):
                        metadata[tag] = str(value).lstrip('+')  # 移除可能的前导加号
                        self.all_tags.add(tag)  # 记录标签名称
                
                # 验证是否找到任何元数据
                if len(metadata) <= 1:  # 只有ImageName
                    print(f"警告: {jpg_path.name} 中未找到匹配的元数据")
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
        将元数据保存为metadata.txt文件
        
        参数:
            data: 元数据列表
            folder_path: 输出文件夹路径
        """
        if not data:
            return
            
        output_path = Path(folder_path) / "metadata.txt"
        
        # 构建字段列表，确保ImageName为第一列
        other_tags = sorted(list(self.all_tags - {'ImageName'}))  # 移除ImageName并对其他标签排序
        fieldnames = ['ImageName'] + other_tags  # 将ImageName放在开头
        
        print(f"\n发现的标签数量: {len(fieldnames)}")
        
        with output_path.open('w', encoding='utf-8') as txtfile:
            # 写入表头
            txtfile.write(','.join(fieldnames) + '\n')
            
            # 写入数据行
            for row in data:
                values = []
                for field in fieldnames:
                    values.append(str(row.get(field, '')))  # 如果标签不存在则使用空字符串
                txtfile.write(','.join(values) + '\n')
        
        print(f"已生成: {output_path}")

    @staticmethod
    def find_subfolders(base_dir: Union[str, Path]) -> List[Path]:
        """
        查找所有子文件夹
        
        参数:
            base_dir: 基础目录路径
            
        返回值:
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
        
        参数:
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
        
        参数:
            root_dir: 根目录路径，默认为'main'
        """
        try:
            root_path = Path(root_dir)
            if not root_path.exists():
                print(f"错误: 未找到目录 - {root_dir}")
                return
                
            subfolders = self.find_subfolders(root_path)
            
            if not subfolders:
                # 如果没有子文件夹，直接处理当前目录
                print("未找到子文件夹，处理当前目录")
                self.process_folder(root_path)
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