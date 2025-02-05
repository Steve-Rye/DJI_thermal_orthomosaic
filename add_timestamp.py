from datetime import datetime
from pathlib import Path
from PIL import Image, ExifTags
from typing import Optional, List
from tqdm import tqdm
import argparse

"""
DJI图像文件时间戳添加工具

功能描述:
---------
从图像EXIF数据中提取拍摄时间，并将其添加到文件名中。
支持批量处理指定目录下所有子文件夹中的JPG图像。

文件名格式:
----------
输入: DJI_XXXX_YYY.JPG
输出: DJI_YYYYMMDDHHMMSS_XXX_YYY.JPG

示例:
----
输入: DJI_0001_001.JPG
输出: DJI_20250201143022_0001_001.JPG
"""

class TimestampProcessor:
    """图像时间戳处理器"""

    def __init__(self):
        """初始化处理器"""
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def get_exif_date(self, image_path: Path) -> Optional[str]:
        """
        从图像中提取EXIF拍摄时间
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            Optional[str]: EXIF日期时间字符串，格式为'YYYY:MM:DD HH:MM:SS'
            
        Notes:
            使用PIL库读取EXIF数据，查找DateTimeOriginal标签
        """
        if not image_path.exists():
            return None
            
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return None
                    
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        return value
                        
        except Exception as e:
            if "不存在" not in str(e):  # 忽略文件不存在的错误提示
                print(f"警告: 读取EXIF数据失败 - {image_path.name}")
                print(f"     原因: {str(e)}")
        return None

    def format_timestamp(self, date_str: str) -> Optional[str]:
        """
        将EXIF时间格式化为文件名格式
        
        Args:
            date_str: EXIF格式的时间字符串 (YYYY:MM:DD HH:MM:SS)
            
        Returns:
            Optional[str]: 格式化后的时间戳 (YYYYMMDDHHMMSS)
        """
        try:
            if date_str:
                dt = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                return dt.strftime('%Y%m%d%H%M%S')
        except ValueError as e:
            print(f"警告: 时间格式化失败 - {date_str}")
            print(f"     原因: {str(e)}")
        return None

    def construct_new_filename(self, file_path: Path, timestamp: str) -> Optional[Path]:
        """
        构造包含时间戳的新文件名
        
        Args:
            file_path: 原始文件路径
            timestamp: 格式化后的时间戳
            
        Returns:
            Optional[Path]: 新的文件路径，如果无法构造则返回None
            
        Notes:
            保持原始文件名结构，在适当位置插入时间戳
        """
        try:
            parts = file_path.stem.split('_')
            if len(parts) >= 3:
                new_name = f"{parts[0]}_{timestamp}_{'_'.join(parts[1:])}"
                return file_path.parent / f"{new_name}{file_path.suffix}"
        except Exception as e:
            print(f"警告: 文件名构造失败 - {file_path.name}")
            print(f"     原因: {str(e)}")
        return None

    def process_single_image(self, image_path: Path) -> bool:
        """
        处理单个图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            bool: 处理是否成功
            
        处理步骤:
        1. 读取EXIF时间
        2. 格式化时间戳
        3. 构造新文件名
        4. 重命名文件
        """
        try:
            if not image_path.exists():
                return False
                
            # 提取EXIF时间
            date_str = self.get_exif_date(image_path)
            if not date_str:
                self.skipped_count += 1
                return False

            # 格式化时间戳
            timestamp = self.format_timestamp(date_str)
            if not timestamp:
                print(f"跳过: {image_path.name} (时间格式无效)")
                self.skipped_count += 1
                return False

            # 构造新文件名
            new_path = self.construct_new_filename(image_path, timestamp)
            if not new_path or new_path == image_path:
                print(f"跳过: {image_path.name} (文件名未改变)")
                self.skipped_count += 1
                return False

            # 重命名文件
            image_path.rename(new_path)
            self.processed_count += 1
            return True

        except Exception as e:
            if "不存在" not in str(e):  # 忽略文件不存在的错误提示
                print(f"错误: 处理失败 - {image_path.name}")
                print(f"     原因: {str(e)}")
                self.error_count += 1
            return False

    def process_folder(self, folder_path: Path) -> None:
        """
        处理文件夹中的所有JPG图像
        
        Args:
            folder_path: 文件夹路径
        """
        if not folder_path.is_dir():
            print(f"错误: 无效的文件夹路径 - {folder_path}")
            return

        print(f"\n处理文件夹: {folder_path}")
        
        # 获取所有JPG文件并排序
        jpg_files = sorted(
            list(folder_path.glob('*.jpg')) + list(folder_path.glob('*.JPG')),
            key=lambda x: x.name
        )
        
        if not jpg_files:
            print("未找到JPG文件")
            return

        # 使用进度条处理文件
        for jpg_file in tqdm(jpg_files, desc="处理图像"):
            self.process_single_image(jpg_file)

    def find_and_process_folders(self, root_dir: str = "main") -> None:
        """
        查找并处理所有子文件夹
        
        Args:
            root_dir: 根目录路径，默认为'main'
        """
        root_path = Path(root_dir)
        if not root_path.exists():
            print(f"错误: 根目录不存在 - {root_dir}")
            return

        print("开始扫描目录...")
        folders = []
        
        # 递归查找所有文件夹并排序
        for path in sorted(root_path.rglob('*')):
            if path.is_dir():
                folders.append(path)

        if not folders:
            print("未找到任何子文件夹")
            return

        print(f"\n找到 {len(folders)} 个子文件夹")
        
        # 处理每个文件夹
        for folder in folders:
            self.process_folder(folder)

        # 打印统计信息
        print("\n处理完成!")
        print(f"成功处理: {self.processed_count} 个文件")
        print(f"跳过处理: {self.skipped_count} 个文件")
        print(f"处理失败: {self.error_count} 个文件")

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="DJI图像文件时间戳添加工具")
    parser.add_argument("-d", "--directory",
                       default="main",
                       help="指定要处理的根目录路径（默认为'main'）")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print("DJI图像文件时间戳添加工具")
    print("=========================")
    print(f"处理目录: {args.directory}")
    
    processor = TimestampProcessor()
    processor.find_and_process_folders(args.directory)

if __name__ == "__main__":
    main()