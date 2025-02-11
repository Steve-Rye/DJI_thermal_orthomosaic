import os
import pyexiv2
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from tqdm import tqdm

"""
图像元数据批量复制工具

功能描述:
---------
遍历main目录下的所有子文件夹，将每个子文件夹中input_dir下的JPG图像元数据
复制到对应的out_dir下的TIFF图像中

工作流程:
--------
1. 扫描main目录下的所有子文件夹
2. 在每个子文件夹中:
   - 从input_dir读取JPG文件
   - 在out_dir中查找对应的TIFF文件
   - 复制元数据
"""

class MetadataCopier:
    """元数据复制器"""
    
    @staticmethod
    def find_image_pairs(src_dir: Path, dst_dir: Path) -> List[Tuple[Path, Path]]:
        """
        查找源目录和目标目录中的对应图像对
        
        Args:
            src_dir: 源目录路径（JPG文件）
            dst_dir: 目标目录路径（TIFF文件）
            
        Returns:
            List[Tuple[Path, Path]]: 匹配的图像对列表 [(jpg_path, tiff_path), ...]
        """
        # 获取所有JPG文件(不区分大小写)
        jpg_files = list(src_dir.glob('*.[Jj][Pp][Gg]'))
        if not jpg_files:
            print(f"警告: {src_dir} 中未找到JPG文件")
            return []
            
        # 获取所有TIFF文件
        tiff_files = {
            f.stem: f for f in dst_dir.glob('*.tif*')
        }
        
        # 匹配文件对
        pairs = []
        for jpg_file in jpg_files:
            tiff_file = tiff_files.get(jpg_file.stem)
            if tiff_file:
                pairs.append((jpg_file, tiff_file))
            else:
                print(f"警告: 未找到与 {jpg_file.name} 对应的TIFF文件")
                
        return pairs

    def copy_metadata(self, src_path: Path, dst_path: Path) -> bool:
        """
        复制元数据从JPG到TIFF
        
        Args:
            src_path: 源JPG文件路径
            dst_path: 目标TIFF文件路径
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 读取源文件元数据
            with pyexiv2.Image(str(src_path)) as src_img:
                exif_data = src_img.read_exif()
                xmp_data = src_img.read_xmp()
                
            # 写入目标文件
            with pyexiv2.Image(str(dst_path)) as dst_img:
                # 写入EXIF数据
                if exif_data:
                    dst_img.modify_exif(exif_data)
                
                # 写入XMP数据
                if xmp_data:
                    dst_img.modify_xmp(xmp_data)
                    
            return True
            
        except Exception as e:
            print(f"错误: 处理 {src_path.name} -> {dst_path.name} 时出错 ({str(e)})")
            return False

    def process_single_folder(self, folder_path: Path) -> None:
        """
        处理单个子文件夹
        
        Args:
            folder_path: 子文件夹路径
        """
        input_dir = folder_path / "input_dir"
        out_dir = folder_path / "out_dir"
        
        # 验证目录
        if not input_dir.is_dir():
            print(f"跳过: {folder_path.name} - input_dir不存在")
            return
            
        if not out_dir.is_dir():
            print(f"跳过: {folder_path.name} - out_dir不存在")
            return
            
        print(f"\n处理文件夹: {folder_path.name}")
        print(f"input_dir: {input_dir}")
        print(f"out_dir: {out_dir}")
        
        # 查找匹配的文件对
        image_pairs = self.find_image_pairs(input_dir, out_dir)
        
        if not image_pairs:
            print(f"警告: {folder_path.name} 中未找到匹配的图像对")
            return
            
        print(f"找到 {len(image_pairs)} 对匹配的图像")
        
        # 处理所有文件对
        success_count = 0
        with tqdm(image_pairs, desc=f"复制元数据 - {folder_path.name}") as pbar:
            for src_file, dst_file in pbar:
                if self.copy_metadata(src_file, dst_file):
                    success_count += 1
                    
        print(f"完成 {folder_path.name}: 成功 {success_count}/{len(image_pairs)}")

    def process_all(self, main_dir: str = "main") -> None:
        """
        处理main目录下所有子文件夹
        
        Args:
            main_dir: main目录路径，默认为'main'
        """
        main_path = Path(main_dir)
        
        if not main_path.is_dir():
            print(f"错误: main目录不存在 - {main_dir}")
            return
            
        # 获取所有子文件夹
        subfolders = [f for f in main_path.iterdir() if f.is_dir()]
        
        if not subfolders:
            print("未找到任何子文件夹")
            return
            
        print(f"找到 {len(subfolders)} 个子文件夹")
        
        # 处理每个子文件夹
        for folder in subfolders:
            self.process_single_folder(folder)
            
        print("\n所有处理完成!")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="图像元数据批量复制工具")
    parser.add_argument("-m", "--main",
                      default="main",
                      help="main目录路径（默认为'main'）")
    
    args = parser.parse_args()
    
    print("图像元数据批量复制工具")
    print("===================")
    print(f"Main目录: {args.main}")
    
    copier = MetadataCopier()
    copier.process_all(args.main)

if __name__ == "__main__":
    main()