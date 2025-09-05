import socket
import time

class TouchSocketClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"Touch socket client initialized, sending to {host}:{port}")
        
    def send_touch_data(self, touched_points):
        """
        发送触摸数据
        touched_points: 被触摸的点ID列表，如 [1, 2, 11, 12]
        """
        # 直接将整数列表转换为字节数组
        data = bytes(touched_points)
        self.socket.sendto(data, (self.host, self.port))
        print(f"Sent data: {touched_points}")
        
    def close(self):
        self.socket.close()
        print("Client closed")

def parse_input(input_str):
    """
    解析用户输入，支持多种格式：
    - 空字符串: 返回空列表 []
    - 逗号分隔: "1,2,3" → [1,2,3]
    - 空格分隔: "1 2 3" → [1,2,3]
    - 混合分隔: "1, 2 3" → [1,2,3]
    """
    if not input_str.strip():
        return []
    
    # 替换所有分隔符为空格，然后分割
    cleaned = input_str.replace(',', ' ').replace(';', ' ')
    numbers = cleaned.split()
    
    try:
        return [int(num) for num in numbers if num.strip()]
    except ValueError:
        print("错误: 输入包含非数字字符")
        return None

def auto_mode_single(client, interval=0.1, reverse=False):
    """
    自动模式：依次发送单个触摸点
    """
    mode_name = "倒序单点" if reverse else "顺序单点"
    print(f"进入{mode_name}模式，按Ctrl+C中断")
    
    # 定义要循环的触摸点序列
    touch_sequence = [
        31,1,32,2,33,3,34,4,35,5,36,6,37,7,38,8,
        41,11,42,12,43,13,44,14,45,15,46,16,47,17,48,18,
        21,22
    ]
    
    if reverse:
        touch_sequence = touch_sequence[::-1]  # 反转序列
    
    try:
        while True:
            for point in touch_sequence:
                client.send_touch_data([point])
                time.sleep(interval)
                    
    except KeyboardInterrupt:
        print(f"\n{mode_name}模式已中断")
        client.send_touch_data([])  # 清空所有触摸点

def auto_mode_double(client, interval=0.1, reverse=False):
    """
    自动模式：重叠双点模式 [31,1] -> [1,32] -> [32,2]
    """
    mode_name = "倒序重叠双点" if reverse else "顺序重叠双点"
    print(f"进入{mode_name}模式，按Ctrl+C中断")
    
    # 定义要循环的触摸点序列
    touch_sequence = [
        31,1,32,2,33,3,34,4,35,5,36,6,37,7,38,8,
        41,11,42,12,43,13,44,14,45,15,46,16,47,17,48,18,
        21,22
    ]
    
    if reverse:
        touch_sequence = touch_sequence[::-1]  # 反转序列
    
    try:
        while True:
            # 重叠双点模式: [31,1] -> [1,32] -> [32,2] -> ...
            for i in range(len(touch_sequence) - 1):
                point1 = touch_sequence[i]
                point2 = touch_sequence[i + 1]
                client.send_touch_data([point1, point2])
                time.sleep(interval)
                    
    except KeyboardInterrupt:
        print(f"\n{mode_name}模式已中断")
        client.send_touch_data([])  # 清空所有触摸点

def parse_auto_command(command):
    """
    解析auto指令
    返回: (模式类型, 是否倒序)
    """
    parts = command.lower().split()
    if len(parts) == 1:
        return 1, False  # 默认模式
    
    try:
        mode = int(parts[1])
        reverse = False
        
        # 处理负数模式（倒序）
        if mode < 0:
            mode = abs(mode)
            reverse = True
            
        return mode, reverse
        
    except ValueError:
        print("错误: 无效的auto模式参数")
        return None, None

# 使用示例
if __name__ == "__main__":
    client = TouchSocketClient()
    
    print("触摸点测试客户端")
    print("输入格式说明:")
    print("- 输入数字，用逗号或空格分隔，如: 1,2,3 或 1 2 3")
    print("- 输入'auto': 自动测试")
    print("- 输入空行或'clear': 清空所有触摸点")
    print("- 输入'q': 退出程序")
    print("- 输入'help': 显示帮助")
    print("\n开始输入:")
    
    try:
        while True:
            user_input = input(">>> ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                break
            elif user_input.lower() in ['help', '?']:
                print("帮助:")
                print("  数字列表: 1,2,3 或 1 2 3")
                print("  自动模式:")
                print("    auto / auto 1: 顺序单点")
                print("    auto -1: 倒序单点")
                print("    auto 2: 重叠双点 ([31,1]→[1,32]→[32,2])")
                print("    auto -2: 倒序重叠双点")
                print("  清空: clear, c, 或直接回车")
                print("  退出: q, quit, exit")
                continue
            elif user_input.lower() in ['clear', 'c', '']:
                # 清空所有触摸点
                client.send_touch_data([])
                print("已清空所有触摸点")
                continue
            elif user_input.lower().startswith('auto'):
                # 解析auto指令
                mode, reverse = parse_auto_command(user_input)
                
                if mode is None:
                    continue
                    
                if mode == 1:
                    auto_mode_single(client, interval=0.1, reverse=reverse)
                elif mode == 2:
                    auto_mode_double(client, interval=0.1, reverse=reverse)
                else:
                    print("错误: 不支持的auto模式，支持1或2")
                continue
            
            # 解析用户输入
            points = parse_input(user_input)
            
            if points is not None:
                client.send_touch_data(points)
            else:
                print("请重新输入有效的数字")
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        client.close()
