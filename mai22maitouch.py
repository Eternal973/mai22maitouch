import serial
import threading
import time
from datetime import datetime

# Serial port configurations
GOPI = 'COM33'  # Game out Python in
CIPO = 'COM13'  # Controller in Python out
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
        self.GOPI = None
        self.CIPO = None
        self.lock = threading.Lock()
        self.received_commands = []
        self.command_log_file = "GOPI_commands.log"
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
            (1, 0): 'A1', (1, 1): 'A2', (1, 2): 'A3', (1, 3): 'A4',
            (1, 4): 'A5', (2, 0): 'A6', (2, 1): 'A7', (2, 2): 'A8',
            # B区
            (2, 3): 'B1', (2, 4): 'B2', (3, 0): 'B3', (3, 1): 'B4',
            (3, 2): 'B5', (3, 3): 'B6', (3, 4): 'B7', (4, 0): 'B8',
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
    
    def handle_GOPI_to_CIPO(self):
        """Handle communication from game to touch controller"""
        while True:
            try:
                if self.GOPI.in_waiting > 0:
                    data = self.GOPI.read(self.GOPI.in_waiting)
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
                                self.GOPI.write(response)
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
                                    self.GOPI.write(response)
                                print(f"Responded to query: {data} -> {response}")
                            else:
                                print(f"No mapping found for prefix: {prefix}")
                            continue
                    
                    # 处理标准命令
                    if b'{STAT}' in data:
                        with self.lock:
                            self.active = True
                            self.GOPI.write(ALL_ZERO_STATE)
                            self.CIPO.write(b'{STAT}')
                            print("Handled STAT command")
                    elif b'{HALT}' in data:
                        with self.lock:
                            self.active = False
                            self.CIPO.write(b'{HALT}')
                            print("Handled HALT command")
                            
            except Exception as e:
                print(f"Error in GOPI handler: {e}")
                time.sleep(1)

    def handle_CIPO_to_GOPI(self):
        """Handle communication from touch controller to game"""
        while True:
            try:
                if self.CIPO.in_waiting > 0:
                    data = self.CIPO.read_until(b'\x29')  # Read until ')'
                    if data.startswith(b'\x28') and len(data) == 9:  # Valid packet
                        with self.lock:
                            if self.active:
                                transformed = self.transform_touch_data(data)
                                self.GOPI.write(transformed)
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                print(f"[{timestamp}] Transformed Data Sent: {transformed}")
                    elif data in (b'{STAT}', b'{HALT}'):
                        with self.lock:
                            self.GOPI.write(data)
            except Exception as e:
                print(f"Error in CIPO handler: {e}")
                time.sleep(1)

    def run(self):
        try:
            with serial.Serial(GOPI, BAUD_RATE, timeout=1) as self.GOPI, \
                 serial.Serial(CIPO, BAUD_RATE, timeout=1) as self.CIPO:
                
                print(f"Touch bridge started at {datetime.now()}")
                print(f"GOPI: {self.GOPI.name}, CIPO: {self.CIPO.name}")
                print("All received GOPI commands will be logged to GOPI_commands.log")
                print("Monitoring for commands:")
                print("- {STAT}: Activate bridge and send zero state")
                print("- {HALT}: Deactivate bridge")
                print("- {XXkY}: Register mapping (XX -> Y), respond with (XX  )")
                print("- {XXth}: Query mapping for XX, respond with (XX Y) if found")
                
                with open(self.command_log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n===== Session started at {datetime.now()} =====\n")
                
                GOPI_thread = threading.Thread(
                    target=self.handle_GOPI_to_CIPO, daemon=True)
                CIPO_thread = threading.Thread(
                    target=self.handle_CIPO_to_GOPI, daemon=True)
                
                GOPI_thread.start()
                CIPO_thread.start()
                
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
            if hasattr(self, 'GOPI') and self.GOPI:
                self.GOPI.close()
            if hasattr(self, 'CIPO') and self.CIPO:
                self.CIPO.close()

if __name__ == "__main__":
    bridge = TouchBridge()
    bridge.run()
