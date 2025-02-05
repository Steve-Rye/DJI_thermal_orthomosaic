from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
import argparse

"""
TIFF转JPG文件重命名工具

功能描述:
---------
批量将指定目录及其子目录中的out_dir目录下TIFF文件重命名为JPG格式。
此工具主要用于将热像图处理后的TIFF文件转换为可导入pix4Dmapper的JPG格式。

使用方法:
--------
默认处理main目录:
    python rename_tiff2jpg.py

指定其他目录:
    python rename_tiff2jpg.py -d your_directory_path

工作流程:
--------
1. 扫描指定目录下所有子文件夹
2. 在每个子文件夹中查找out_dir目录
3. 将out_dir中的.tiff文件重命名为.jpg文件

注意事项:
--------
- 只修改文件扩展名，不改变文件内容
- 原始TIFF文件将被重命名，不保留副本
- 处理完成后会显示成功和失败的文件数量
"""

class FileRenamer:
    """文件重命名处理器"""
    
    def __init__(self):
        """初始化处理器，设置计数器"""
        self.processed_count = 0
        self.error_count = 0

    def find_subfolders(self, root_dir: Path) -> List[Path]:
        """
        查找所有子文件夹
        
        Args:
            root_dir: 根目录路径
            
        Returns:
            List[Path]: 找到的文件夹路径列表
            
        Notes:
            递归搜索所有子目录
        """
        subfolders = []
        try:
            for path in root_dir.rglob('*'):
                if path.is_dir():
                    subfolders.append(path)
        except Exception as e:
            print(f"错误: 目录扫描失败 - {str(e)}")
            
        return subfolders

    def process_out_dir(self, out_dir: Path) -> None:
        """
        处理out_dir目录中的TIFF文件
        
        Args:
            out_dir: out_dir目录路径
            
        Notes:
            将所有.tiff文件重命名为.jpg文件
        """
        try:
            # 获取所有TIFF文件
            tiff_files = list(out_dir.glob('*.tiff'))
            
            if not tiff_files:
                return
                
            print(f"\n处理目录: {out_dir}")
            print(f"找到 {len(tiff_files)} 个TIFF文件")
            
            # 使用进度条处理文件
            for tiff_file in tqdm(tiff_files, desc="重命名文件"):
                try:
                    # 构造新文件名
                    jpg_file = tiff_file.with_suffix('.jpg')
                    
                    # 重命名文件
                    tiff_file.rename(jpg_file)
                    self.processed_count += 1
                    
                except Exception as e:
                    print(f"错误: 重命名失败 - {tiff_file.name}")
                    print(f"     原因: {str(e)}")
                    self.error_count += 1
                    
        except Exception as e:
            print(f"错误: 处理目录失败 - {out_dir}")
            print(f"     原因: {str(e)}")

    def process_folder(self, folder: Path) -> None:
        """
        处理单个文件夹
        
        Args:
            folder: 文件夹路径
        """
        try:
            # 查找out_dir目录
            out_dir = folder / "out_dir"
            if out_dir.exists():
                self.process_out_dir(out_dir)
            
        except Exception as e:
            print(f"错误: 处理文件夹失败 - {folder.name}")
            print(f"     原因: {str(e)}")

    def process_all(self, root_dir: Path) -> None:
        """
        处理所有符合条件的文件夹
        
        Args:
            root_dir: 根目录路径
        """
        if not root_dir.exists():
            print(f"错误: 根目录不存在 - {root_dir}")
            return
            
        print("开始扫描目录...")
        subfolders = self.find_subfolders(root_dir)
        
        if not subfolders:
            print("未找到任何子文件夹")
            return
            
        valid_folders = sum(1 for f in subfolders if (f / "out_dir").exists())
        print(f"\n找到 {valid_folders} 个包含out_dir的文件夹")
        
        # 处理每个文件夹
        for folder in subfolders:
            self.process_folder(folder)
            
        # 打印统计信息
        print("\n处理完成!")
        print(f"成功重命名: {self.processed_count} 个文件")
        print(f"处理失败: {self.error_count} 个文件")

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="TIFF转JPG文件重命名工具")
    parser.add_argument("-d", "--directory",
                      default="main",
                      help="指定要处理的根目录路径（默认为'main'）")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print("TIFF转JPG文件重命名工具")
    print("======================")
    print(f"处理目录: {args.directory}")
    
    # 设置根目录
    root_dir = Path.cwd() / args.directory
    
    renamer = FileRenamer()
    renamer.process_all(root_dir)

if __name__ == "__main__":
    main()