import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QFont
import os
from datetime import datetime
import json
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import random

class BirdEyeTransformer:
    def __init__(self, camera_matrix, dist_coeffs, fov_x, fov_y, camera_height, tilt_angle):
        self.K = camera_matrix
        self.dist = dist_coeffs
        self.fov_x = fov_x
        self.fov_y = fov_y
        self.h = camera_height
        self.theta_deg = tilt_angle
        self.pixels_per_meter = 400#正射变换完可设视频区域变化
        

    def calculate_ground_dimensions(self):
        theta = math.radians(abs(self.theta_deg))
        fov_x = math.radians(self.fov_x)
        fov_y = math.radians(self.fov_y)
        W_ground = 2 * self.h * math.tan(fov_x / 2) / math.cos(theta)
        H_ground = 2 * self.h * math.tan(fov_y / 2) / math.cos(theta)
        return W_ground, H_ground

    def adjust_homography(self, H, img_shape, target_size):
        h, w = img_shape[:2]
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype=np.float32)
        warped_corners = cv2.perspectiveTransform(corners.reshape(1, -1, 2), H).reshape(-1, 2)
        x_min, y_min = warped_corners.min(axis=0)
        x_max, y_max = warped_corners.max(axis=0)
        scale_x = target_size[0] / (x_max - x_min)
        scale_y = target_size[1] / (y_max - y_min)
        scale = min(scale_x, scale_y)
        adjust_M = np.array([
            [scale, 0, -x_min * scale],
            [0, scale, -y_min * scale],
            [0, 0, 1]
        ])
        return adjust_M @ H, target_size
    def get_rotation_matrix(self):
        pitch = math.radians(self.theta_deg)
        yaw = 0  # 可根据需要设为用户输入值
        roll = 0  # 可添加侧倾参数

        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(pitch), -math.sin(pitch)],
            [0, math.sin(pitch), math.cos(pitch)]
        ], dtype=np.float32)

        Ry = np.array([
            [math.cos(yaw), 0, math.sin(yaw)],
            [0, 1, 0],
            [-math.sin(yaw), 0, math.cos(yaw)]
        ], dtype=np.float32)

        Rz = np.array([
            [math.cos(roll), -math.sin(roll), 0],
            [math.sin(roll), math.cos(roll), 0],
            [0, 0, 1]
        ], dtype=np.float32)

        return Rz @ Ry @ Rx

    def get_bird_eye_view(self, img, target_size=None):
        if img is None or img.size == 0:
            return None, None
        try:
            img_undistorted = cv2.undistort(img, self.K, self.dist)
            W_ground, H_ground = self.calculate_ground_dimensions()
            if target_size is None:
                target_width = int(round(W_ground * self.pixels_per_meter))
                target_height = int(round(H_ground * self.pixels_per_meter))
            else:
                target_width, target_height = target_size

            # theta_rad = math.radians(self.theta_deg)
            # R_x = np.array([
            #     [1, 0, 0],
            #     [0, math.cos(theta_rad), -math.sin(theta_rad)],
            #     [0, math.sin(theta_rad), math.cos(theta_rad)]
            # ], dtype=np.float32)
            # tvec = np.array([[0], [0], [self.h]], dtype=np.float32)
            # H = self.K @ np.hstack((R_x[:, :2], tvec))
            # H_inv = np.linalg.inv(H)
            R = self.get_rotation_matrix()
            tvec = np.array([[0], [0], [self.h]], dtype=np.float32)
            H = self.K @ np.hstack((R[:, :2], tvec))
            H_inv = np.linalg.inv(H) 
            scale_M = np.diag([self.pixels_per_meter, self.pixels_per_meter, 1])
            H_scaled = scale_M @ H_inv
            H_final, output_size = self.adjust_homography(H_scaled, img_undistorted.shape, (target_width, target_height))
            bird_eye_img = cv2.warpPerspective(img_undistorted, H_final, output_size, flags=cv2.INTER_LINEAR)

            # Auto-crop black borders
            gray = cv2.cvtColor(bird_eye_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            coords = cv2.findNonZero(thresh)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                bird_eye_img = bird_eye_img[y:y+h, x:x+w]

            return bird_eye_img, bird_eye_img.shape[:2][::-1]
        except Exception as e:
            print(f"[BirdEyeTransformer] Transformation failed: {e}")
            return None, None
            
    def get_rotation_matrix(self):
        pitch = math.radians(self.theta_deg)
        yaw = 0.0   # 如需扩展可以变为 self.yaw_deg
        roll = 0.0  # 如需扩展可以变为 self.roll_deg

        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(pitch), -math.sin(pitch)],
            [0, math.sin(pitch), math.cos(pitch)]
        ], dtype=np.float32)

        Ry = np.array([
            [math.cos(yaw), 0, math.sin(yaw)],
            [0, 1, 0],
            [-math.sin(yaw), 0, math.cos(yaw)]
        ], dtype=np.float32)

        Rz = np.array([
            [math.cos(roll), -math.sin(roll), 0],
            [math.sin(roll), math.cos(roll), 0],
            [0, 0, 1]
        ], dtype=np.float32)

        return Rz @ Ry @ Rx

class VideoThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    # failed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.cap = None
        self.running = False
        self.source = None
        self.frame_rate = 30
        self.frame_width = 640  # 降低默认分辨率
        self.frame_height = 480
    

    
    def start_capture(self, source):
        self.source = source
        self.running = True
        self.start()  # 开始线程，真正打开摄像头放在 run() 内
        return True

    
    def run(self):
        try:
            print(f"[VideoThread] 正在初始化视频源: {self.source}")
            # 自动判断视频源类型
            if isinstance(self.source, str):
                self.cap = cv2.VideoCapture(self.source)  # 视频文件
            else:
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)  # 摄像头

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            if not self.cap.isOpened():
                print(f"[VideoThread] ❌ 无法打开视频源: {self.source}")
                self.running = False
                self.frame_ready.emit(np.zeros((480, 640, 3), dtype=np.uint8))
                return

            while self.running:
                ret, frame = self.cap.read()
                if not ret or frame is None or frame.size == 0:
                    print("[VideoThread] ⚠️ 帧读取失败或为空")
                    self.msleep(100)
                    continue
                self.frame_ready.emit(frame)
                self.msleep(int(1000 / self.frame_rate))

        finally:
            if self.cap:
                self.cap.release()

class CropWidget(QLabel):
    def __init__(self):
        super().__init__()
        # self.setMinimumSize(400, 300)
        self.setMinimumSize(800, 640)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)#保持弹性

        self.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.setScaledContents(True)#自动缩放画面
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignCenter)

        self.crop_rect = None
        self.dragging = False
        self.drag_start = None
        self.current_frame = None
        self.show_crop_rect = False
        self.show_row_lines = False

    # def set_frame(self, frame):
    #     self.current_frame = frame.copy()
    #     self.update_display()
    def set_frame(self, frame):
        if frame is None or frame.size == 0:
            self.current_frame = None
            self.clear()
            self.setPixmap(QPixmap())  #  强制清空 pixmap
            # self.setText("视频显示区域")
            # self.setAlignment(Qt.AlignCenter)
            # font = QFont()
            # font.setPointSize(14)
            # font.setBold(True)
            # self.setFont(font)
            self.setText("视频显示区域")
            self.setAlignment(Qt.AlignCenter)
            self.setFont(QFont())  # 恢复为默认字体（跟最初保持一致）
            return

        self.setText("")  #  清空文字
        self.current_frame = frame.copy()
        self.update_display()


    def set_crop_rect(self, rect):
        self.crop_rect = rect
        if self.show_crop_rect:
            self.update_display()
    def reset_display(self):
        """清空图像并居中显示提示文本"""
        self.clear()
        self.current_frame = None
        self.setText("视频显示区域")
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont())  # 恢复默认字体
        # font = QFont()
        # font.setPointSize(14)
        # font.setBold(True)
        # self.setFont(font)


    def set_show_crop_rect(self, show):
        self.show_crop_rect = show
        self.update_display()

    def set_show_row_lines(self, show):
        self.show_row_lines = show
        self.update_display()

    def update_display(self):
        # if self.current_frame is None:
        #     self.clear()
        #     return
        if self.current_frame is None:
            self.clear()
            self.setPixmap(QPixmap())  # 确保完全清除图像
            self.setText("视频显示区域")
            self.setAlignment(Qt.AlignCenter)
            self.setFont(QFont())  
            # font = QFont()
            # font.setPointSize(14)
            # font.setBold(True)
            # self.setFont(font)
            return    
        try:
            frame = self.current_frame.copy()
            
            # 确保是3通道BGR
            if frame.ndim == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # 确保是3通道BGR格式
            if frame.shape[2] != 3:
                frame = frame[:, :, :3]
                
            # 从BGR转换为RGB - 修正颜色问题
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 绘制裁剪框和行线
            if self.show_crop_rect and self.crop_rect:
                x, y, w, h = self.crop_rect
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                
            if self.show_row_lines:
                h, w = frame.shape[:2]
                for i in range(3):
                    y_pos = int(h * (0.3 + i * 0.2))
                    cv2.line(frame, (50, y_pos), (w-50, y_pos), (255,0,0), 2)

            # 转换为QImage
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            # 缩放保持宽高比
            # scaled_pixmap = pixmap.scaled(
            #     self.width(), self.height(), 
            #     Qt.KeepAspectRatio, 
            #     Qt.SmoothTransformation
            # )
            scaled_pixmap = pixmap.scaled(
            self.width(), self.height(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation  # 更快且避免过度平滑模糊
        )
            
            self.setPixmap(scaled_pixmap)
        
        except Exception as e:
            print(f"[CropWidget] Display error: {e}")
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.show_crop_rect:
            self.dragging = True
            self.drag_start = (event.x(), event.y())

    def mouseMoveEvent(self, event):
        if self.dragging and self.drag_start and self.show_crop_rect:
            start_x, start_y = self.drag_start
            end_x, end_y = event.x(), event.y()
            
            pixmap = self.pixmap()
            if pixmap is None:
                return
                
            img_w = self.current_frame.shape[1]
            img_h = self.current_frame.shape[0]
            disp_w = pixmap.width()
            disp_h = pixmap.height()
            
            scale_x = img_w / disp_w
            scale_y = img_h / disp_h

            x = min(start_x, end_x) * scale_x
            y = min(start_y, end_y) * scale_y
            w = abs(end_x - start_x) * scale_x
            h = abs(end_y - start_y) * scale_y

            self.crop_rect = (int(x), int(y), int(w), int(h))
            self.update_display()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

class BiasPlotWidget(FigureCanvas):
    def __init__(self):
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 设置支持中文
        matplotlib.rcParams['axes.unicode_minus'] = False
        self.figure = Figure(figsize=(6, 3))
        super().__init__(self.figure)
        self.setParent(None)
        self.ax = self.figure.add_subplot(111)
        # self.ax.set_title("偏移量曲线")
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel("偏移量")
        self.ax.grid(True)
        
        self.data_x = []
        self.data_y = []
        self.max_points = 100
        self.time_counter = 0
        
        # Initial empty plot
        self.line, = self.ax.plot([], [], 'b-')
        self.figure.tight_layout()

    def update_plot(self, bias_value):
        self.time_counter += 1
        self.data_x.append(self.time_counter)
        self.data_y.append(bias_value)
        
        # Keep only last max_points
        if len(self.data_x) > self.max_points:
            self.data_x = self.data_x[-self.max_points:]
            self.data_y = self.data_y[-self.max_points:]
        
        self.line.set_data(self.data_x, self.data_y)
        
        if self.data_x and self.data_y:
            self.ax.set_xlim(min(self.data_x), max(self.data_x))
            self.ax.set_ylim(min(self.data_y) - 1, max(self.data_y) + 1)
        
        self.draw()

    def clear_plot(self):
        self.data_x.clear()
        self.data_y.clear()
        self.time_counter = 0
        self.line.set_data([], [])
        self.ax.clear()
        # self.ax.set_title("偏移量曲线")
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel("偏移量")
        self.ax.grid(True)
        self.draw()

class OrthophotoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("中控系统监控大屏")
        self.setGeometry(50, 50, 1400, 800)

        # Video thread
        self.video_thread = VideoThread()
        self.video_thread.frame_ready.connect(self.update_frame)

        # Current frame and parameters
        self.current_frame = None
        self.original_frame = None
        self.camera_height = 130.0  # cm
        self.tilt_angle = -49  # degrees (positive up)
        self.recording = False
        self.video_writer = None
        self.video_output_path = ""

        # Camera intrinsics
        self.camera_matrix = np.array([[1125, 0, 439],
                                     [0, 1656, 293],
                                     [0, 0, 1]], dtype=np.float32)
        self.dist_coeffs = np.zeros((4, 1))
        self.fov_x = 65  # degrees
        self.fov_y = 46  # degrees

        self.video_source = 'camera'
        self.bird_eye_transformer = None
        
        # State variables
        self.ortho_mode = False
        self.crop_mode = False
        self.model_running = False
        self.plc_connected = False
        self.current_model = "unet"
        
        # Timer for model simulation
        self.model_timer = QTimer()
        self.model_timer.timeout.connect(self.simulate_model_data)
        
        self.init_ui()

    def init_ui(self):
        # 设置全局按钮样式
        self.btn_style = """
            QPushButton {
                padding: 5px 15px;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Top control bar - made more compact
        top_control_layout = QHBoxLayout()
        top_control_layout.setSpacing(5)
        # top_control_layout.insertStretch(0, 1)  # 向右推整体控件
        
        # Video source selection
        top_control_layout.addWidget(QLabel("视频源"))
        self.video_source_combo = QComboBox()
        self.video_source_combo.addItems(["摄像头", "视频流"])
        self.video_source_combo.setFixedWidth(120)
        top_control_layout.addWidget(self.video_source_combo)
        self.video_source_combo.currentTextChanged.connect(self.handle_video_source_change)

        # Control buttons
        btn_style = """
            QPushButton {
                padding: 5px 15px;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        
        self.start_stop_btn = QPushButton("启动/停止模型")
        self.start_stop_btn.setFixedWidth(120)
        self.start_stop_btn.setStyleSheet(btn_style)
        self.start_stop_btn.clicked.connect(self.toggle_model)
        top_control_layout.addWidget(self.start_stop_btn)
        
        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems(["unet", "unet++", "yolo11_row"])
        self.model_combo.setFixedWidth(100)
        top_control_layout.addWidget(self.model_combo)
        
        self.switch_model_btn = QPushButton("切换模型")
        self.switch_model_btn.setFixedWidth(120)
        self.switch_model_btn.setStyleSheet(btn_style)
        self.switch_model_btn.clicked.connect(self.switch_model)
        top_control_layout.addWidget(self.switch_model_btn)
        
        # PLC controls
        self.plc_btn = QPushButton("连接/断开PLC")
        self.plc_btn.setStyleSheet(btn_style)
        self.plc_btn.clicked.connect(self.toggle_plc)
        top_control_layout.addWidget(self.plc_btn)
        
        # PLC status
        self.plc_status_btn = QPushButton("已断开")
        self.plc_status_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #ffcccc;
                color: red;
                min-height: 25px;
            }
        """)
        self.plc_status_btn.setEnabled(False)
        top_control_layout.addWidget(self.plc_status_btn)
        
        top_control_layout.addStretch()
        main_layout.addLayout(top_control_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        # Left side - Charts
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Bias curve
        bias_group = QGroupBox("偏移量曲线")
        bias_group.setFixedSize(300, 300)
        bias_layout = QVBoxLayout(bias_group)
        self.bias_plot = BiasPlotWidget()
        self.bias_plot.setFixedSize(280, 300)
        bias_layout.addWidget(self.bias_plot)
        left_layout.addWidget(bias_group)
        
        # Console output
        console_group = QGroupBox("控制台信息输出")
        console_group.setFixedSize(300, 300)
        console_layout = QVBoxLayout(console_group)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFixedSize(280, 300)
        console_layout.addWidget(self.console_output)
        left_layout.addWidget(console_group)
        
        content_layout.addLayout(left_layout)
        
        # Center - Video display
        video_group = QGroupBox("视频显示区域")
        video_layout = QVBoxLayout(video_group)
        self.video_label = CropWidget()
        self.video_label.setFixedSize(800, 640)
        self.video_label.setText("视频显示区域")
        self.video_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.video_label)
        video_group.setStyleSheet("border: 1px solid #ccc;")
        content_layout.addWidget(video_group)
        content_layout.setContentsMargins(10, 5, 10, 5)

        # Right side - Controls
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        # 设置右侧控件对齐顶部
        # right_layout.setAlignment(Qt.AlignTop)
        # Video controls
        video_control_group = QGroupBox("视频控制")
        video_control_layout = QVBoxLayout(video_control_group)
        video_control_layout.setSpacing(5)

        self.original_video_btn = QPushButton("原始视频")
        self.original_video_btn.setStyleSheet(btn_style)
        self.original_video_btn.clicked.connect(self.start_original_video)
        video_control_layout.addWidget(self.original_video_btn)
        
        self.ortho_video_btn = QPushButton("正射变换视频")
        self.ortho_video_btn.setStyleSheet(btn_style)
        self.ortho_video_btn.clicked.connect(self.start_ortho_video)
        self.ortho_video_btn.setEnabled(False)
        video_control_layout.addWidget(self.ortho_video_btn)
        
        self.cropped_video_btn = QPushButton("裁剪后视频")
        self.cropped_video_btn.setStyleSheet(btn_style)
        self.cropped_video_btn.clicked.connect(self.start_cropped_video)
        self.cropped_video_btn.setEnabled(False)
        video_control_layout.addWidget(self.cropped_video_btn)
        
        right_layout.addWidget(video_control_group)
        
        # Cropping tool
        crop_group = QGroupBox("裁剪工具")
        crop_layout = QVBoxLayout(crop_group)
        
        self.roi_tool_btn = QPushButton("默认裁剪")
        self.roi_tool_btn.setStyleSheet(btn_style)
        self.roi_tool_btn.clicked.connect(self.show_roi_tool)
        crop_layout.addWidget(self.roi_tool_btn)
        
        right_layout.addWidget(crop_group)
        
        # Cropping settings
        crop_settings_group = QGroupBox("裁剪设置")
        crop_settings_layout = QVBoxLayout(crop_settings_group)
        crop_settings_layout.setSpacing(5)
        # Margin sliders with labels and values
        margins_layout = QVBoxLayout()
        margins_layout.setSpacing(3)
        
        # Left margin
        left_layout_h = QHBoxLayout()
        left_layout_h.addWidget(QLabel("左边距"))
        left_layout_h.addStretch()
        self.left_value_label = QLabel("14")
        left_layout_h.addWidget(self.left_value_label)
        margins_layout.addLayout(left_layout_h)
        
        self.left_margin_slider = QSlider(Qt.Horizontal)
        self.left_margin_slider.setRange(0, 50)
        self.left_margin_slider.setValue(14)
        self.left_margin_slider.setFixedWidth(150)  # Reduced width
        self.left_margin_slider.valueChanged.connect(self.update_left_margin)
        margins_layout.addWidget(self.left_margin_slider)
        
        # Right margin
        right_layout_h = QHBoxLayout()
        right_layout_h.addWidget(QLabel("右边距"))
        right_layout_h.addStretch()
        self.right_value_label = QLabel("17")
        right_layout_h.addWidget(self.right_value_label)
        margins_layout.addLayout(right_layout_h)
        
        self.right_margin_slider = QSlider(Qt.Horizontal)
        self.right_margin_slider.setRange(0, 50)
        self.right_margin_slider.setValue(17)
        self.right_margin_slider.setFixedWidth(150)  # Reduced width
        self.right_margin_slider.valueChanged.connect(self.update_right_margin)
        margins_layout.addWidget(self.right_margin_slider)
        
        crop_settings_layout.addLayout(margins_layout)
        
        # Vertical sliders
        vertical_layout = QHBoxLayout()
        
        # Top margin
        top_v_layout = QVBoxLayout()
        top_v_layout.addWidget(QLabel("上边距"))
        self.top_margin_slider = QSlider(Qt.Vertical)
        self.top_margin_slider.setRange(0, 50)
        self.top_margin_slider.setValue(0)
        self.top_margin_slider.setFixedHeight(80)
        self.top_margin_slider.valueChanged.connect(self.update_top_margin)
        top_v_layout.addWidget(self.top_margin_slider)
        self.top_value_label = QLabel("0")
        top_v_layout.addWidget(self.top_value_label)
        vertical_layout.addLayout(top_v_layout)
        
        vertical_layout.addStretch()
        
        # Bottom margin  
        bottom_v_layout = QVBoxLayout()
        bottom_v_layout.addWidget(QLabel("下边距"))
        self.bottom_margin_slider = QSlider(Qt.Vertical)
        self.bottom_margin_slider.setRange(0, 50)
        self.bottom_margin_slider.setValue(0)
        self.bottom_margin_slider.setFixedHeight(80)
        self.bottom_margin_slider.valueChanged.connect(self.update_bottom_margin)
        bottom_v_layout.addWidget(self.bottom_margin_slider)
        self.bottom_value_label = QLabel("0")
        bottom_v_layout.addWidget(self.bottom_value_label)
        vertical_layout.addLayout(bottom_v_layout)
        
        crop_settings_layout.addLayout(vertical_layout)
        right_layout.addWidget(crop_settings_group)

        self.load_crop_params()  # 初始化时载入参数

        right_layout.addStretch()
        content_layout.addLayout(right_layout)
        
        main_layout.addLayout(content_layout)
        
        # Bottom status bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(5)
       
               
        params_layout = QHBoxLayout()
        params_layout.setSpacing(10)  # 更统一的控件间距

        def add_param(label_text, lineedit: QLineEdit, label_width=None, edit_width=None):
            sub_layout = QHBoxLayout()
            label = QLabel(label_text)
            if label_width:
                label.setFixedWidth(label_width)
            if edit_width:
                lineedit.setFixedWidth(edit_width)
            sub_layout.addWidget(label)
            sub_layout.addWidget(lineedit)
            params_layout.addLayout(sub_layout)


        self.height_input = QLineEdit("130")
        add_param("相机高度", self.height_input, label_width=70, edit_width=50)

        self.tilt_input = QLineEdit("49")
        add_param("倾斜角", self.tilt_input, label_width=60, edit_width=50)

        self.fov_x_input = QLineEdit("65")
        add_param("水平视场角", self.fov_x_input, label_width=90, edit_width=50)

        self.fov_y_input = QLineEdit("46")
        add_param("垂直视场角", self.fov_y_input, label_width=90, edit_width=50)

        # params_layout.addWidget(QLabel("保存路径"))
        # self.save_path_input = QLineEdit("")
        # self.save_path_input.setFixedWidth(300)
        # params_layout.addWidget(self.save_path_input)
        # self.browse_path_btn = QPushButton("浏览")
        # self.browse_path_btn.setFixedWidth(60)
        # self.browse_path_btn.clicked.connect(self.browse_save_path)
        # params_layout.addWidget(self.browse_path_btn)

        bottom_layout.addLayout(params_layout)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)
    # def handle_video_source_change(self, text):
    #     if text == "视频流":
    #         file_dialog = QFileDialog()
    #         file_path, _ = file_dialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov)")
    #         if file_path:
    #             success = self.video_thread.start_capture(file_path)
    #             if success:
    #                 self.ortho_video_btn.setEnabled(True)
    #                 self.cropped_video_btn.setEnabled(True)
    #                 self.log_message(f"已打开视频流文件: {file_path}")
    #                 self.ortho_mode = False
    #                 self.crop_mode = False
    #                 self.video_label.set_show_crop_rect(False)
    #                 self.video_label.set_show_row_lines(False)
    #             else:
    #                 self.log_message("无法打开选中的视频流文件")
    def save_crop_params(self):
        params = {
            "left": self.left_margin_slider.value(),
            "right": self.right_margin_slider.value(),
            "top": self.top_margin_slider.value(),
            "bottom": self.bottom_margin_slider.value()
        }
        try:
            with open("interrow_param.txt", "w") as f:
                json.dump(params, f)
            self.log_message("已保存裁剪参数到 interrow_param.txt")
        except Exception as e:
            self.log_message(f"保存裁剪参数失败: {e}")

    def load_crop_params(self):
        try:
            if os.path.exists("interrow_param.txt"):
                with open("interrow_param.txt", "r") as f:
                    params = json.load(f)
                self.left_margin_slider.setValue(params.get("left", 14))
                self.right_margin_slider.setValue(params.get("right", 17))
                self.top_margin_slider.setValue(params.get("top", 0))
                self.bottom_margin_slider.setValue(params.get("bottom", 0))
                self.log_message("已加载裁剪参数")
        except Exception as e:
            self.log_message(f"读取裁剪参数失败: {e}")

    def handle_video_source_change(self, text):
        if text == "视频流":
            # 先停止当前视频源
            if self.video_thread.running:
                self.video_thread.running = False
                self.video_thread.wait()
                
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self, 
                "选择视频文件", 
                "", 
                "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv)"
            )
            
            if file_path:
                # 先测试文件是否能打开
                test_cap = cv2.VideoCapture(file_path)
                if not test_cap.isOpened():
                    self.log_message(f"无法打开视频文件: {file_path}")
                    test_cap.release()
                    return
                test_cap.release()
                
                # 显示加载状态
                self.log_message(f"正在加载视频文件: {file_path}")
                QApplication.processEvents()
                
                # 启动视频线程
                success = self.video_thread.start_capture(file_path)
                if success:
                    self.ortho_video_btn.setEnabled(True)
                    self.cropped_video_btn.setEnabled(True)
                    self.log_message(f"成功打开视频流文件: {file_path}")
                    self.ortho_mode = False
                    self.crop_mode = False
                    self.video_label.set_show_crop_rect(False)
                    self.video_label.set_show_row_lines(False)
                    
                    # 立即显示第一帧
                    cap = cv2.VideoCapture(file_path)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        self.current_frame = frame
                        self.original_frame = frame
                        self.video_label.set_frame(frame)
                else:
                    self.log_message("无法打开选中的视频流文件")
                    self.video_label.clear()
                    self.video_label.setText("视频显示区域")
    # def browse_save_path(self):
    #     directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
    #     if directory:
    #         self.save_path_input.setText(directory)
    def update_left_margin(self, value):
        self.left_value_label.setText(str(value))
        self.update_crop_from_sliders()

    def update_right_margin(self, value):
        self.right_value_label.setText(str(value))
        self.update_crop_from_sliders()

    def update_top_margin(self, value):
        self.top_value_label.setText(str(value))
        self.update_crop_from_sliders()

    def update_bottom_margin(self, value):
        self.bottom_value_label.setText(str(value))
        self.update_crop_from_sliders()

    def log_message(self, message):
        """Add message to console output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_output.append(f"[{timestamp}] {message}")
        self.console_output.ensureCursorVisible()

    # def start_original_video(self):
    #     """Start original video stream"""
    #     if not self.video_thread.running:
    #         success = self.video_thread.start_capture(0)  # Use camera
    #         if success:
    #             self.ortho_video_btn.setEnabled(True)
    #             self.cropped_video_btn.setEnabled(True)
    #             self.log_message("成功接入原始视频")
    #             self.ortho_mode = False
    #             self.crop_mode = False
    #             self.video_label.set_show_crop_rect(False)
    #             self.video_label.set_show_row_lines(False)
    #         else:
    #             self.log_message("无法接入摄像头")
    #解决接入视频卡顿问题
    def start_original_video(self):
        """Start/stop original video stream with faster first frame display"""
        if not self.video_thread.running:
            # 显示加载状态
            self.original_video_btn.setText("正在连接...")
            QApplication.processEvents()
            
            # 快速获取首帧
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)

            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                if ret and frame is not None:
                    # 立即显示首帧
                    # frame = cv2.resize(frame, (640, 480))  # 确保尺寸
                    self.current_frame = frame
                    self.original_frame = frame
                    self.video_label.set_frame(frame)
                    QApplication.processEvents()
                    # self.log_message("快速显示首帧")
                    
                    # 启动视频线程
                    success = self.video_thread.start_capture(0)
                    if success:
                        self.ortho_video_btn.setEnabled(True)
                        self.cropped_video_btn.setEnabled(True)
                        self.log_message("成功接入原始视频")
                        self.ortho_mode = False
                        self.crop_mode = False
                        self.video_label.set_show_crop_rect(False)
                        self.video_label.set_show_row_lines(False)
                        self.original_video_btn.setText("停止原始视频")
                        self.original_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
                    else:
                        self.log_message("无法正式接入摄像头")
                        self.original_video_btn.setText("原始视频")
                else:
                    self.log_message("摄像头读取首帧失败")
                    self.original_video_btn.setText("原始视频")
            else:
                self.log_message("摄像头初始化失败")
                self.original_video_btn.setText("原始视频")
        else:
            # 停止视频
            self.video_thread.running = False
            self.video_thread.wait()
            # self.video_label.clear()
            # self.video_label.setText("视频显示区域")
            # self.video_label.current_frame = None  # 清空缓存帧，防止 update_display 再次绘制
            # self.video_label.reset_display()
            # self.video_label.setText("视频显示区域")
            self.video_label.set_frame(None)  # 强制地清空并显示默认文字
            self.current_frame = None         # 关键：清除帧缓存
            self.original_frame = None


            self.original_video_btn.setText("原始视频")
            self.original_video_btn.setStyleSheet(self.btn_style)
            self.log_message("已停止原始视频")

            # 恢复两个右侧按钮的状态
            self.ortho_video_btn.setText("正射变换视频")
            self.ortho_video_btn.setStyleSheet(self.btn_style)
            self.ortho_mode = False

            self.cropped_video_btn.setText("裁剪后视频")
            self.cropped_video_btn.setStyleSheet(self.btn_style)
            self.crop_mode = False

            self.ortho_video_btn.setEnabled(False)
            self.cropped_video_btn.setEnabled(False)

            # 关闭裁剪框显示与行线
            self.video_label.set_show_crop_rect(False)
            self.video_label.set_show_row_lines(False)


    def _start_camera_capture(self):
        """直接读取首帧并启动主视频线程"""
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None and frame.size > 0:
                self._handle_first_frame(frame)
            else:
                self.log_message("摄像头读取首帧失败")
        else:
            self.log_message("摄像头初始化失败")


    def _handle_first_frame(self, frame):
        """处理异步读取的首帧并启动正式视频线程"""
        self.current_frame = frame.copy()
        self.original_frame = frame.copy()
        self.video_label.set_frame(frame)
        QApplication.processEvents()
        # self.log_message("✅ 快速显示首帧")

        # 开启主视频线程
        success = self.video_thread.start_capture(0)
        if success:
            self.ortho_video_btn.setEnabled(True)
            self.cropped_video_btn.setEnabled(True)
            self.log_message("成功接入原始视频")
            self.ortho_mode = False
            self.crop_mode = False
            self.video_label.set_show_crop_rect(False)
            self.video_label.set_show_row_lines(False)
            self.original_video_btn.setText("停止原始视频")
            self.original_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
        else:
            self.log_message("无法正式接入摄像头")

    # def start_ortho_video(self):
    #     """Start orthophoto transformation video"""
    #     if self.current_frame is not None:
    #         try:
    #             self.bird_eye_transformer = BirdEyeTransformer(
    #                 camera_matrix=self.camera_matrix,
    #                 dist_coeffs=self.dist_coeffs,
    #                 fov_x=self.fov_x,
    #                 fov_y=self.fov_y,
    #                 camera_height=self.camera_height / 100,
    #                 tilt_angle=self.tilt_angle
    #             )
    #             self.ortho_mode = True
    #             self.crop_mode = False
    #             self.video_label.set_show_crop_rect(False)
    #             self.video_label.set_show_row_lines(False)
    #             self.log_message("成功接入正射变换视频")
    #             self.update_frame(self.current_frame)  # ← 立即刷新显示
    #         except Exception as e:
    #             self.log_message(f"正射变换失败: {e}")
    # def start_ortho_video(self):
    #     """Toggle orthophoto transformation video"""
    #     if not self.ortho_mode:
    #         if self.current_frame is not None:
    #             try:
    #                 self.bird_eye_transformer = BirdEyeTransformer(
    #                     camera_matrix=self.camera_matrix,
    #                     dist_coeffs=self.dist_coeffs,
    #                     fov_x=self.fov_x,
    #                     fov_y=self.fov_y,
    #                     camera_height=self.camera_height / 100,
    #                     tilt_angle=self.tilt_angle
    #                 )
    #                 self.ortho_mode = True
    #                 self.crop_mode = False
    #                 self.video_label.set_show_crop_rect(False)
    #                 self.video_label.set_show_row_lines(False)
    #                 self.log_message("成功接入正射变换视频")
    #                 self.ortho_video_btn.setText("关闭正射变换")
    #                 self.ortho_video_btn.setStyleSheet("background-color: #ccffcc;" + btn_style)
    #                 self.update_frame(self.current_frame)
    #             except Exception as e:
    #                 self.log_message(f"正射变换失败: {e}")
    #     else:
    #         self.ortho_mode = False
    #         self.log_message("已关闭正射变换视频")
    #         self.ortho_video_btn.setText("正射变换视频")
    #         self.ortho_video_btn.setStyleSheet(self.btn_style)
    #         self.update_frame(self.current_frame)
    def start_ortho_video(self):
        """Toggle orthophoto transformation video"""
        if not self.ortho_mode:
            if self.current_frame is not None:
                try:
                    # 读取用户输入参数
                    self.tilt_angle = float(self.tilt_input.text())
                    self.camera_height = float(self.height_input.text())
                    self.fov_x = float(self.fov_x_input.text())
                    self.fov_y = float(self.fov_y_input.text())

                    self.bird_eye_transformer = BirdEyeTransformer(
                        camera_matrix=self.camera_matrix,
                        dist_coeffs=self.dist_coeffs,
                        fov_x=self.fov_x,
                        fov_y=self.fov_y,
                        camera_height=self.camera_height / 100,  # cm -> m
                        tilt_angle=self.tilt_angle
                    )
                    self.ortho_mode = True
                    self.crop_mode = False
                    self.video_label.set_show_crop_rect(False)
                    self.video_label.set_show_row_lines(False)
                    self.log_message(f"成功接入正射变换视频 | 倾斜角: {self.tilt_angle}° 高度: {self.camera_height}cm")
                    self.ortho_video_btn.setText("关闭正射变换")
                    self.ortho_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
                    self.update_frame(self.current_frame)
                except Exception as e:
                    self.log_message(f"正射变换失败: {e}")
        else:
            self.ortho_mode = False
            self.log_message("已关闭正射变换视频")
            self.ortho_video_btn.setText("正射变换视频")
            self.ortho_video_btn.setStyleSheet(self.btn_style)
            self.update_frame(self.current_frame)

    def start_cropped_video(self):
        """Toggle cropped video display on/off"""
        # 若未启用，则启用裁剪模式
        if not self.crop_mode:
            self.crop_mode = True
            self.ortho_mode = True  # 通常裁剪是在正射后
            self.update_crop_from_sliders()
            self.video_label.set_show_crop_rect(False)
            self.video_label.set_show_row_lines(False)
            self.cropped_video_btn.setText("裁剪已启用")
            self.cropped_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
            self.log_message("显示裁剪后视频")
            self.save_crop_params()#在这里保存裁剪参数
        else:
            # 再次点击则关闭裁剪
            self.crop_mode = False
            self.cropped_video_btn.setText("裁剪后视频")
            self.cropped_video_btn.setStyleSheet(self.btn_style)
            self.log_message("已关闭裁剪视频")



    def show_roi_tool(self):
        """Show ROI tool"""
        self.video_label.set_show_crop_rect(True)
        self.update_crop_from_sliders()
        self.log_message("已启用默认裁剪")
    def update_crop_from_sliders(self):
        """Update crop rectangle from slider values"""
        if self.current_frame is None:
            return

        # Get current frame (with ortho if enabled)
        frame = self.current_frame.copy()
        if self.ortho_mode and self.bird_eye_transformer:
            try:
                frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
            except Exception as e:
                self.log_message(f"Ortho transformation failed: {e}")
                return

        frame_h, frame_w = frame.shape[:2]

        # Get margin percentages from sliders
        left_percent = self.left_margin_slider.value()
        right_percent = self.right_margin_slider.value()
        top_percent = self.top_margin_slider.value()
        bottom_percent = self.bottom_margin_slider.value()

        # Calculate margins in pixels
        left_margin = int(frame_w * left_percent / 100)
        right_margin = int(frame_w * right_percent / 100)
        top_margin = int(frame_h * top_percent / 100)
        bottom_margin = int(frame_h * bottom_percent / 100)

        # Calculate crop rectangle
        x = left_margin
        y = top_margin
        w = frame_w - left_margin - right_margin
        h = frame_h - top_margin - bottom_margin

        # Ensure valid dimensions
        x = max(0, min(x, frame_w-1))
        y = max(0, min(y, frame_h-1))
        w = max(1, min(w, frame_w-x))
        h = max(1, min(h, frame_h-y))

        self.video_label.set_crop_rect((x, y, w, h))
        self.video_label.set_show_crop_rect(True)  # 确保滑动时显示裁剪框
        self.video_label.update_display()
        # self.save_crop_params()  # 自动保存参数

    def toggle_model(self):
        """Toggle model on/off"""
        if self.model_running:
            self.model_running = False
            self.start_stop_btn.setText("启动模型")
            self.plc_status_btn.setText("已断开")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: red;
                    min-height: 25px;
                }
            """)
            self.model_timer.stop()
            self.log_message("模型已停止")
        else:
            self.model_running = True
            self.start_stop_btn.setText("停止模型")
            self.plc_status_btn.setText("已连接")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ccffcc;
                    color: green;
                    min-height: 25px;
                }
            """)
            self.model_timer.start(100)  # Update every 100ms
            self.log_message("模型已启动")

    def switch_model(self):
        """Switch between available models"""
        self.current_model = self.model_combo.currentText()
        self.log_message(f"已切换到{self.current_model}")

    def toggle_plc(self):
        """Toggle PLC connection"""
        if self.plc_connected:
            self.plc_connected = False
            self.plc_btn.setText("连接PLC")
            self.plc_status_btn.setText("已断开")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: red;
                    min-height: 25px;
                }
            """)
            self.log_message("PLC已断开")
        else:
            self.plc_connected = True
            self.plc_btn.setText("断开PLC")
            self.plc_status_btn.setText("已连接")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ccffcc;
                    color: green;
                    min-height: 25px;
                }
            """)
            self.log_message("PLC已连接")

    def simulate_model_data(self):
        """Simulate model data for testing"""
        if self.model_running:
            # Generate random bias value between -10 and 10
            bias_value = random.uniform(-10, 10)
            self.bias_plot.update_plot(bias_value)
            
            # Show row lines in video display
            self.video_label.set_show_row_lines(True)
            self.video_label.update_display()

    def save_original_video(self):
        """Save original video stream"""
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if save_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = os.path.join(save_dir, f"original_{timestamp}.mp4")
            self.log_message(f"开始保存原视频到: {video_path}")
            # Implementation for saving video would go here

    def save_processed_video(self):
        """Save processed video stream"""
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if save_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = os.path.join(save_dir, f"processed_{timestamp}.mp4")
            self.log_message(f"开始保存处理视频到: {video_path}")
            # Implementation for saving video would go here

    # def update_frame(self, frame):
    #     """Update frame from video thread"""
    #     print(f"[App] update_frame called | shape: {frame.shape}")
    #     self.current_frame = frame.copy()
    #     self.original_frame = frame.copy()
        
    #     # Apply transformations if needed
    #     display_frame = frame.copy()
    #     if self.ortho_mode and self.bird_eye_transformer:
    #         try:
    #             display_frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
    #         except Exception as e:
    #             self.log_message(f"Ortho transform error: {e}")
    #             return
        
    #     # Apply crop if needed
    #     if self.crop_mode and self.video_label.crop_rect:
    #         x, y, w, h = self.video_label.crop_rect
    #         display_frame = display_frame[y:y+h, x:x+w]
        
    #     # Update display
    #     self.video_label.set_frame(display_frame)
    #     self.video_label.update_display()

    #     QApplication.processEvents()  # 强制 UI 刷新
    def update_frame(self, frame):
        try:
            if frame is None or frame.size == 0:
                return
            # 如果视频线程已关闭，不再更新帧
            if not self.video_thread.running:
                return
        
            # 使用浅拷贝提高性能
            self.current_frame = frame
            
            # 在子线程中处理帧
            QTimer.singleShot(0, lambda: self._process_frame(frame))
           

        except Exception as e:
            print(f"[App] Frame update error: {e}")

    def _process_frame(self, frame):
        try:
            # 应用变换
            display_frame = frame.copy()
            if self.ortho_mode and self.bird_eye_transformer:
                display_frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)

            # 应用裁剪
            if self.crop_mode and self.video_label.crop_rect:
                x, y, w, h = self.video_label.crop_rect
                display_frame = display_frame[y:y+h, x:x+w]

            # ✅ 添加自然锐化（Unsharp Masking）
            blurred = cv2.GaussianBlur(display_frame, (5, 5), 1.0)
            display_frame = cv2.addWeighted(display_frame, 1.5, blurred, -0.5, 0)

            # 更新显示
            self.video_label.set_frame(display_frame)

        except Exception as e:
            print(f"[App] Frame processing error: {e}")



def main():
    app = QApplication(sys.argv)
    window = OrthophotoApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()