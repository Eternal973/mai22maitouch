import os
import re
import argparse
from pathlib import Path

def replace_svg_color(input_path, output_suffix="_touch"):
    """
    处理SVG文件：将fill:#000000替换为fill:#00ff00
    
    Args:
        input_path: 输入路径（文件或文件夹）
        output_suffix: 输出文件后缀
    """
    
    # 获取所有SVG文件
    svg_files = []
    if os.path.isfile(input_path) and input_path.lower().endswith('.svg'):
        svg_files = [input_path]
    elif os.path.isdir(input_path):
        svg_files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                    if f.lower().endswith('.svg')]
    else:
        print(f"错误：{input_path} 不是有效的文件或文件夹")
        return
    
    if not svg_files:
        print("未找到SVG文件")
        return
    
    processed_count = 0
    
    for svg_file in svg_files:
        try:
            # 读取文件内容
            with open(svg_file, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 替换颜色代码（使用正则表达式确保精确匹配）
            # 匹配 fill:#000000 或 fill: #000000（可能有空格）
            pattern = r'fill:\s*#000000'
            new_content = re.sub(pattern, 'fill:#00ff00', content)
            
            # 如果内容有变化，则保存新文件
            if new_content != content:
                # 生成输出文件名
                file_path = Path(svg_file)
                output_file = file_path.parent / f"{file_path.stem}{output_suffix}{file_path.suffix}"
                
                # 写入新文件
                with open(output_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                
                print(f"处理成功：{svg_file} -> {output_file}")
                processed_count += 1
            else:
                print(f"未找到匹配项：{svg_file}")
                
        except Exception as e:
            print(f"处理文件 {svg_file} 时出错：{str(e)}")
    
    print(f"\n处理完成！共成功处理 {processed_count} 个文件")

def main():
    parser = argparse.ArgumentParser(description='批量替换SVG文件中的颜色代码')
    parser.add_argument('path', help='SVG文件路径或包含SVG文件的文件夹路径')
    parser.add_argument('-s', '--suffix', default='_touch', 
                       help='输出文件后缀（默认：_touch）')
    
    args = parser.parse_args()
    
    # 检查路径是否存在
    if not os.path.exists(args.path):
        print(f"错误：路径 {args.path} 不存在")
        return
    
    replace_svg_color(args.path, args.suffix)

if __name__ == "__main__":
    # 如果直接运行脚本（而不是作为模块导入），执行主函数
    main()
