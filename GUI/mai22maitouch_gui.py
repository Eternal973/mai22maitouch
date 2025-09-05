import sys
import time
import socket
import threading
from collections import deque
from PyQt6.QtWidgets import (QWidget, QApplication, QHBoxLayout, QVBoxLayout, 
                             QComboBox, QPushButton, QLabel, QSizePolicy)
from PyQt6.QtGui import QPainter, QColor, QFont, QPalette, QKeyEvent
from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtSvg import QSvgRenderer

class TouchSocketServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.touch_data_queue = deque()
        self.running = True
        self.current_touched_points = []  # 保存当前触摸状态
        
    def start_server(self):
        """启动socket服务器线程"""
        self.thread = threading.Thread(target=self._receive_data)
        self.thread.daemon = True
        self.thread.start()
        
    def _receive_data(self):
        """接收数据线程"""
        print(f"Touch socket server listening on {self.host}:{self.port}")
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                self._process_data(data)
            except Exception as e:
                if self.running:  # 只在运行状态下打印错误
                    print(f"Socket error: {e}")
                
    def _process_data(self, data):
        """处理接收到的二进制数据"""
        touched_points = list(data)  # 直接将字节转换为整数列表
        
        # 更新当前状态
        self.current_touched_points = touched_points
        
        # 将数据放入队列（如果需要历史数据可以保留，否则直接使用current_touched_points）
        self.touch_data_queue.append(touched_points)
        
    def get_latest_data(self):
        """获取最新的触摸数据"""
        # 直接返回当前状态，不需要队列处理
        return self.current_touched_points
        
    def stop_server(self):
        """停止服务器"""
        self.running = False
        self.socket.close()
        
class TouchWidget(QWidget):
    def __init__(self, parent=None, points_data=None, svg_prefix="", size_factor=1.0):
        super().__init__(parent)
        self.size_factor = size_factor
        self.touch_points = points_data or {
            1: (404, 73, 'A1'),
            2: (528, 193, 'A2'),
            3: (528, 404, 'A3'),
            4: (403, 526, 'A4'),
            5: (197, 528, 'A5'),
            6: (72, 404, 'A6'),
            7: (72, 193, 'A7'),
            8: (197, 73, 'A8'),
            11: (347, 184, 'B1'),
            12: (418, 254, 'B2'),
            13: (418, 346, 'B3'),
            14: (347, 417, 'B4'),
            15: (254, 417, 'B5'),
            16: (186, 346, 'B6'),
            17: (186, 254, 'B7'),
            18: (254, 184, 'B8'),
            21: (330, 300, 'C1'),
            22: (271, 300, 'C2'),
            31: (300, 50, 'D1'),
            32: (481, 119, 'D2'),
            33: (550, 300, 'D3'),
            34: (477, 477, 'D4'),
            35: (300, 550, 'D5'),
            36: (118, 482, 'D6'),
            37: (50, 300, 'D7'),
            38: (123, 123, 'D8'),
            41: (300, 130, 'E1'),
            42: (421, 178, 'E2'),
            43: (471, 300, 'E3'),
            44: (421, 421, 'E4'),
            45: (300, 471, 'E5'),
            46: (178, 421, 'E6'),
            47: (129, 300, 'E7'),
            48: (179, 179, 'E8')
        }
        
        # 应用尺寸因子并取整
        self.touch_points = {k: (round(v[0]*size_factor), round(v[1]*size_factor), v[2]) 
                           for k, v in self.touch_points.items()}
        
        self.svg_prefix = svg_prefix
        self.default_svgs = {point: QSvgRenderer(f"{self.svg_prefix}touch/{label}.svg") for point, (x, y, label) in self.touch_points.items()}
        self.touch_svgs = {point: QSvgRenderer(f"{self.svg_prefix}touch/{label}_touch.svg") for point, (x, y, label) in self.touch_points.items()}
        self.current_svgs = self.default_svgs.copy()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        palette = self.palette()
        painter.fillRect(self.rect(), palette.window())
        
        # 字体大小取整
        font_size = max(8, round(12 * self.size_factor))
        font = QFont("SEGA-Humming v2 B", font_size)
        painter.setFont(font)
        
        for point, (center_x, center_y, label) in self.touch_points.items():
            # 缩放因子取整处理
            scale_factor = round(0.3 * self.size_factor * 100) / 100  # 保留两位小数
            
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
        
        for point, (center_x, center_y, label) in self.touch_points.items():
            # 文本位置取整
            text_x = round(center_x - 10 * self.size_factor)
            text_y = round(center_y + 5 * self.size_factor)
            painter.drawText(text_x, text_y, label)

