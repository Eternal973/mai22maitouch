import serial
import threading
import time
from datetime import datetime
from collections import deque


GOPI = 'COM33'  
CIPO = 'COM13'  
BAUD_RATE = 9600


ALL_ZERO_STATE = bytes([
    0x28,       
    0x40, 0x40, 0x40, 0x40,  
    0x40, 0x40,  
    0x40, 0x40, 0x40, 0x40,  
    0x40, 0x40,  
    0x29         
])

class TouchBridge:
    def __init__(self):
        self.active = False
        self.GOPI = None
        self.CIPO = None
        self.lock = threading.Lock()
        self.received_commands = []
        self.command_log_file = "GOPI_commands.log"
        self.key_mappings = {}  
        
        
        self.delay_ms = 16  # 在这里输入你增加的输入延迟(不建议大于25)
        self.delayed_buffer = deque()  
        self.last_state = ALL_ZERO_STATE  

    def log_command(self, data):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] Received: {data}\n"
        self.received_commands.append(log_entry)
        
        with open(self.command_log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(log_entry.strip())

    def transform_touch_data(self, raw_data):
        if len(raw_data) != 9 or raw_data[0] != 0x28 or raw_data[8] != 0x29:
            raise ValueError("Invalid mai2 input data format")
    
        mai_data = [0x40] * 14
        mai_data[0] = 0x28
        mai_data[13] = 0x29
    
        zone_mapping = {
            'A1': (1, 0), 'A2': (1, 2), 'A3': (2, 0), 'A4': (2, 2),
            'A5': (3, 0), 'A6': (3, 2), 'A7': (4, 0), 'A8': (4, 2),
            'B1': (1, 1), 'B2': (1, 3), 'B3': (2, 1), 'B4': (2, 3),
            'B5': (3, 1), 'B6': (3, 3), 'B7': (4, 1), 'B8': (4, 3),
            'C1': (4, 4), 'C2': (4, 4)
        }
    
        mai2_zones = {
            (1, 0): 'A1', (1, 1): 'A2', (1, 2): 'A3', (1, 3): 'A4',
            (1, 4): 'A5', (2, 0): 'A6', (2, 1): 'A7', (2, 2): 'A8',
            (2, 3): 'B1', (2, 4): 'B2', (3, 0): 'B3', (3, 1): 'B4',
            (3, 2): 'B5', (3, 3): 'B6', (3, 4): 'B7', (4, 0): 'B8',
            (4, 1): 'C1', (4, 2): 'C2'
        }
    
        for byte_pos in range(1, 8):
            byte = raw_data[byte_pos]
            for bit_pos in range(8):
                if byte & (1 << bit_pos):
                    zone = mai2_zones.get((byte_pos, bit_pos))
                    if zone in zone_mapping:
                        mai_byte, mai_bit = zone_mapping[zone]
                        mai_data[mai_byte] |= (1 << mai_bit)
    
        return bytes(mai_data)
    
    def handle_GOPI_to_CIPO(self):
       
        while True:
            try:
                if self.GOPI.in_waiting > 0:
                    data = self.GOPI.read(self.GOPI.in_waiting)
                    self.log_command(data)
                    
                    if len(data) == 6 and data.startswith(b'{') and data.endswith(b'}'):
                        if data[3] == ord('k'):
                            prefix = data[1:3].decode('ascii')
                            suffix = data[4:5]
                            self.key_mappings[prefix] = suffix
                            response = b'(' + data[1:3] + b'  )'
                            with self.lock:
                                self.GOPI.write(response)
                            print(f"Registered mapping: {prefix} -> {suffix}")
                            continue
                    
                    if len(data) == 6 and data.startswith(b'{') and data.endswith(b'}'):
                        if data[3:5] == b'th':
                            prefix = data[1:3].decode('ascii')
                            if prefix in self.key_mappings:
                                y_value = self.key_mappings[prefix]
                                response = b'(' + data[1:3] + b' ' + y_value + b')'
                                with self.lock:
                                    self.GOPI.write(response)
                                print(f"Responded to query: {data} -> {response}")
                            continue
                    
                    if b'{STAT}' in data:
                        with self.lock:
                            self.active = True
                            self.GOPI.write(ALL_ZERO_STATE)
                            self.CIPO.write(b'{STAT}')
                            self.last_state = ALL_ZERO_STATE
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
        
        while True:
            try:
                if self.CIPO.in_waiting > 0:
                    data = self.CIPO.read(self.CIPO.in_waiting)
                    
                   
                    if data.startswith(b'\x28') and data.endswith(b'\x29'):
                        if len(data) == 9:  
                            release_time = time.time() + (self.delay_ms / 1000)
                            with self.lock:
                                self.delayed_buffer.append((data, release_time))
                        elif len(data) > 9:  
                            packets = data.split(b'\x29')
                            for packet in packets:
                                if len(packet) >= 8:
                                    full_packet = packet + b'\x29'
                                    if len(full_packet) == 9:
                                        release_time = time.time() + (self.delay_ms / 1000)
                                        with self.lock:
                                            self.delayed_buffer.append((full_packet, release_time))
                    
                    
                    elif data in (b'{STAT}', b'{HALT}'):
                        with self.lock:
                            self.GOPI.write(data)
                
               
                current_time = time.time()
                while True:
                    with self.lock:
                        if not self.delayed_buffer or current_time < self.delayed_buffer[0][1]:
                            break
                        
                        delayed_data, _ = self.delayed_buffer.popleft()
                        if self.active:
                            try:
                                transformed = self.transform_touch_data(delayed_data)
                                self.GOPI.write(transformed)
                                self.last_state = transformed
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                print(f"[{timestamp}] Delayed({self.delay_ms}ms) Data Sent: {transformed}")
                            except Exception as e:
                                print(f"Error transforming data: {e}")
                
            
                if not self.delayed_buffer and self.active:
                    with self.lock:
                        self.GOPI.write(self.last_state)
                
                
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error in CIPO handler: {e}")
                time.sleep(1)

    def run(self):
        try:
            self.GOPI = serial.Serial(GOPI, BAUD_RATE, timeout=0.1)
            self.CIPO = serial.Serial(CIPO, BAUD_RATE, timeout=0.1)
            
            print(f"Touch bridge started at {datetime.now()}")
            print(f"GOPI: {self.GOPI.name}, CIPO: {self.CIPO.name}")
            print(f"Input delay set to {self.delay_ms}ms")
            print("All received GOPI commands will be logged to GOPI_commands.log")
            print("Monitoring for commands:")
            print("- {STAT}: Activate bridge and send zero state")
            print("- {HALT}: Deactivate bridge")
            print("- {XXkY}: Register mapping (XX -> Y), respond with (XX  )")
            print("- {XXth}: Query mapping for XX, respond with (XX Y) if found")
            
            with open(self.command_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n===== Session started at {datetime.now()} =====\n")
                f.write(f"Input delay: {self.delay_ms}ms\n")
            
            
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