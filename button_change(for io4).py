import pygame
import time
from pynput.keyboard import Controller
from collections import deque

pygame.init()
keyboard = Controller()

pygame.joystick.init()
joystick_count = pygame.joystick.get_count()

if joystick_count == 0:
    print("未检测到设备")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"检测到设备: {joystick.get_name()}")

button_mapping = {
    3: 'e',      
    2: 'w',      
    0: 'd',      
    11: 'q',      
    15: 'c', 
    14: 'x',  
    13: 'z',
    12: 'a',
}


delay_ms = 20  # 输入延迟（由于旧框尾判特性，不建议高于25ms）
delayed_buffer = deque()
last_process_time = 0

def handle_button(button_id, pressed):
    if button_id in button_mapping:
        key = button_mapping[button_id]
        
        logical_pressed = not pressed
        
        if logical_pressed:
            keyboard.press(key)
            print(f"{button_id} -> {key}")
        else:
            keyboard.release(key)
            print(f"{button_id} -> {key}")


print("start")
try:
    while True:
        current_time = time.time() * 1000  
        
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                release_time = current_time + delay_ms
                delayed_buffer.append(('press', event.button, release_time))
            elif event.type == pygame.JOYBUTTONUP:
                release_time = current_time + delay_ms
                delayed_buffer.append(('release', event.button, release_time))
        
        while delayed_buffer and current_time >= delayed_buffer[0][2]:
            event_type, button_id, _ = delayed_buffer.popleft()
            
            if event_type == 'press':
                handle_button(button_id, True)
            elif event_type == 'release':
                handle_button(button_id, False)
        
        time.sleep(0.001)  

except KeyboardInterrupt:
    print("\n")
finally:
    pygame.quit()