class TouchWidget_mai(QWidget):
    def __init__(self, parent=None, points_data=None, svg_prefix="", size_factor=1.0):
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mai22maitouch GUI")
        
        # 基础尺寸（默认尺寸）
        self.base_window_width = 1280
        self.base_window_height = 680
        self.base_canvas_size = 600
        
        # 尺寸选项 - 现在基于基础尺寸进行缩放
        self.size_options = {
            "1280x680 (默认)": {"window": (self.base_window_width, self.base_window_height), "canvas": self.base_canvas_size, "factor": 1.0},
            "1080x580": {"window": (1080, 580), "canvas": 500, "factor": 500/self.base_canvas_size},
            "720x400": {"window": (720, 400), "canvas": 340, "factor": 340/self.base_canvas_size}
        }
        
        self.current_size = "1280x680 (默认)"
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建控制面板
        self.control_panel = QWidget()
        self.control_layout = QHBoxLayout(self.control_panel)
        self.control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 添加控制元素
        self.size_label = QLabel("窗口大小：")
        self.size_combo = QComboBox()
        self.size_combo.addItems(self.size_options.keys())
        self.size_combo.setCurrentText(self.current_size)
        
        self.apply_button = QPushButton("应用")
        self.apply_button.clicked.connect(self.apply_size)
        
        self.control_layout.addWidget(self.size_label)
        self.control_layout.addWidget(self.size_combo)
        self.control_layout.addWidget(self.apply_button)
        self.control_layout.addStretch()
        
        # 控制面板固定高度
        self.control_panel.setFixedHeight(40)
        
        # 初始化画布
        self.init_canvases()
        
        # 组装界面
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addWidget(self.control_panel)
        
        # 设置初始尺寸
        self.apply_size()
        
        # 初始化socket服务器
        self.socket_server = TouchSocketServer()
        self.socket_server.start_server()
        
        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(50)

    def init_canvases(self):
        """初始化画布"""
        # 清除现有画布
        if hasattr(self, 'left_widget'):
            self.content_layout.removeWidget(self.left_widget)
            self.left_widget.deleteLater()
        if hasattr(self, 'right_widget'):
            self.content_layout.removeWidget(self.right_widget)
            self.right_widget.deleteLater()
        
        # 获取当前尺寸因子
        factor = self.size_options[self.current_size]["factor"]
        canvas_size = self.size_options[self.current_size]["canvas"]
        
        # 创建新画布
        self.left_widget = TouchWidget(self, size_factor=factor)
        self.left_widget.setFixedSize(canvas_size, canvas_size)
        self.content_layout.addWidget(self.left_widget)
        
        self.right_widget = TouchWidget_mai(self, size_factor=factor)
        self.right_widget.setFixedSize(canvas_size, canvas_size)
        self.content_layout.addWidget(self.right_widget)

    def apply_size(self):
        """应用选择的窗口尺寸"""
        self.current_size = self.size_combo.currentText()
        size_info = self.size_options[self.current_size]
        
        # 更新窗口尺寸
        self.resize(size_info["window"][0], size_info["window"][1])
        
        # 重新初始化画布
        self.init_canvases()
        
        # 调整窗口最小尺寸，防止窗口过小
        self.setMinimumSize(size_info["window"][0] // 2, size_info["window"][1] // 2)

    def update_data(self):
        # 从socket获取当前触摸状态
        touched_points = self.socket_server.get_latest_data()
        
        # 左侧输出
        for point in self.left_widget.touch_points.keys():
            if point in touched_points:
                self.left_widget.current_svgs[point] = self.left_widget.touch_svgs[point]
            else:
                self.left_widget.current_svgs[point] = self.left_widget.default_svgs[point]
        
        # 右侧输出
        for point in self.right_widget.touch_points.keys():
            if point in touched_points:
                self.right_widget.current_svgs[point] = self.right_widget.touch_svgs[point]
            elif 22 in touched_points:
                self.right_widget.current_svgs[21] = self.right_widget.touch_svgs[21]
            else:
                self.right_widget.current_svgs[point] = self.right_widget.default_svgs[point]
        
        # 更新显示
        self.left_widget.update()
        self.right_widget.update()
        
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.socket_server.stop_server()
        event.accept()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    try:
        sys.exit(app.exec())
    finally:
        window.socket_server.stop_server()
