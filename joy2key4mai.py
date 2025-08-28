import pygame
import time
from pynput.keyboard import Controller
from collections import deque

# 初始化pygame
pygame.init()

# 创建键盘控制器
keyboard = Controller()

# 初始化游戏手柄
pygame.joystick.init()
joystick_count = pygame.joystick.get_count()

# 检查是否有连接的手柄设备
if joystick_count == 0:
    print("未检测到设备")
    exit()

# 获取第一个手柄并初始化
joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"检测到设备: {joystick.get_name()}")

# 手柄按钮到键盘按键的映射配置 (按钮ID: 键盘按键)
# 默认为SEGA I/O 4及兼容协议的默认映射
button_mapping = {
    2: 'w',        # 1P 1号键
    3: 'e',        # 1P 2号键
    0: 'd',        # 1P 3号键
    15: 'c',       # 1P 4号键
    14: 'x',       # 1P 5号键
    13: 'z',       # 1P 6号键
    12: 'a',       # 1P 7号键
    11: 'q',       # 1P 8号键
    '''
    #可根据需要添加
    19: 'num 8',   # 2P 1号键
    20: 'num 9',   # 2P 2号键
    17: 'num 6',   # 2P 3号键
    32: 'num 3',   # 2P 4号键
    31: 'num 2',   # 2P 5号键
    30: 'num 1',   # 2P 6号键
    29: 'num 4',   # 2P 7号键
    28: 'num 7',   # 2P 8号键
    '''
}

# 输入延迟设置（毫秒）
# 由于旧框尾判特性，不建议高于25ms
delay_ms = 20

# 延迟事件缓冲区
delayed_buffer = deque()

# 上次处理时间
last_process_time = 0

def handle_button(button_id, pressed):
    """
    处理按钮事件，映射到键盘按键
    
    参数:
        button_id: 手柄按钮ID
        pressed: 按钮是否被按下
    """
    if button_id in button_mapping:
        # 获取映射的键盘按键
        key = button_mapping[button_id]
        
        # 处理按键逻辑 (按下或释放)
        if pressed:
            keyboard.press(key)
            # print(f"按下: 按钮{button_id} -> 键盘'{key}'")
        else:
            keyboard.release(key)
            # print(f"释放: 按钮{button_id} -> 键盘'{key}'")


# 加载完配置后主程序开始
print("手柄按键监听已启动，按Ctrl+C退出")

try:
    while True:
        # 获取当前时间（毫秒）
        current_time = time.time() * 1000  
        
        # 处理所有pygame事件
        for event in pygame.event.get():
            # 处理按钮按下事件
            if event.type == pygame.JOYBUTTONDOWN:
                release_time = current_time + delay_ms
                delayed_buffer.append(('press', event.button, release_time))
            
            # 处理按钮释放事件
            elif event.type == pygame.JOYBUTTONUP:
                release_time = current_time + delay_ms
                delayed_buffer.append(('release', event.button, release_time))
        
        # 处理延迟缓冲区中到期的事件
        while delayed_buffer and current_time >= delayed_buffer[0][2]:
            event_type, button_id, _ = delayed_buffer.popleft()

            # 根据事件类型处理按键
            if event_type == 'press':
                handle_button(button_id, True)
            elif event_type == 'release':
                handle_button(button_id, False)
        
        # 短暂休眠以减少CPU占用
        time.sleep(0.001)  

# 捕获Ctrl+C中断信号
except KeyboardInterrupt:
    print("\n程序被用户中断")

# 确保资源被正确释放
finally:
    pygame.quit()
    print("\n程序已退出")
