import sys
import socket
import serial
import threading
import time
from PyQt6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout, QComboBox, QPushButton,
    QLabel, QCheckBox, QLineEdit, QMessageBox
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QImage
from PyQt6.QtCore import QTimer, Qt, QRectF, QPointF
from PyQt6.QtSvg import QSvgRenderer
from datetime import datetime

class TouchSocketClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"Touch socket client initialized, sending to {host}:{port}")

    def send_touch_data(self, touched_points):
        data = bytes(touched_points)
        self.socket.sendto(data, (self.host, self.port))

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Client closed")

class SerialBridge:
    def __init__(self, port='COM13', baud_rate=9600, touch_widget=None):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.active = False
        self.touch_widget = touch_widget
        self.key_mappings = {}
        self.lock = threading.Lock()
        self.receive_thread = None
        self.running = False

    def start(self):
        try:
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            print(f"Serial communication started on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to start serial communication: {e}")
            return False

    def stop(self):
        self.running = False
        self.active = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.serial = None
        print("Serial communication stopped")

    def _receive_loop(self):
        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    data = self.serial.read_until(b'}')
                    if data:
                        self._process_command(data)
            except Exception as e:
                print(f"Error in serial receive loop: {e}")
                time.sleep(0.1)

    def _process_command(self, data):
        print(f"Received serial command: {data}")

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
                    if self.serial and self.serial.is_open:
                        self.serial.write(response)
                print(f"Registered mapping: {prefix} -> {suffix}")
                print(f"Responded to mapping command: {data} -> {response}")
                return
        
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
                        if self.serial and self.serial.is_open:
                            self.serial.write(response)
                    print(f"Responded to query: {data} -> {response}")
                else:
                    print(f"No mapping found for prefix: {prefix}")
                return
        
        # 处理标准命令
        if b'{STAT}' in data:
            with self.lock:
                self.active = True
                print("Received STAT command, activating serial bridge")
        elif b'{HALT}' in data:
            with self.lock:
                self.active = False
                print("Received HALT command, deactivating serial bridge")

    def send_touch_data(self, touched_points):
        if not self.active or not self.serial or not self.serial.is_open:
            return
        
        # 将触摸点转换为mai2格式
        mai2_data = self._transform_touch_data(touched_points)
        with self.lock:
            try:
                self.serial.write(mai2_data)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] Serial Data Sent: {mai2_data.hex()}")
            except Exception as e:
                print(f"Error sending serial data: {e}")

    def _transform_touch_data(self, touched_points):
        """
        将触摸点列表转换为mai格式的字节序列
        格式: 14字节，以b'\x28'开头，b'\x29'结尾
        """
        # 初始化mai输出数据 (全初始化为0x40 '@')
        mai_data = [0x40] * 14
        mai_data[0] = 0x28  # 起始字节 '('
        mai_data[13] = 0x29  # 结束字节 ')'
        
        # 触摸点到位映射
        point_to_bit = {
            # A区映射
            1: (1, 0), 2: (1, 2), 3: (2, 0), 4: (2, 2),
            5: (3, 0), 6: (3, 2), 7: (4, 0), 8: (4, 2),
            # B区映射
            11: (1, 1), 12: (1, 3), 13: (2, 1), 14: (2, 3),
            15: (3, 1), 16: (3, 3), 17: (4, 1), 18: (4, 3),
            # C区映射
            21: (4, 4)
        }
        
        # 设置触摸位
        for point in touched_points:
            if point in point_to_bit:
                byte_pos, bit_pos = point_to_bit[point]
                mai_data[byte_pos] |= (1 << bit_pos)
        
        return bytes(mai_data)

