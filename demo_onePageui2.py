import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QFont
from qtpy import QtGui
import os
from datetime import datetime
import json
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import random
from clientside.client_io import IOClient

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
            
            if target_size is None:
                target_width = int(round(W_ground * self.pixels_per_meter))
                target_height = int(round(H_ground * self.pixels_per_meter))
            else:
                target_width, target_height = target_size

            # 限制图像最大输出尺寸（防止分辨率过高造成卡死）
            max_width = 1920
            max_height = 1080
            if target_width > max_width or target_height > max_height:
                scale_factor = min(max_width / target_width, max_height / target_height)
                target_width = int(target_width * scale_factor)
                target_height = int(target_height * scale_factor)
                # print(f"[BirdEyeTransformer] ⚠️ 正射图像缩放至最大限制：{target_width}x{target_height}")
                print(f"[BirdEyeTransformer] 警告: 正射图像缩放至最大限制: {target_width}x{target_height}")


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
            # bird_eye_img = cv2.warpPerspective(img_undistorted, H_final, output_size, flags=cv2.INTER_LINEAR)

            # # Auto-crop black borders
            # gray = cv2.cvtColor(bird_eye_img, cv2.COLOR_BGR2GRAY)
            bird_eye_img = cv2.warpPerspective(img_undistorted, H_final, output_size, flags=cv2.INTER_LINEAR)

            # 如果图像为空，提前返回 None，防止崩溃
            if bird_eye_img is None or bird_eye_img.size == 0:
                print("[BirdEyeTransformer] warpPerspective failed: output is empty.")
                return None, None

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
            
    

class CropWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("border: 1px solid #ddd; background-color: white;")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignCenter)

        self.crop_rect = None
        self.dragging = False
        self.drag_start = None
        self.current_frame = None
        self.show_crop_rect = False
        self.show_row_lines = False

    def set_frame(self, frame):
        self.current_frame = frame.copy()
        self.update_display()

    def set_crop_rect(self, rect):
        self.crop_rect = rect
        self.update_display()

    def set_show_crop_rect(self, show):
        self.show_crop_rect = show
        self.update_display()

    def set_show_row_lines(self, show):
        self.show_row_lines = show
        self.update_display()

    def update_display(self):
        if self.current_frame is None:
            return
            
        try:
            # 将OpenCV图像转换为QImage
            rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb.shape
            bytes_per_line = 3 * width
            q_img = QImage(rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # 创建QPixmap并绘制
            pixmap = QPixmap.fromImage(q_img)
            
            # 如果需要显示裁剪框且裁剪框存在
            if self.show_crop_rect and self.crop_rect is not None:
                # 创建一个新的绘图设备
                new_pixmap = QPixmap(pixmap.size())
                new_pixmap.fill(Qt.transparent)
                
                # 在新的绘图设备上绘制原始图像和裁剪框
                painter = QPainter(new_pixmap)
                painter.drawPixmap(0, 0, pixmap)
                
                # 设置画笔样式
                pen = QPen(Qt.green, 2, Qt.DashLine)
                painter.setPen(pen)
                
                # 绘制裁剪框
                x, y, w, h = self.crop_rect
                painter.drawRect(x, y, w, h)
                painter.end()
                
                pixmap = new_pixmap
            
            # 显示到QLabel
            self.setPixmap(pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))
            
        except Exception as e:
            print(f"[CropWidget] Display error: {e}")
class BiasPlotWidget(FigureCanvas):
    def __init__(self):
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        matplotlib.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['font.size'] = 10
        
        self.figure = Figure(figsize=(3.5, 2.2), facecolor='white')
        super().__init__(self.figure)
        self.setParent(None)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel("偏移量")
        self.ax.grid(True, alpha=0.3)
        
        self.data_x = []
        self.data_y = []
        self.max_points = 20
        self.time_counter = 0
        
        self.line, = self.ax.plot([], [], 'b-', linewidth=2)
        self.figure.tight_layout()

    def update_plot(self, bias_value):
        self.time_counter += 1
        self.data_x.append(self.time_counter)
        self.data_y.append(bias_value)
        
        if len(self.data_x) > self.max_points:
            self.data_x = self.data_x[-self.max_points:]
            self.data_y = self.data_y[-self.max_points:]
        
        self.line.set_data(self.data_x, self.data_y)
        
        if self.data_x and self.data_y:
            self.ax.set_xlim(min(self.data_x), max(self.data_x))
            self.ax.set_ylim(min(self.data_y) - 1, max(self.data_y) + 1)
        
        self.draw()


class OrthophotoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("中控系统监控大屏")
        
        # 设置应用程序字体
        self.setup_fonts()
        
        # 设置固定1024×768分辨率
        self.base_width = 1024
        self.base_height = 768
        self.setFixedSize(self.base_width, self.base_height)

        # Initialize variables
        self.current_frame = None
        self.original_frame = None
        self.camera_height = 130.0
        self.tilt_angle = -49
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
    
        # 视频文件播放相关
        self.video_cap = None
        self.video_file_timer = QTimer(self)
        self.video_file_timer.timeout.connect(self.read_video_frame)

        # State variables
        self.ortho_mode = False
        self.crop_mode = False
        self.model_running = True
        self.plc_connected = False
        self.current_model = "unet"
         # 初始化 model_timer
        self.model_timer = QTimer(self)
        self.model_timer.timeout.connect(self.update_model)
            
        self.init_ui()

        # Initialize IOClient
        server_ip = '192.168.137.100'
        video_port = 8090
        instruction_port = 8091
        system_type = 'interrow_weeder'
        self.clientio = IOClient(server_ip, video_port, instruction_port, system_type)
        self.clientio.video_client.connect_video_displayer(self.update_frame)
        self.clientio.video_client.connect_plotter(self.plot_bias)

    def setup_fonts(self):
        """设置应用程序字体"""
        font = QFont("Microsoft YaHei", 10)
        font.setBold(False)
        font.setWeight(QFont.Normal)
        QApplication.setFont(font)
        font.setStyleHint(QFont.SansSerif, QFont.PreferAntialias)

    def get_clientio(self):
        return self.clientio

    def init_ui(self):
        # 定义全局样式
        self.btn_style = """
            QPushButton {
                padding: 6px 12px;
                font-size: 12px;
                font-weight: normal;
                font-family: 'Microsoft YaHei';
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f8f8;
                color: #333;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #b0b0b0;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
            }
        """
        
        self.label_style = """
            QLabel {
                font-size: 12px;
                font-weight: normal;
                font-family: 'Microsoft YaHei';
                color: #333;
            }
        """
        
        self.group_style = """
            QGroupBox {
                font-size: 13px;
                font-weight: normal;
                font-family: 'Microsoft YaHei';
                color: #333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                background-color: white;
            }
        """
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # 顶部控制栏
        top_control_layout = QHBoxLayout()
        top_control_layout.setSpacing(8)
        
        # # 摄像头选择
        # camera_label = QLabel("摄像头")
        # camera_label.setStyleSheet(self.label_style)
        # top_control_layout.addWidget(camera_label)
        # self.camera_combo = QComboBox()
        # self.camera_combo.addItems(["摄像头1", "摄像头2", "摄像头3"])
        # self.camera_combo.setFixedWidth(100)
        # self.camera_combo.setStyleSheet("""
        #     QComboBox {
        #         font-size: 12px;
        #         font-family: 'Microsoft YaHei';
        #         font-weight: normal;
        #         padding: 4px;
        #         border: 1px solid #d0d0d0;
        #         border-radius: 3px;
        #         background-color: white;
        #         color: #333;
        #     }
        # """)
        # top_control_layout.addWidget(self.camera_combo)
        
        # 视频源选择
        video_label = QLabel("视频源")
        video_label.setStyleSheet(self.label_style)
        top_control_layout.addWidget(video_label)
        self.video_source_combo = QComboBox()
        self.video_source_combo.addItems(["摄像头", "视频流"])
        self.video_source_combo.setFixedWidth(100)
        self.video_source_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                padding: 4px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: white;
                color: #333;
            }
        """)
        top_control_layout.addWidget(self.video_source_combo)
        
        # 控制按钮
        self.start_stop_btn = QPushButton("启动/停止模型")
        self.start_stop_btn.setFixedWidth(120)
        self.start_stop_btn.setStyleSheet(self.btn_style)
        self.start_stop_btn.clicked.connect(self.toggle_model)
        top_control_layout.addWidget(self.start_stop_btn)


       
        
        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.addItems(["unet", "unet++", "yolo11_row"])
        self.model_combo.setFixedWidth(100)
        self.model_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                padding: 4px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: white;
                color: #333;
            }
        """)
        top_control_layout.addWidget(self.model_combo)
        
        self.switch_model_btn = QPushButton("切换模型")
        self.switch_model_btn.setFixedWidth(80)
        self.switch_model_btn.setStyleSheet(self.btn_style)
        self.switch_model_btn.clicked.connect(self.switch_model)
        top_control_layout.addWidget(self.switch_model_btn)
        
        # PLC控制
        self.plc_btn = QPushButton("连接/断开PLC")
        self.plc_btn.setFixedWidth(120)
        self.plc_btn.setStyleSheet(self.btn_style)
        self.plc_btn.clicked.connect(self.toggle_plc)
        top_control_layout.addWidget(self.plc_btn)
        
        # PLC状态
        self.plc_status_btn = QPushButton("已断开")
        self.plc_status_btn.setFixedWidth(70)
        self.plc_status_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 12px;
                font-weight: normal;
                font-family: 'Microsoft YaHei';
                border: 1px solid #ffaaaa;
                border-radius: 4px;
                background-color: #ffe6e6;
                color: #cc0000;
                min-height: 28px;
            }
        """)
        self.plc_status_btn.setEnabled(False)
        top_control_layout.addWidget(self.plc_status_btn)
        # self.tilt_input.editingFinished.connect(self.update_bird_eye_transformer)

        top_control_layout.addStretch()
        main_layout.addLayout(top_control_layout)
        
        # 主内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        
        # 左侧 - 图表和控制台 (25%)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        
        # 偏移量曲线
        bias_group = QGroupBox("偏移量曲线")
        bias_group.setStyleSheet(self.group_style)
        bias_layout = QVBoxLayout(bias_group)
        bias_layout.setContentsMargins(6, 12, 6, 6)
        
        self.bias_plot = BiasPlotWidget()
        self.bias_plot.setMinimumSize(200, 150)
        bias_layout.addWidget(self.bias_plot)
        left_layout.addWidget(bias_group)
        
        # 控制台输出
        console_group = QGroupBox("控制台信息输出")
        console_group.setStyleSheet(self.group_style)
        console_layout = QVBoxLayout(console_group)
        console_layout.setContentsMargins(6, 12, 6, 6)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMinimumSize(200, 200)
        self.console_output.setStyleSheet("""
            QTextEdit {
                font-size: 11px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #333;
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 6px;
                line-height: 1.3;
            }
        """)
        console_layout.addWidget(self.console_output)
        left_layout.addWidget(console_group)
        
        content_layout.addLayout(left_layout, 2)  # 25%宽度
        
        # 底部状态栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)
        bottom_layout.setContentsMargins(0, 2, 0, 2)
        
        # 参数输入
        params_layout = QHBoxLayout()
        params_layout.setSpacing(6)

      
       # 在 init_ui 方法中，找到视频显示区域的代码部分，修改如下：

        # 中间 - 视频显示区域 (50%)
        video_group = QGroupBox("视频显示区域")
        video_group.setStyleSheet(self.group_style)
        video_layout = QVBoxLayout(video_group)
        video_layout.setAlignment(Qt.AlignTop)
        video_layout.setContentsMargins(6, 12, 6, 6)

        # 蓝色加粗标题（在 groupBox 内部）
        video_title_label = QLabel("基于计算机视觉的智能农机自动对行系统")
        video_title_label.setAlignment(Qt.AlignCenter)
        video_title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                color: #0033cc;
            }
        """)
        video_layout.addWidget(video_title_label)

        # 视频显示 QLabel
        self.video_label = CropWidget()
        self.video_label.setMinimumSize(625, 469)  # 4:3 显示区域
        self.video_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.video_label.setText("视频显示区域")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #666;
                background-color: #f8f8f8;
                border: 2px dashed #ddd;
                border-radius: 6px;
            }
        """)
        video_layout.addWidget(self.video_label)

        # 添加相机参数控制面板在视频下方
        params_group = QGroupBox("相机参数设置")
        params_group.setStyleSheet(self.group_style)
        params_layout = QHBoxLayout(params_group)
        params_layout.setContentsMargins(6, 12, 6, 6)

        def add_param(label_text, lineedit: QLineEdit):
            sub_layout = QHBoxLayout()
            sub_layout.setSpacing(2)
            label = QLabel(label_text)
            label.setFixedWidth(60)
            label.setStyleSheet("font-size: 11px; font-weight: bold;")
            lineedit.setFixedWidth(40)
            lineedit.setStyleSheet("font-size: 11px; padding: 2px;")
            sub_layout.addWidget(label)
            sub_layout.addWidget(lineedit)
            sub_layout.setContentsMargins(0, 0, 0, 0)
            params_layout.addLayout(sub_layout)

        self.height_input = QLineEdit("60")
        add_param("相机高度", self.height_input)

        self.tilt_input = QLineEdit("49")
        add_param("倾斜角", self.tilt_input)

        self.tilt_input.editingFinished.connect(self.update_bird_eye_transformer)

        self.fov_x_input = QLineEdit("65")
        add_param("水平视场角", self.fov_x_input)

        self.fov_y_input = QLineEdit("46")
        add_param("垂直视场角", self.fov_y_input)

         # 在创建完所有输入框后，再连接信号
        self.tilt_input.editingFinished.connect(self.update_bird_eye_transformer)
        self.height_input.editingFinished.connect(self.update_bird_eye_transformer)
        self.fov_x_input.editingFinished.connect(self.update_bird_eye_transformer)
        self.fov_y_input.editingFinished.connect(self.update_bird_eye_transformer)


        video_layout.addWidget(params_group)

        # 加入主内容布局
        content_layout.addWidget(video_group, 6)
                        
        # 右侧 - 控制面板 (25%)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        
        # 视频控制
        video_control_group = QGroupBox("视频控制")
        video_control_group.setStyleSheet(self.group_style)
        video_control_layout = QVBoxLayout(video_control_group)
        video_control_layout.setSpacing(6)
        video_control_layout.setContentsMargins(6, 12, 6, 6)

        self.original_video_btn = QPushButton("原始视频")
        self.original_video_btn.setStyleSheet(self.btn_style)
        self.original_video_btn.clicked.connect(self.start_original_video)
        video_control_layout.addWidget(self.original_video_btn)
        
        self.ortho_video_btn = QPushButton("正射变换视频")
        self.ortho_video_btn.setStyleSheet(self.btn_style)
        self.ortho_video_btn.clicked.connect(self.start_ortho_video)
        self.ortho_video_btn.setEnabled(False)
        video_control_layout.addWidget(self.ortho_video_btn)
        
        self.cropped_video_btn = QPushButton("裁剪后视频")
        self.cropped_video_btn.setStyleSheet(self.btn_style)
        self.cropped_video_btn.clicked.connect(self.start_cropped_video)
        self.cropped_video_btn.setEnabled(False)
        video_control_layout.addWidget(self.cropped_video_btn)
        
        right_layout.addWidget(video_control_group)
        
        # 裁剪工具
        crop_group = QGroupBox("裁剪工具")
        crop_group.setStyleSheet(self.group_style)
        crop_layout = QVBoxLayout(crop_group)
        crop_layout.setContentsMargins(6, 12, 6, 6)
        
        self.roi_tool_btn = QPushButton("默认裁剪")
        self.roi_tool_btn.setStyleSheet(self.btn_style)
        self.roi_tool_btn.clicked.connect(self.show_roi_tool)
        crop_layout.addWidget(self.roi_tool_btn)
        
        right_layout.addWidget(crop_group)
        
        # 裁剪设置
        crop_settings_group = QGroupBox("裁剪设置")
        crop_settings_group.setStyleSheet(self.group_style)
        crop_settings_layout = QVBoxLayout(crop_settings_group)
        crop_settings_layout.setSpacing(6)
        crop_settings_layout.setContentsMargins(6, 12, 6, 6)
        
        # 水平边距
        margins_layout = QVBoxLayout()
        margins_layout.setSpacing(4)
        
        # 左边距
        left_layout_h = QHBoxLayout()
        left_label = QLabel("左")
        left_label.setStyleSheet(self.label_style)
        left_layout_h.addWidget(left_label)
        left_layout_h.addStretch()
        self.left_value_label = QLabel("36")
        self.left_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #0066cc;
                min-width: 20px;
            }
        """)
        left_layout_h.addWidget(self.left_value_label)
        margins_layout.addLayout(left_layout_h)
        
        self.left_margin_slider = QSlider(Qt.Horizontal)
        self.left_margin_slider.setRange(0, 50)
        self.left_margin_slider.setValue(36)
        self.left_margin_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #f0f0f0;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0066cc;
                border: 1px solid #0055aa;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #0077dd;
            }
        """)
        self.left_margin_slider.valueChanged.connect(self.update_left_margin)
        margins_layout.addWidget(self.left_margin_slider)
        
        # 右边距
        right_layout_h = QHBoxLayout()
        right_label = QLabel("右")
        right_label.setStyleSheet(self.label_style)
        right_layout_h.addWidget(right_label)
        right_layout_h.addStretch()
        self.right_value_label = QLabel("10")
        self.right_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #0066cc;
                min-width: 20px;
            }
        """)
        right_layout_h.addWidget(self.right_value_label)
        margins_layout.addLayout(right_layout_h)
        
        self.right_margin_slider = QSlider(Qt.Horizontal)
        self.right_margin_slider.setRange(0, 50)
        self.right_margin_slider.setValue(10)
        self.right_margin_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #f0f0f0;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0066cc;
                border: 1px solid #0055aa;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #0077dd;
            }
        """)
        self.right_margin_slider.valueChanged.connect(self.update_right_margin)
        margins_layout.addWidget(self.right_margin_slider)
        
        crop_settings_layout.addLayout(margins_layout)
        
        # 垂直边距
        vertical_layout = QHBoxLayout()
        
        # 上边距
        top_v_layout = QVBoxLayout()
        top_label = QLabel("上")
        top_label.setStyleSheet(self.label_style)
        top_v_layout.addWidget(top_label)
        self.top_margin_slider = QSlider(Qt.Vertical)
        self.top_margin_slider.setRange(0, 50)
        self.top_margin_slider.setValue(0)
        self.top_margin_slider.setFixedHeight(60)
        self.top_margin_slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #bbb;
                background: #f0f0f0;
                width: 4px;
                border-radius: 2px;
            }
            QSlider::handle:vertical {
                background: #0066cc;
                border: 1px solid #0055aa;
                width: 12px;
                height: 12px;
                margin: 0 -4px;
                border-radius: 6px;
            }
            QSlider::handle:vertical:hover {
                background: #0077dd;
            }
        """)
        self.top_margin_slider.valueChanged.connect(self.update_top_margin)
        top_v_layout.addWidget(self.top_margin_slider)
        self.top_value_label = QLabel("0")
        self.top_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #0066cc;
            }
        """)
        top_v_layout.addWidget(self.top_value_label)
        vertical_layout.addLayout(top_v_layout)
        
        vertical_layout.addStretch()
        
        # 下边距
        bottom_v_layout = QVBoxLayout()
        bottom_label = QLabel("下")
        bottom_label.setStyleSheet(self.label_style)
        bottom_v_layout.addWidget(bottom_label)
        self.bottom_margin_slider = QSlider(Qt.Vertical)
        self.bottom_margin_slider.setRange(0, 50)
        self.bottom_margin_slider.setValue(0)
        self.bottom_margin_slider.setFixedHeight(60)
        self.bottom_margin_slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #bbb;
                background: #f0f0f0;
                width: 4px;
                border-radius: 2px;
            }
            QSlider::handle:vertical {
                background: #0066cc;
                border: 1px solid #0055aa;
                width: 12px;
                height: 12px;
                margin: 0 -4px;
                border-radius: 6px;
            }
            QSlider::handle:vertical:hover {
                background: #0077dd;
            }
        """)
        self.bottom_margin_slider.valueChanged.connect(self.update_bottom_margin)
        bottom_v_layout.addWidget(self.bottom_margin_slider)
        self.bottom_value_label = QLabel("0")
        self.bottom_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-family: 'Microsoft YaHei';
                font-weight: normal;
                color: #0066cc;
            }
        """)
        bottom_v_layout.addWidget(self.bottom_value_label)
        vertical_layout.addLayout(bottom_v_layout)
        
        crop_settings_layout.addLayout(vertical_layout)
        right_layout.addWidget(crop_settings_group)
        
        right_layout.addStretch()
        content_layout.addLayout(right_layout, 2)  # 25%宽度
        
        main_layout.addLayout(content_layout)
        self.video_source_combo.currentTextChanged.connect(self.handle_video_source_change)
       
        # main_layout.addLayout(bottom_layout)
    def update_model(self):
        """定时更新模型数据"""
        if not self.model_running:
            return
        
        try:
            # 1. 从服务器获取最新偏移量数据（这里模拟获取数据）
            # 实际应用中应该从你的IOClient获取真实数据
            current_time = datetime.now().strftime("%H:%M:%S")
            bias_value = random.uniform(-5, 5)  # 模拟偏移量数据
            
            # 2. 更新数据存储
            self.time_data.append(current_time)
            self.bias_data.append(bias_value)
            
            # 保持数据量不超过最大显示点数
            if len(self.time_data) > self.max_data_points:
                self.time_data = self.time_data[-self.max_data_points:]
                self.bias_data = self.bias_data[-self.max_data_points:]
            
            # 3. 更新图表显示
            self.update_bias_plot(self.time_data, self.bias_data)
            
            # 4. 根据偏移量生成控制指令（示例）
            self.generate_control_signal(bias_value)
            
            # 5. 更新状态信息
            self.log_message(f"模型更新 - 偏移量: {bias_value:.2f} cm")
            
        except Exception as e:
            self.log_message(f"模型更新错误: {str(e)}")

    def update_bird_eye_transformer(self):
        """根据界面输入参数更新正射变换器"""
        try:
            tilt = float(self.tilt_input.text())
            height = float(self.height_input.text())
            fov_x = float(self.fov_x_input.text())
            fov_y = float(self.fov_y_input.text())

            self.bird_eye_transformer = BirdEyeTransformer(
                camera_matrix=self.camera_matrix,
                dist_coeffs=self.dist_coeffs,
                fov_x=fov_x,
                fov_y=fov_y,
                camera_height=height,
                tilt_angle=tilt
            )

            self.log_message(f"✅ 正射变换参数更新成功 - 倾斜角: {tilt}°")

            if self.current_frame is not None and self.ortho_mode:
                self.update_frame(self.current_frame)

        except Exception as e:
            self.log_message(f"❌ 正射变换器更新失败: {e}")

    def generate_control_signal(self, bias_value):
        """根据偏移量生成控制指令"""
        if not self.plc_connected:
            return
        
        # 设置阈值，超过阈值才发送控制指令
        threshold = 1.0  # 1厘米
        
        if abs(bias_value) > threshold:
            direction = "左" if bias_value > 0 else "右"
            correction_value = min(abs(bias_value), 5.0)  # 限制最大修正值
            
            # 这里应该是实际发送给PLC的指令
            # 示例: self.clientio.send_plc_command(...)
            
            self.log_message(f"发送控制指令: 向{direction}修正 {correction_value:.1f} cm")


    def handle_video_source_change(self, text):
        if text == "视频流":
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "选择视频文件",
                "",
                "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv)"
            )

            if file_path:
                if self.video_cap:  # 释放旧视频
                    self.video_cap.release()
                self.video_cap = cv2.VideoCapture(file_path)

                if not self.video_cap.isOpened():
                    self.log_message(f"❌ 无法打开视频文件: {file_path}")
                    return

                self.log_message(f"✅ 成功打开视频文件: {file_path}")
                self.ortho_video_btn.setEnabled(True)
                self.cropped_video_btn.setEnabled(True)
                self.ortho_mode = False
                self.crop_mode = False
                self.video_label.set_show_crop_rect(False)
                self.video_label.set_show_row_lines(False)

                # 启动播放定时器，约30FPS
                self.video_file_timer.start(33)

        elif text == "摄像头":
            # 切换回摄像头模式时关闭定时器
            if self.video_cap:
                self.video_cap.release()
                self.video_cap = None
            # self.video_file_timer.stop()
            self.log_message("📷 切换回摄像头模式")

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

    def start_original_video(self):
        """Start/stop original video stream"""
        if not self.original_video_active:
            self.get_clientio().start_model()
            self.original_video_btn.setText("停止原始视频")
            self.original_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
            self.ortho_video_btn.setEnabled(False)
            self.cropped_video_btn.setEnabled(False)
            self.original_video_active = True
            self.log_message("原始视频已启动")
            self.original_video_active = False

        else:
            self.get_clientio().stop_video()
            self.reset_video_buttons()
    def reset_video_buttons(self):
        """Reset all video buttons to default state"""
        self.original_video_btn.setText("原始视频")
        self.original_video_btn.setStyleSheet(self.btn_style)
        self.ortho_video_btn.setText("正射变换视频")
        self.ortho_video_btn.setStyleSheet(self.btn_style)
        self.cropped_video_btn.setText("裁剪后视频")
        self.cropped_video_btn.setStyleSheet(self.btn_style)
        
        # 根据当前模式设置按钮状态
        self.original_video_btn.setEnabled(True)
        self.ortho_video_btn.setEnabled(True)
        self.cropped_video_btn.setEnabled(True)
        
        self.original_video_active = False
        self.ortho_mode = False
        self.crop_mode = False
    def start_ortho_video(self):
        """开启或关闭正射变换模式（允许与裁剪叠加）"""
        if not self.ortho_mode:
            self.ortho_mode = True
            self.ortho_video_btn.setText("关闭正射变换")
            self.ortho_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
            self.log_message("✅ 正射变换模式已启用")

            # 如果视频未在播放，则启动定时器
            if self.video_source_combo.currentText() == "视频流" and not self.video_file_timer.isActive():
                self.video_file_timer.start(33)
                self.log_message("▶️ 启动正射后视频播放")

        else:
            self.ortho_mode = False
            self.ortho_video_btn.setText("正射变换视频")
            self.ortho_video_btn.setStyleSheet(self.btn_style)
            self.log_message("❎ 正射变换模式已关闭")

        # 强制刷新当前帧
        if self.current_frame is not None:
            self.update_frame(self.current_frame)


    def start_cropped_video(self):
        """开启或关闭裁剪模式（允许与正射叠加）"""
        if not self.crop_mode:
            # 启用裁剪模式
            self.crop_mode = True
            self.cropped_video_btn.setText("关闭裁剪")
            self.cropped_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
            self.log_message("✅ 裁剪模式已开启")

            #  不禁用正射按钮，允许叠加使用
            self.original_video_btn.setEnabled(False)
            self.video_label.set_show_crop_rect(False)  # 不显示绿色虚线框


            # 如果是视频文件，确保定时器正在播放
            if self.video_source_combo.currentText() == "视频流" and not self.video_file_timer.isActive():
                self.video_file_timer.start(33)
                self.log_message("▶️ 正在播放正射+裁剪后视频")

        else:
            # 关闭裁剪模式
            self.crop_mode = False
            self.cropped_video_btn.setText("裁剪后视频")
            self.cropped_video_btn.setStyleSheet(self.btn_style)
            self.original_video_btn.setEnabled(True)
            self.log_message("❎ 裁剪模式已关闭")
            self.video_label.set_show_crop_rect(False)

        # 刷新当前帧显示
        if self.current_frame is not None:
            self.update_frame(self.current_frame)

    def show_roi_tool(self):
        """点击‘默认裁剪’按钮的行为：激活裁剪并立即生效"""
        self.video_label.set_show_crop_rect(False)  # ✅ 不显示绿色裁剪框

        # 强制进入裁剪模式（如果尚未开启）
        if not self.crop_mode:
            self.crop_mode = True
            self.cropped_video_btn.setText("关闭裁剪")
            self.cropped_video_btn.setStyleSheet("background-color: #ccffcc;" + self.btn_style)
            self.log_message("✅ 默认裁剪已开启裁剪模式")

        # 确保定时器在播放中
        if self.video_source_combo.currentText() == "视频流" and not self.video_file_timer.isActive():
            self.video_file_timer.start(33)
            self.log_message("▶️ 默认裁剪播放已启动")

        # 执行裁剪并强制刷新帧
        self.update_crop_from_sliders()
        if self.current_frame is not None:
            self.update_frame(self.current_frame)

        self.log_message("✅ 已启用默认裁剪区域并刷新帧")



    def update_crop_from_sliders(self):
        """Update crop rectangle from slider values"""
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()
        if hasattr(self, 'bird_eye_transformer') and self.ortho_mode and self.bird_eye_transformer:
            try:
                frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
            except Exception as e:
                self.log_message(f"Ortho transformation failed: {e}")
                return

        frame_h, frame_w = frame.shape[:2]

        left_percent = self.left_margin_slider.value()
        right_percent = self.right_margin_slider.value()
        top_percent = self.top_margin_slider.value()
        bottom_percent = self.bottom_margin_slider.value()

        left_margin = int(frame_w * left_percent / 100)
        right_margin = int(frame_w * right_percent / 100)
        top_margin = int(frame_h * top_percent / 100)
        bottom_margin = int(frame_h * bottom_percent / 100)

        x = left_margin
        y = top_margin
        w = frame_w - left_margin - right_margin
        h = frame_h - top_margin - bottom_margin

        x = max(0, min(x, frame_w-1))
        y = max(0, min(y, frame_h-1))
        w = max(1, min(w, frame_w-x))
        h = max(1, min(h, frame_h-y))

        # 确保裁剪框坐标有效
        if w > 0 and h > 0:
            self.video_label.set_crop_rect((x, y, w, h))
            self.video_label.set_show_crop_rect(True)
            # 强制更新显示
            self.video_label.update_display()
            
    def toggle_model(self):
        """切换模型运行状态"""
        if self.model_running:
            self.stop_model()
        else:
            self.start_model()

    def start_model(self):
        """启动模型"""
        try:
            # 1. 启动模型逻辑
            self.clientio.start_model()  # 调用IOClient启动模型
            
            # 2. 更新UI状态
            self.model_running = True
            self.start_stop_btn.setText("停止模型")
            self.plc_status_btn.setText("运行中")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    font-size: 11px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ccffcc;
                    color: green;
                    min-height: 22px;
                }
            """)
            
            # 3. 启动定时器(100ms更新一次)
            self.model_timer.start(100)
            
            # 4. 记录日志
            self.log_message("模型已启动")
            
            # 5. 初始化数据
            self.bias_data = []
            self.time_data = []
            
        except Exception as e:
            self.log_message(f"启动模型失败: {str(e)}")
            self.model_running = False
            self.start_stop_btn.setText("启动模型")

    def stop_model(self):
        """停止模型"""
        try:
            # 1. 停止模型逻辑
            self.clientio.stop_model()  # 调用IOClient停止模型
            
            # 2. 更新UI状态
            self.model_running = False
            self.start_stop_btn.setText("启动模型")
            self.plc_status_btn.setText("已停止")
            self.plc_status_btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    font-size: 11px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: red;
                    min-height: 22px;
                }
            """)
            
            # 3. 停止定时器
            self.model_timer.stop()
            
            # 4. 记录日志
            self.log_message("模型已停止")
            
        except Exception as e:
            self.log_message(f"停止模型失败: {str(e)}")

    def update_model(self):
        """定时更新模型状态"""
        if not self.model_running:
            return
        
        try:
            # 1. 获取最新数据
            status = self.clientio.get_model_status()
            bias_value = self.clientio.get_latest_bias()
            
            # 2. 更新数据存储
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_data.append(current_time)
            self.bias_data.append(bias_value)
            
            # 保持最近20个数据点
            if len(self.time_data) > 20:
                self.time_data = self.time_data[-20:]
                self.bias_data = self.bias_data[-20:]
            
            # 3. 更新图表
            self.plot_bias(self.time_data, self.bias_data)
            
            # 4. 检查状态异常
            if status.get("error"):
                self.log_message(f"模型异常: {status['error']}")
                self.stop_model()
                
        except Exception as e:
            self.log_message(f"更新模型状态错误: {str(e)}")
            # 发生错误时自动停止模型
            self.stop_model()
            
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

    def plot_bias(self, time_list, bias_list):
        """更新偏移量曲线图"""
        try:
            if not self.model_running or not time_list or not bias_list:
                return
                
            # 确保数据长度一致
            min_len = min(len(time_list), len(bias_list))
            time_list = time_list[-min_len:]
            bias_list = bias_list[-min_len:]
            
            # 更新图表
            self.bias_plot.data_x = list(range(len(time_list)))
            self.bias_plot.data_y = bias_list
            self.bias_plot.line.set_data(self.bias_plot.data_x, self.bias_plot.data_y)
            
            if self.bias_plot.data_x and self.bias_plot.data_y:
                self.bias_plot.ax.set_xlim(min(self.bias_plot.data_x), max(self.bias_plot.data_x))
                self.bias_plot.ax.set_ylim(min(self.bias_plot.data_y)-1, max(self.bias_plot.data_y)+1)
            
            self.bias_plot.draw()
            
        except Exception as e:
            self.log_message(f"图表更新错误: {str(e)}")

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

    
    def update_frame(self, frame):
        self.original_frame = frame.copy()
        self.current_frame = frame.copy()

        try:
            # 应用正射变换（若启用）
            if hasattr(self, 'bird_eye_transformer') and self.ortho_mode and self.bird_eye_transformer:
                try:
                    frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
                except Exception as e:
                    self.log_message(f"正射变换失败: {e}")

            # 应用裁剪（若启用）
            if self.crop_mode:
                frame = self.apply_crop(frame)

            # 使用CropWidget的方法更新帧
            self.video_label.set_frame(frame)
            
        except Exception as e:
            self.log_message(f"update_frame 出错: {e}")

        QApplication.processEvents()
        # def read_video_frame(self):
    #     """从本地视频文件中读取帧并显示"""
    #     if not self.video_cap:
    #         return
    #     ret, frame = self.video_cap.read()
    #     if not ret:
    #         self.log_message("🎞 视频播放完毕")
    #         self.video_file_timer.stop()
    #         self.video_cap.release()
    #         self.video_cap = None
    #         return
    #     self.update_frame(frame)
    def read_video_frame(self):
        if not self.video_cap:
            return
        ret, frame = self.video_cap.read()
        if not ret:
            self.log_message("🎞 视频播放完毕")
            self.video_file_timer.stop()
            self.video_cap.release()
            self.video_cap = None
            return

        self.original_frame = frame.copy()
        self.current_frame = frame.copy()

        # 处理正射变换
        if hasattr(self, 'bird_eye_transformer') and self.ortho_mode and self.bird_eye_transformer:
            try:
                frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
            except Exception as e:
                self.log_message(f"正射变换失败: {e}")

        # 处理裁剪
        if self.crop_mode:
            frame = self.apply_crop(frame)

        self.video_label.set_frame(frame)
        QApplication.processEvents()


    # def apply_crop(self, frame):
    #     """根据当前 crop slider 裁剪图像"""
    #     h, w = frame.shape[:2]
    #     l = int(self.left_margin_slider.value() / 100 * w)
    #     r = int(self.right_margin_slider.value() / 100 * w)
    #     t = int(self.top_margin_slider.value() / 100 * h)
    #     b = int(self.bottom_margin_slider.value() / 100 * h)
    #     return frame[t:h-b, l:w-r]
    def apply_crop(self, frame):
        """根据当前 crop slider 裁剪图像"""
        h, w = frame.shape[:2]
        
        # 计算裁剪边界
        left = int(self.left_margin_slider.value() / 100 * w)
        right = int(self.right_margin_slider.value() / 100 * w)
        top = int(self.top_margin_slider.value() / 100 * h)
        bottom = int(self.bottom_margin_slider.value() / 100 * h)
        
        # 确保裁剪区域有效
        x1 = max(0, left)
        x2 = min(w, w - right)
        y1 = max(0, top)
        y2 = min(h, h - bottom)
        
        if x1 >= x2 or y1 >= y2:
            self.log_message("⚠️ 裁剪区域无效，显示完整帧")
            return frame
        
        return frame[y1:y2, x1:x2]


def main():
    app = QApplication(sys.argv)
    window = OrthophotoApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
