import serial
import threading
import time
from datetime import datetime

# Serial port configurations
COM3 = 'COM23'  # Game program
COM13 = 'COM33'  # Touchscreen controller
BAUD_RATE = 9600

# Default all-zero state for the game (14 bytes including start/end markers)
ALL_ZERO_STATE = bytes([
    0x28,       # Start byte '('
    0x40, 0x40, 0x40, 0x40,  # P1 bytes (A1-A8, B1-B8, C all 0)
    0x40, 0x40,  # Padding '@@'
    0x40, 0x40, 0x40, 0x40,  # P2 bytes (ignored)
    0x40, 0x40,  # Padding '@@'
    0x29         # End byte ')'
])

class TouchBridge:
    def __init__(self):
        self.active = False
        self.com3 = None
        self.com13 = None
        self.lock = threading.Lock()
        self.received_commands = []
        self.command_log_file = "com3_commands.log"
        # 存储XXkY映射关系的字典
        self.key_mappings = {}  # 格式: {"XX": bytes([Y])}
        
    def log_command(self, data):
        """记录所有接收到的COM3指令"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] Received: {data}\n"
        self.received_commands.append(log_entry)
        
        with open(self.command_log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(log_entry.strip())

    def transform_touch_data(self, raw_data):
        """
        将mai2格式的触摸数据转换为mai格式
        输入: mai2格式的bytes (9字节，以b'\x28'开头，b'\x29'结尾)
        输出: mai格式的bytes (14字节，以b'\x28'开头，b'\x29'结尾)
        """
        # 验证输入数据
        if len(raw_data) != 9 or raw_data[0] != 0x28 or raw_data[8] != 0x29:
            raise ValueError("Invalid mai2 input data format")
    
        # 初始化mai输出数据 (全初始化为0x40 '@')
        mai_data = [0x40] * 14
        mai_data[0] = 0x28  # 起始字节 '('
        mai_data[13] = 0x29  # 结束字节 ')'
    
        # mai2到mai的映射关系 (mai2区域 -> mai字节/位)
        zone_mapping = {
            # A区映射 (P1)
            'A1': (1, 0), 'A2': (1, 2), 'A3': (2, 0), 'A4': (2, 2),
            'A5': (3, 0), 'A6': (3, 2), 'A7': (4, 0), 'A8': (4, 2),
            # B区映射 (P1)
            'B1': (1, 1), 'B2': (1, 3), 'B3': (2, 1), 'B4': (2, 3),
            'B5': (3, 1), 'B6': (3, 3), 'B7': (4, 1), 'B8': (4, 3),
            # C区映射 (合并C1和C2)
            'C1': (4, 4), 'C2': (4, 4)  # 两者都映射到同一位
        }
    
        # mai2的区域定义 (字节位置, 位位置): 区域名称
        mai2_zones = {
            # A区
            (7, 0): 'A1', (7, 1): 'A2', (7, 2): 'A3', (7, 3): 'A4',
            (7, 4): 'A5', (6, 0): 'A6', (6, 1): 'A7', (6, 2): 'A8',
            # B区
            (6, 3): 'B1', (6, 4): 'B2', (5, 0): 'B3', (5, 1): 'B4',
            (5, 2): 'B5', (5, 3): 'B6', (5, 4): 'B7', (4, 0): 'B8',
            # C区
            (4, 1): 'C1', (4, 2): 'C2'
        }
    
        # 处理mai2数据中的每个区域
        for byte_pos in range(1, 8):  # 只处理字节1-7
            byte = raw_data[byte_pos]
            for bit_pos in range(8):
                if byte & (1 << bit_pos):
                    zone = mai2_zones.get((byte_pos, bit_pos))
                    if zone in zone_mapping:
                        mai_byte, mai_bit = zone_mapping[zone]
                        mai_data[mai_byte] |= (1 << mai_bit)
    
        return bytes(mai_data)
    
    def handle_com3_to_com13(self):
        """Handle communication from game to touch controller"""
        while True:
            try:
                if self.com3.in_waiting > 0:
                    data = self.com3.read(self.com3.in_waiting)
                    self.log_command(data)
                    
                    # 处理特殊格式{XXkY}的命令（建立映射关系）
                    if len(data) == 6 and data.startswith(b'{') and data.endswith(b'}'):
                        if data[3] == ord('k'):  # 第三位是k
                            prefix = data[1:3].decode('ascii')  # 提取XX
                            suffix = data[4:5]  # 提取Y
                            # 存储映射关系
                            self.key_mappings[prefix] = suffix
                            # 响应(xx  )
                            response = b'(' + data[1:3] + b'  )'
                            with self.lock:
                                self.com3.write(response)
                            print(f"Registered mapping: {prefix} -> {suffix}")
                            print(f"Responded to mapping command: {data} -> {response}")
                            continue
                    
                    # 处理查询格式{XXth}的命令
                    if len(data) == 6 and data.startswith(b'{') and data.endswith(b'}'):
                        if data[3:5] == b'th':  # 第4-5位是th
                            prefix = data[1:3].decode('ascii')  # 提取XX
                            # 查找映射关系
                            if prefix in self.key_mappings:
                                y_value = self.key_mappings[prefix]
                                # 响应(xx Y)
                                response = b'(' + data[1:3] + b' ' + y_value + b')'
                                with self.lock:
                                    self.com3.write(response)
                                print(f"Responded to query: {data} -> {response}")
                            else:
                                print(f"No mapping found for prefix: {prefix}")
                            continue
                    
                    # 处理标准命令
                    if b'{STAT}' in data:
                        with self.lock:
                            self.active = True
                            self.com3.write(ALL_ZERO_STATE)
                            self.com13.write(b'{STAT}')
                            print("Handled STAT command")
                    elif b'{HALT}' in data:
                        with self.lock:
                            self.active = False
                            self.com13.write(b'{HALT}')
                            print("Handled HALT command")
                            
            except Exception as e:
                print(f"Error in COM3 handler: {e}")
                time.sleep(1)

    def handle_com13_to_com3(self):
        """Handle communication from touch controller to game"""
        while True:
            try:
                if self.com13.in_waiting > 0:
                    data = self.com13.read_until(b'\x29')  # Read until ')'
                    if data.startswith(b'\x28') and len(data) == 9:  # Valid packet
                        with self.lock:
                            if self.active:
                                transformed = self.transform_touch_data(data)
                                self.com3.write(transformed)
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                print(f"[{timestamp}] Transformed Data Sent: {transformed}")
                    elif data in (b'{STAT}', b'{HALT}'):
                        with self.lock:
                            self.com3.write(data)
            except Exception as e:
                print(f"Error in COM13 handler: {e}")
                time.sleep(1)

    def run(self):
        try:
            with serial.Serial(COM3, BAUD_RATE, timeout=1) as self.com3, \
                 serial.Serial(COM13, BAUD_RATE, timeout=1) as self.com13:
                
                print(f"Touch bridge started at {datetime.now()}")
                print(f"COM3: {self.com3.name}, COM13: {self.com13.name}")
                print("All received COM3 commands will be logged to com3_commands.log")
                print("Monitoring for commands:")
                print("- {STAT}: Activate bridge and send zero state")
                print("- {HALT}: Deactivate bridge")
                print("- {XXkY}: Register mapping (XX -> Y), respond with (XX  )")
                print("- {XXth}: Query mapping for XX, respond with (XX Y) if found")
                
                with open(self.command_log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n===== Session started at {datetime.now()} =====\n")
                
                com3_thread = threading.Thread(
                    target=self.handle_com3_to_com13, daemon=True)
                com13_thread = threading.Thread(
                    target=self.handle_com13_to_com3, daemon=True)
                
                com3_thread.start()
                com13_thread.start()
                
                while True:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\nStopping touch bridge...")
            with open(self.command_log_file, "a", encoding="utf-8") as f:
                f.write(f"===== Session ended at {datetime.now()} =====\n")
                f.write(f"Total commands received: {len(self.received_commands)}\n")
                f.write(f"Current mappings: {self.key_mappings}\n")
        except Exception as e:
            print(f"Error: {e}")
            with open(self.command_log_file, "a", encoding="utf-8") as f:
                f.write(f"Error occurred: {e}\n")
        finally:
            if hasattr(self, 'com3') and self.com3:
                self.com3.close()
            if hasattr(self, 'com13') and self.com13:
                self.com13.close()

if __name__ == "__main__":
    bridge = TouchBridge()
    bridge.run()