class TouchWidget(QWidget):
    MAX_TOUCH_POINTS = 10

    def __init__(self, parent=None, points_data=None, svg_prefix="", size_factor=2.0, socket_client=None, socket_enabled_func=None, serial_bridge=None):
        super().__init__(parent)
        self.size_factor = size_factor
        self.touch_points = points_data or {
            1: (407, 74, 'A1', -20, 10),
            2: (525, 191, 'A2', -10, 20),
            3: (525, 409, 'A3', -10, -15),
            4: (407, 526, 'A4', -20, -5),
            5: (193, 526, 'A5', 15, -5),
            6: (75, 409, 'A6', 5, -15),
            7: (75, 191, 'A7', 5, 20),
            8: (193, 74, 'A8', 15, 10),
            11: (350, 188, 'B1', -5, 0),
            12: (412, 249, 'B2', 0, 5),
            13: (412, 351, 'B3', 0, 0),
            14: (350, 412, 'B4', -5, 5),
            15: (250, 412, 'B5', 0, 5),
            16: (188, 351, 'B6', -5, 0),
            17: (188, 251, 'B7', -5, 5),
            18: (250, 188, 'B8', 0, 0),
            21: (300, 300, 'C', 2, 5)
        }
        # 应用尺寸因子并取整
        self.touch_points = {k: (
            round(v[0]*size_factor), 
            round(v[1]*size_factor), 
            v[2], 
            round(v[3]*size_factor), 
            round(v[4]*size_factor)
        ) for k, v in self.touch_points.items()}
        
        self.svg_prefix = svg_prefix
        self.default_svgs = {point: QSvgRenderer(f"{self.svg_prefix}touch/mai_{label}.svg") for point, (x, y, label, prefix_x, prefix_y) in self.touch_points.items()}
        self.touch_svgs = {point: QSvgRenderer(f"{self.svg_prefix}touch/mai_{label}_touch.svg") for point, (x, y, label, prefix_x, prefix_y) in self.touch_points.items()}
        self.current_svgs = self.default_svgs.copy()
        self.active_touches = set()
        self.touch_point_map = {}
        self.mouse_pressed = False
        self.mouse_touch_id = -1
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.svg_bounds = {}
        self.svg_images = {}
        self.calculate_svg_bounds_and_images()
        self.socket_client = socket_client
        self.socket_enabled_func = socket_enabled_func
        self.serial_bridge = serial_bridge
        self.last_sent_touches = None

    def set_socket_client(self, client):
        self.socket_client = client
        self.last_sent_touches = None

    def set_serial_bridge(self, bridge):
        self.serial_bridge = bridge
        self.last_sent_touches = None

    def calculate_svg_bounds_and_images(self):
        for point, (center_x, center_y, label, prefix_x, prefix_y) in self.touch_points.items():
            renderer = self.default_svgs[point]
            rect = renderer.viewBoxF()
            scale_factor = 0.85 * self.size_factor
            scaled_width = round(rect.width() * scale_factor)
            scaled_height = round(rect.height() * scale_factor)
            top_left_x = round(center_x - scaled_width / 2)
            top_left_y = round(center_y - scaled_height / 2)
            self.svg_bounds[point] = QRectF(top_left_x, top_left_y, scaled_width, scaled_height)
            image = QImage(scaled_width, scaled_height, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter, QRectF(0, 0, scaled_width, scaled_height))
            painter.end()
            self.svg_images[point] = image

    def is_point_in_svg(self, point_id, pos):
        if point_id not in self.svg_bounds:
            return False
        bounds = self.svg_bounds[point_id]
        if bounds.contains(pos):
            local_x = int(pos.x() - bounds.x())
            local_y = int(pos.y() - bounds.y())
            if (0 <= local_x < self.svg_images[point_id].width() and 
                0 <= local_y < self.svg_images[point_id].height()):
                pixel_color = self.svg_images[point_id].pixelColor(local_x, local_y)
                return pixel_color.alpha() > 10
        return False

    def find_touched_points(self, pos):
        touched = []
        for point_id in self.touch_points.keys():
            if self.is_point_in_svg(point_id, pos):
                touched.append(point_id)
        return touched

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        palette = self.palette()
        painter.fillRect(self.rect(), palette.window())
        
        # 字体大小取整
        font_size = max(8, round(12 * self.size_factor))
        font = QFont("SEGA-Humming v2 B", font_size)
        painter.setFont(font)
        
        for point, (center_x, center_y, label, prefix_x, prefix_y) in self.touch_points.items():
            # 缩放因子取整处理
            scale_factor = round(0.85 * self.size_factor * 100) / 100  # 保留两位小数
            
            renderer = self.current_svgs[point]
            rect = renderer.viewBoxF()
            # 尺寸取整
            scaled_width = round(rect.width() * scale_factor)
            scaled_height = round(rect.height() * scale_factor)
            
            # 位置取整
            top_left_x = round(center_x - scaled_width / 2)
            top_left_y = round(center_y - scaled_height / 2)
            
            painter.save()
            painter.translate(top_left_x, top_left_y)
            renderer.render(painter, QRectF(0, 0, scaled_width, scaled_height))
            painter.restore()
        
        painter.setPen(QColor(255,255,255))
        
        for point, (center_x, center_y, label, prefix_x, prefix_y) in self.touch_points.items():
            # 文本位置取整
            text_x = round(center_x - 10 * self.size_factor + prefix_x)
            text_y = round(center_y + prefix_y)
            painter.drawText(text_x, text_y, label)

    def mousePressEvent(self, event):
        self.mouse_pressed = True
        pos = event.position()
        self.mouse_touch_id = -1
        touched_points = self.find_touched_points(pos)
        self.touch_point_map[self.mouse_touch_id] = set(touched_points)
        self.update_active_touches()
        self.update_touch_display()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.mouse_pressed and (event.buttons() & Qt.MouseButton.LeftButton):
            current_pos = event.position()
            if self.mouse_touch_id in self.touch_point_map:
                self.touch_point_map[self.mouse_touch_id].clear()
                touched_points = self.find_touched_points(current_pos)
                self.touch_point_map[self.mouse_touch_id].update(touched_points)
                self.update_active_touches()
                self.update_touch_display()
        event.accept()

    def mouseReleaseEvent(self, event):
        self.mouse_pressed = False
        if self.mouse_touch_id in self.touch_point_map:
            del self.touch_point_map[self.mouse_touch_id]
        self.update_active_touches()
        self.update_touch_display()
        event.accept()

    def leaveEvent(self, event):
        if self.mouse_pressed:
            if self.mouse_touch_id in self.touch_point_map:
                del self.touch_point_map[self.mouse_touch_id]
            self.update_active_touches()
            self.update_touch_display()
        event.accept()

    def event(self, event):
        if event.type() in (event.Type.TouchBegin, event.Type.TouchUpdate, event.Type.TouchEnd, event.Type.TouchCancel):
            self.touchEvent(event)
            return True
        return super().event(event)

    def touchEvent(self, event):
        event_type = event.type()
        if event_type == event.Type.TouchBegin:
            self.handle_touch_begin(event)
        elif event_type == event.Type.TouchUpdate:
            self.handle_touch_update(event)
        elif event_type == event.Type.TouchEnd:
            self.handle_touch_end(event)
        elif event_type == event.Type.TouchCancel:
            self.handle_touch_cancel(event)
        event.accept()

    def handle_touch_begin(self, event):
        points = event.points()[:self.MAX_TOUCH_POINTS]
        keys_to_remove = [k for k in self.touch_point_map.keys() if k != self.mouse_touch_id]
        for k in keys_to_remove:
            del self.touch_point_map[k]
        for point in points:
            touch_id = point.id()
            pos = point.position()
            touched_points = self.find_touched_points(pos)
            self.touch_point_map[touch_id] = set(touched_points)
        self.update_active_touches()
        self.update_touch_display()
    
    def handle_touch_update(self, event):
        points = event.points()[:self.MAX_TOUCH_POINTS]
        keys_to_remove = [k for k in self.touch_point_map.keys() if k != self.mouse_touch_id]
        for k in keys_to_remove:
            del self.touch_point_map[k]
        for point in points:
            touch_id = point.id()
            pos = point.position()
            touched_points = self.find_touched_points(pos)
            self.touch_point_map[touch_id] = set(touched_points)
        self.update_active_touches()
        self.update_touch_display()

    def handle_touch_end(self, event):
        for point in event.points():
            touch_id = point.id()
            if touch_id in self.touch_point_map:
                del self.touch_point_map[touch_id]
        self.update_active_touches()
        self.update_touch_display()

    def handle_touch_cancel(self, event):
        self.touch_point_map.clear()
        self.update_active_touches()
        self.update_touch_display()

    def update_active_touches(self):
        self.active_touches.clear()
        keys = [k for k in self.touch_point_map.keys() if k != self.mouse_touch_id][:self.MAX_TOUCH_POINTS]
        for key in keys:
            self.active_touches.update(self.touch_point_map[key])
        if self.mouse_touch_id in self.touch_point_map:
            self.active_touches.update(self.touch_point_map[self.mouse_touch_id])

    def update_touch_display(self):
        for point_id in self.touch_points.keys():
            if point_id in self.active_touches:
                self.current_svgs[point_id] = self.touch_svgs[point_id]
            else:
                self.current_svgs[point_id] = self.default_svgs[point_id]
        self.update()

    def send_socket_touch_data(self):
        if self.socket_client is not None and self.socket_enabled_func is not None and self.socket_enabled_func():
            current_touches = sorted(self.active_touches)
            if current_touches != self.last_sent_touches:
                self.socket_client.send_touch_data(current_touches)
                self.last_sent_touches = current_touches

    def send_serial_touch_data(self):
        if self.serial_bridge is not None:
            current_touches = sorted(self.active_touches)
            if current_touches != self.last_sent_touches:
                self.serial_bridge.send_touch_data(current_touches)
                self.serial_bridge.send_touch_data(current_touches)
                self.last_sent_touches = current_touches

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mai2touch PAD")
        self.base_window_width = 600
        self.base_window_height = 700
        self.base_canvas_size = 600
        self.size_options = {
            "600x700 (默认)": {"window": (self.base_window_width, self.base_window_height), "canvas": self.base_canvas_size, "factor": 1.0},
            "1080x1180": {"window": (1080, 1180), "canvas": 1080, "factor": 1080/self.base_canvas_size},
            "300x400": {"window": (300, 400), "canvas": 300, "factor": 300/self.base_canvas_size},
            "540x600": {"window": (540, 600), "canvas": 540, "factor": 540/self.base_canvas_size}
        }
        self.current_size = "600x700 (默认)"
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.control_layout.setContentsMargins(10, 0, 0, 0)
        self.setWindowOpacity(0.25)
        # 第一行：启用socket通信，端口输入框，应用按钮
        self.socket_checkbox = QCheckBox("启用Socket通信")
        self.socket_checkbox.setChecked(True)
        self.socket_port_edit = QLineEdit()
        self.socket_port_edit.setText("8888")
        self.socket_port_edit.setFixedWidth(60)
        self.socket_port_edit.setMaximumWidth(80)
        self.socket_port_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.socket_port_edit.setToolTip("输入Socket端口")
        self.socket_port_label = QLabel("端口:")
        self.socket_port_apply_btn = QPushButton("应用")
        self.socket_port_apply_btn.setFixedWidth(50)
        self.socket_port_apply_btn.clicked.connect(self.apply_socket_port)
        socket_line = QHBoxLayout()
        socket_line.addWidget(self.socket_checkbox)
        socket_line.addSpacing(10)
        socket_line.addWidget(self.socket_port_label)
        socket_line.addWidget(self.socket_port_edit)
        socket_line.addWidget(self.socket_port_apply_btn)
        socket_line.addStretch()

        # socket复选框取消勾选时立刻关闭socket
        self.socket_checkbox.stateChanged.connect(self.on_socket_checkbox_state_changed)

        # 第二行：启用Serial通信，COM口输入框，应用按钮
        self.serial_checkbox = QCheckBox("启用Serial通信  ")
        self.serial_checkbox.setChecked(False)
        self.serial_port_edit = QLineEdit()
        self.serial_port_edit.setText("COM13")
        self.serial_port_edit.setFixedWidth(60)
        self.serial_port_edit.setMaximumWidth(80)
        self.serial_port_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.serial_port_edit.setToolTip("输入Serial端口")
        self.serial_port_label = QLabel("端口:")
        self.serial_port_apply_btn = QPushButton("应用")
        self.serial_port_apply_btn.setFixedWidth(50)
        self.serial_port_apply_btn.clicked.connect(self.apply_serial_port)
        serial_line = QHBoxLayout()
        serial_line.addWidget(self.serial_checkbox)
        serial_line.addSpacing(10)
        serial_line.addWidget(self.serial_port_label)
        serial_line.addWidget(self.serial_port_edit)
        serial_line.addWidget(self.serial_port_apply_btn)
        serial_line.addStretch()

        # serial复选框状态变化处理
        self.serial_checkbox.stateChanged.connect(self.on_serial_checkbox_state_changed)

        # 第三行：窗口尺寸
        self.size_label = QLabel("窗口大小：")
        self.size_combo = QComboBox()
        self.size_combo.addItems(self.size_options.keys())
        self.size_combo.setCurrentText(self.current_size)
        self.apply_button = QPushButton("应用")
        self.apply_button.setFixedWidth(50)
        self.apply_button.clicked.connect(self.apply_size)
        size_line = QHBoxLayout()
        size_line.addWidget(self.size_label)
        size_line.addWidget(self.size_combo)
        size_line.addWidget(self.apply_button)
        size_line.addStretch()

        # 第四行：触摸状态
        self.status_label = QLabel("触摸状态: 无")
        status_line = QHBoxLayout()
        status_line.addWidget(self.status_label)
        status_line.addStretch()

        # 添加到控制面板
        self.control_layout.addLayout(socket_line)
        self.control_layout.addLayout(serial_line)
        self.control_layout.addLayout(size_line)
        self.control_layout.addLayout(status_line)
        self.control_panel.setFixedHeight(100)

        self.socket_port = 8888
        self.socket_client = TouchSocketClient(host='localhost', port=self.socket_port)
        
        self.serial_port = "COM13"
        self.serial_bridge = None
        
        self.init_canvas()
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addWidget(self.control_panel)
        self.apply_size()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(50)

    def is_socket_enabled(self):
        return self.socket_checkbox.isChecked()

    def is_serial_enabled(self):
        return self.serial_checkbox.isChecked()

    def init_canvas(self):
        if hasattr(self, 'touch_widget'):
            self.content_layout.removeWidget(self.touch_widget)
            self.touch_widget.deleteLater()
        factor = self.size_options[self.current_size]["factor"]
        canvas_size = self.size_options[self.current_size]["canvas"]
        self.touch_widget = TouchWidget(
            self, size_factor=factor,
            socket_client=self.socket_client,
            socket_enabled_func=self.is_socket_enabled,
            serial_bridge=self.serial_bridge
        )
        self.touch_widget.setFixedSize(canvas_size, canvas_size)
        self.content_layout.addWidget(self.touch_widget)

    def apply_size(self):
        self.current_size = self.size_combo.currentText()
        size_info = self.size_options[self.current_size]
        self.resize(size_info["window"][0], size_info["window"][1])
        self.init_canvas()
        self.setMinimumSize(size_info["window"][0], size_info["window"][1])

    def get_touch_data(self):
        if hasattr(self, 'touch_widget'):
            return list(self.touch_widget.active_touches)
        return []

    def update_data(self):
        touched_points = self.get_touch_data()
        if touched_points:
            self.status_label.setText(f"触摸状态: {sorted(touched_points)}")
        else:
            self.status_label.setText("触摸状态: 无")
        if hasattr(self, 'touch_widget'):
            self.touch_widget.send_socket_touch_data()
            self.touch_widget.send_serial_touch_data()

    def apply_socket_port(self):
        port_text = self.socket_port_edit.text().strip()
        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "端口错误", "请输入有效的端口号 (1~65535)")
            self.socket_port_edit.setText(str(self.socket_port))
            return
        # 关闭旧socket
        if hasattr(self, 'socket_client') and self.socket_client is not None:
            self.socket_client.close()
        self.socket_port = port
        self.socket_client = TouchSocketClient(host='localhost', port=port)
        if hasattr(self, 'touch_widget'):
            self.touch_widget.set_socket_client(self.socket_client)

    def apply_serial_port(self):
        port_text = self.serial_port_edit.text().strip()
        if not port_text:
            QMessageBox.warning(self, "端口错误", "请输入有效的COM端口")
            self.serial_port_edit.setText(self.serial_port)
            return
        
        # 如果串口正在运行，先停止
        if self.serial_bridge and self.serial_bridge.running:
            self.serial_bridge.stop()
            self.serial_bridge = None
        
        self.serial_port = port_text
        if self.serial_checkbox.isChecked():
            # 如果复选框已勾选，重新启动串口
            self.serial_bridge = SerialBridge(port=self.serial_port, touch_widget=self.touch_widget)
            if not self.serial_bridge.start():
                self.serial_checkbox.setChecked(False)
                QMessageBox.warning(self, "串口错误", f"无法打开串口 {self.serial_port}")
        
        if hasattr(self, 'touch_widget'):
            self.touch_widget.set_serial_bridge(self.serial_bridge)

    def on_socket_checkbox_state_changed(self, state):
        # 取消勾选时立刻关闭socket
        if not self.socket_checkbox.isChecked():
            if hasattr(self, 'socket_client') and self.socket_client is not None:
                self.socket_client.close()
                self.socket_client = None
            if hasattr(self, 'touch_widget'):
                self.touch_widget.set_socket_client(None)
        else:
            # 勾选时重启socket（使用当前端口）
            if self.socket_client is None:
                try:
                    port = int(self.socket_port_edit.text().strip())
                    if not (1 <= port <= 65535):
                        raise ValueError
                except ValueError:
                    port = 8888
                    self.socket_port_edit.setText("8888")
                self.socket_client = TouchSocketClient(host='localhost', port=port)
                if hasattr(self, 'touch_widget'):
                    self.touch_widget.set_socket_client(self.socket_client)

    def on_serial_checkbox_state_changed(self, state):
        if self.serial_checkbox.isChecked():
            # 启用串口通信
            self.serial_bridge = SerialBridge(port=self.serial_port, touch_widget=self.touch_widget)
            if not self.serial_bridge.start():
                self.serial_checkbox.setChecked(False)
                QMessageBox.warning(self, "串口错误", f"无法打开串口 {self.serial_port}")
            else:
                if hasattr(self, 'touch_widget'):
                    self.touch_widget.set_serial_bridge(self.serial_bridge)
        else:
            # 禁用串口通信
            if self.serial_bridge and self.serial_bridge.running:
                self.serial_bridge.stop()
                self.serial_bridge = None
            if hasattr(self, 'touch_widget'):
                self.touch_widget.set_serial_bridge(None)

    def closeEvent(self, event):
        if hasattr(self, 'socket_client') and self.socket_client is not None:
            self.socket_client.close()
        if hasattr(self, 'serial_bridge') and self.serial_bridge is not None and self.serial_bridge.running:
            self.serial_bridge.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
