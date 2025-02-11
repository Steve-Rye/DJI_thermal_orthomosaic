import os
import argparse
from extract_metadata import MetadataProcessor
from jpg2tiff import ImageProcessor
from copy_metadata import MetadataCopier

"""
DJI 热红外图像处理工具

功能描述:
---------
按顺序执行以下处理:
1. 提取图像元数据 (extract_metadata.py)
2. JPG转换为TIFF (jpg2tiff.py)
3. 复制元数据到TIFF (copy_metadata.py)
"""

class ProcessManager:
    """处理管理器"""
    
    def __init__(self, directory: str):
        """
        初始化处理管理器
        
        参数:
            directory: 要处理的目录路径
        """
        self.directory = directory

    def run_all(self) -> None:
        """
        按顺序执行所有处理步骤
        """
        try:
            print("\n===== 步骤 1: 提取元数据 =====")
            metadata_processor = MetadataProcessor()
            metadata_processor.process_all(self.directory)

            print("\n===== 步骤 2: 转换图像格式 =====")
            image_processor = ImageProcessor()
            image_processor.process_subfolders(self.directory)

            print("\n===== 步骤 3: 复制元数据 =====")
            metadata_copier = MetadataCopier()
            metadata_copier.process_all(self.directory)

            print("\n===== 所有处理完成! =====")

        except Exception as e:
            print(f"\n错误: 处理过程中出现异常: {str(e)}")
            raise

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="DJI 热红外图像处理工具")
    parser.add_argument("-d", "--directory",
                       default="main",
                       help="指定要处理的根目录路径（默认为'main'）")

    # 解析命令行参数
    args = parser.parse_args()

    print("DJI 热红外图像处理工具")
    print("====================")
    print(f"处理目录: {args.directory}\n")

    # 验证目录是否存在
    if not os.path.exists(args.directory):
        print(f"错误: 目录不存在 - {args.directory}")
        return

    # 创建处理管理器并执行
    try:
        manager = ProcessManager(args.directory)
        manager.run_all()
    except Exception as e:
        print(f"\n处理失败: {str(e)}")
        return

if __name__ == "__main__":
    main()