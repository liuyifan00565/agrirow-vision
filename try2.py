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

DEFAULT_CAMERA_WIDTH = 1920  #摄像头拍摄宽度分辨率
DEFAULT_CAMERA_HEIGHT = 1080 #摄像头拍摄高度分辨率

class BirdEyeTransformer:
    def __init__(self, camera_matrix, dist_coeffs, fov_x, fov_y, camera_height, tilt_angle):
        self.K = camera_matrix
        self.dist = dist_coeffs
        self.fov_x = fov_x
        self.fov_y = fov_y
        self.h = camera_height
        self.theta_deg = tilt_angle
        self.pixels_per_meter = 200

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

            theta_rad = math.radians(self.theta_deg)
            R_x = np.array([
                [1, 0, 0],
                [0, math.cos(theta_rad), -math.sin(theta_rad)],
                [0, math.sin(theta_rad), math.cos(theta_rad)]
            ], dtype=np.float32)
            tvec = np.array([[0], [0], [self.h]], dtype=np.float32)
            H = self.K @ np.hstack((R_x[:, :2], tvec))
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

            # # Resize for display缩放取消
            # display_size = (980, 700)
            # resized_img = cv2.resize(bird_eye_img, display_size, interpolation=cv2.INTER_AREA)

            # return resized_img, resized_img.shape[:2][::-1]
            return bird_eye_img, bird_eye_img.shape[:2][::-1]

        except Exception as e:
            print(f"[BirdEyeTransformer] Transformation failed: {e}")
            return None, None

class VideoThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.cap = None
        self.running = False
        self.source = None
        self.frame_rate = 20

    def start_capture(self, source, backend=cv2.CAP_ANY):
        print(f"[VideoThread] Opening source: {source} with backend: {backend}")
        try:
            self.cap = cv2.VideoCapture(source, backend)
            if not self.cap.isOpened():
                print(f"[VideoThread] ❌ Failed to open source")
                return False
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_CAMERA_HEIGHT)
            # 获取实际分辨率
            real_frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            real_frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"🎥 录制分辨率: {real_frame_width}x{real_frame_height}")

            self.running = True
            self.start()  # 启动线程
            return True
        except Exception as e:
            print(f"[VideoThread] Error: {e}")
            return False
    def stop_capture(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.wait()  # 等待线程结束

    def run(self):
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue
            self.frame_ready.emit(frame)  # 发射帧数据
            self.msleep(int(1000 / self.frame_rate))

class CropWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet("border: 1px solid gray;")
        self.setScaledContents(True)
        # self.setScaledContents(False)  # 关闭缩放
        # self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)  # 允许内容尺寸决定自身

        self.crop_rect = None
        self.dragging = False
        self.drag_start = None
        self.current_frame = None
        self.show_crop_rect = False

    def set_frame(self, frame):
        self.current_frame = frame.copy()
        self.update_display()

    def set_crop_rect(self, rect):
        self.crop_rect = rect
        if self.show_crop_rect:
            self.update_display()

    def set_show_crop_rect(self, show):
        self.show_crop_rect = show
        self.update_display()

    def update_display(self):
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()

        if self.show_crop_rect and self.crop_rect:
            x, y, w, h = self.crop_rect
            x = max(0, min(x, frame.shape[1]-1))
            y = max(0, min(y, frame.shape[0]-1))
            w = max(1, min(w, frame.shape[1]-x))
            h = max(1, min(h, frame.shape[0]-y))
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.setPixmap(QPixmap.fromImage(q_image))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.show_crop_rect:
            self.dragging = True
            self.drag_start = (event.x(), event.y())
            # Initialize crop rect if it doesn't exist
            if self.crop_rect is None:
                self.crop_rect = (event.x(), event.y(), 1, 1)

    def mouseMoveEvent(self, event):
        if self.dragging and self.drag_start and self.show_crop_rect:
            start_x, start_y = self.drag_start
            end_x, end_y = event.x(), event.y()
            
            # Calculate coordinates relative to the displayed image
            pixmap = self.pixmap()
            if pixmap is None:
                return
                
            # Get the actual displayed image size (may be scaled)
            disp_w = pixmap.width()
            disp_h = pixmap.height()
            
            # Get the original frame dimensions
            if self.current_frame is None:
                return
            img_w = self.current_frame.shape[1]
            img_h = self.current_frame.shape[0]
            
            # Calculate scaling factors
            scale_x = img_w / disp_w
            scale_y = img_h / disp_h
            
            # Convert mouse coordinates to image coordinates
            x = min(start_x, end_x) * scale_x
            y = min(start_y, end_y) * scale_y
            w = abs(end_x - start_x) * scale_x
            h = abs(end_y - start_y) * scale_y
            
            # Update crop rectangle
            self.crop_rect = (int(x), int(y), int(w), int(h))
            self.update_display()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
class OrthophotoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orthophoto Imaging Software")
        self.setGeometry(50, 50, 1000, 800)

        # Video thread
        self.video_thread = VideoThread()
        # self.video_thread.frame_ready.connect(self.update_frame)

        # Current frame and parameters
        self.current_frame = None
        self.original_frame = None  # 保存原始帧用于录制
        self.camera_height = 130.0  # cm
        self.tilt_angle = 49  # degrees (positive up)
        self.recording = False
        self.video_writer = None
        self.video_output_path = ""
        # 定时处理显示队列
        self.display_queue = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_display_queue)
        self.timer.start(33)  # 每 33ms 处理一次，约 30 FPS


        # Camera intrinsics
        # Camera intrinsics
        self.camera_matrix = np.array([[1.36074827e+03, 0.00000000e+00, 9.65363696e+02], 
                                       [0.00000000e+00, 1.35918014e+03, 5.86850945e+02], 
                                       [0,0,1]], dtype=np.float32)
        self.dist_coeffs = np.array([0.00780561,  0.00221039, -0.00031791,  0.00078508, -0.03267454], dtype=np.float32)
        self.fov_x = 65  # degrees
        self.fov_y = 46  # degrees

        self.video_source = 'camera'
        self.bird_eye_transformer = None
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # Left video display area
        left_layout = QVBoxLayout()

        # Video source selection
        source_layout = QHBoxLayout()
        source_label = QLabel("视频源")
        source_label.setStyleSheet("color: black; font-weight: bold;")
        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件"])
        self.source_combo.setFixedWidth(150)
        self.source_combo.currentIndexChanged.connect(self.change_video_source)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        source_layout.addStretch()
        left_layout.addLayout(source_layout)

        # Video display label
        self.video_label = CropWidget()
        # self.video_label.setFixedSize(980, 700)

        self.video_label.setText("视频显示区域")
        self.video_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.video_label)

        # Bottom parameter input area
        params_layout = QHBoxLayout()
        params_layout.setContentsMargins(0, 10, 0, 0)

        # Camera height
        params_layout.addWidget(QLabel("相机高度（厘米）"))
        self.height_input = QLineEdit("130")
        self.height_input.setFixedWidth(60)
        params_layout.addWidget(self.height_input)

        # Camera tilt angle
        params_layout.addWidget(QLabel("俯仰角（度，正为上）"))
        self.tilt_input = QLineEdit("49")
        self.tilt_input.setFixedWidth(60)
        self.tilt_input.returnPressed.connect(self.update_pitch_angle)
        params_layout.addWidget(self.tilt_input)

        # Horizontal FOV
        params_layout.addWidget(QLabel("水平视场角（度）"))
        self.fov_x_input = QLineEdit("65")
        self.fov_x_input.setFixedWidth(40)
        params_layout.addWidget(self.fov_x_input)

        # Vertical FOV
        params_layout.addWidget(QLabel("垂直视场角（度）"))
        self.fov_y_input = QLineEdit("46")
        self.fov_y_input.setFixedWidth(40)
        params_layout.addWidget(self.fov_y_input)

        # Save path selection
        path_layout = QHBoxLayout()
        path_label = QLabel("保存路径")
        path_label.setStyleSheet("color: black; font-weight: bold;")
        self.path_input = QLineEdit()
        self.path_input.setMinimumWidth(150)
        self.path_input.setReadOnly(True)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(60)
        self.browse_btn.clicked.connect(self.browse_save_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        params_layout.addLayout(path_layout)

        left_layout.addLayout(params_layout)
        main_layout.addLayout(left_layout)

        # Right control panel
        right_widget = QWidget()
        right_widget.setFixedWidth(280)
        right_widget.setStyleSheet("background-color: #f8f8f8;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(10)

        # Video control buttons section
        video_control_group = QGroupBox("视频控制")
        video_control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: white;
            }
        """)
        video_control_layout = QVBoxLayout(video_control_group)
        video_control_layout.setSpacing(8)

        # Button style
        btn_style = """
            QPushButton {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                min-width: 120px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """

        self.start_btn = QPushButton("原始视频")
        self.start_btn.setStyleSheet(btn_style)
        self.start_btn.clicked.connect(self.start_video)
        video_control_layout.addWidget(self.start_btn)

        self.ortho_btn = QPushButton("正射变换视频")
        self.ortho_btn.setStyleSheet(btn_style)
        self.ortho_btn.clicked.connect(self.orthophoto_transform)
        self.ortho_btn.setEnabled(False)
        video_control_layout.addWidget(self.ortho_btn)

        self.crop_btn = QPushButton("裁剪视频")
        self.crop_btn.setStyleSheet(btn_style)
        self.crop_btn.clicked.connect(self.toggle_crop_view)
        self.crop_btn.setEnabled(False)
        video_control_layout.addWidget(self.crop_btn)

        right_layout.addWidget(video_control_group)

        # Save control buttons section
        save_control_group = QGroupBox("保存控制")
        save_control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: white;
            }
        """)
        save_control_layout = QVBoxLayout(save_control_group)
        save_control_layout.setSpacing(8)

        self.save_original_video_btn = QPushButton("保存原视频")
        self.save_original_video_btn.setStyleSheet(btn_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_original_video_btn.clicked.connect(self.save_original_video)
        self.save_original_video_btn.setEnabled(False)
        save_control_layout.addWidget(self.save_original_video_btn)

        self.save_btn = QPushButton("保存当前帧")
        self.save_btn.setStyleSheet(btn_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_btn.clicked.connect(self.save_action)
        save_control_layout.addWidget(self.save_btn)

        right_layout.addWidget(save_control_group)

        # Crop tools section
        crop_tools_group = QGroupBox("裁剪工具")
        crop_tools_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: white;
            }
        """)
        crop_tools_layout = QVBoxLayout(crop_tools_group)
        crop_tools_layout.setSpacing(8)

        self.default_crop_btn = QPushButton("默认裁剪")
        self.default_crop_btn.setStyleSheet(btn_style)
        self.default_crop_btn.clicked.connect(self.set_default_crop)
        crop_tools_layout.addWidget(self.default_crop_btn)

        right_layout.addWidget(crop_tools_group)

        # Crop settings group
        crop_group = QGroupBox("裁剪设置")
        crop_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: white;
            }
        """)
        crop_layout = QVBoxLayout(crop_group)
        crop_layout.setSpacing(15)

        # Left margin slider
        left_layout_container = QVBoxLayout()
        left_label = QLabel("左边距")
        left_label.setAlignment(Qt.AlignCenter)
        left_layout_container.addWidget(left_label)

        left_slider_container = QHBoxLayout()
        left_slider_container.addWidget(QLabel("0"))
        self.left_margin_slider = QSlider(Qt.Horizontal)
        self.left_margin_slider.setRange(0, 100)
        self.left_margin_slider.setValue(10)
        self.left_margin_slider.valueChanged.connect(self.update_crop_from_sliders)
        left_slider_container.addWidget(self.left_margin_slider)
        self.left_value_label = QLabel("10")
        self.left_value_label.setFixedWidth(25)
        left_slider_container.addWidget(self.left_value_label)
        left_layout_container.addLayout(left_slider_container)
        crop_layout.addLayout(left_layout_container)

        # Right margin slider
        right_layout_container = QVBoxLayout()
        right_label = QLabel("右边距")
        right_label.setAlignment(Qt.AlignCenter)
        right_layout_container.addWidget(right_label)

        right_slider_container = QHBoxLayout()
        right_slider_container.addWidget(QLabel("0"))
        self.right_margin_slider = QSlider(Qt.Horizontal)
        self.right_margin_slider.setRange(0, 100)
        self.right_margin_slider.setValue(10)
        self.right_margin_slider.valueChanged.connect(self.update_crop_from_sliders)
        right_slider_container.addWidget(self.right_margin_slider)
        self.right_value_label = QLabel("10")
        self.right_value_label.setFixedWidth(25)
        right_slider_container.addWidget(self.right_value_label)
        right_layout_container.addLayout(right_slider_container)
        crop_layout.addLayout(right_layout_container)

        # Vertical margins layout
        vertical_margins_layout = QHBoxLayout()

        # Top margin slider
        top_layout_container = QVBoxLayout()
        top_label = QLabel("上边距")
        top_label.setAlignment(Qt.AlignCenter)
        top_layout_container.addWidget(top_label)

        top_slider_container = QVBoxLayout()
        self.top_margin_slider = QSlider(Qt.Vertical)
        self.top_margin_slider.setRange(0, 100)
        self.top_margin_slider.setValue(10)
        self.top_margin_slider.setFixedHeight(120)
        self.top_margin_slider.valueChanged.connect(self.update_crop_from_sliders)
        top_slider_container.addWidget(self.top_margin_slider, alignment=Qt.AlignHCenter)
        self.top_value_label = QLabel("10")
        self.top_value_label.setAlignment(Qt.AlignCenter)
        top_slider_container.addWidget(self.top_value_label)
        top_layout_container.addLayout(top_slider_container)
        vertical_margins_layout.addLayout(top_layout_container)

        # Bottom margin slider
        bottom_layout_container = QVBoxLayout()
        bottom_label = QLabel("下边距")
        bottom_label.setAlignment(Qt.AlignCenter)
        bottom_layout_container.addWidget(bottom_label)

        bottom_slider_container = QVBoxLayout()
        self.bottom_margin_slider = QSlider(Qt.Vertical)
        self.bottom_margin_slider.setRange(0, 100)
        self.bottom_margin_slider.setValue(10)
        self.bottom_margin_slider.setFixedHeight(120)
        self.bottom_margin_slider.valueChanged.connect(self.update_crop_from_sliders)
        bottom_slider_container.addWidget(self.bottom_margin_slider, alignment=Qt.AlignHCenter)
        self.bottom_value_label = QLabel("10")
        self.bottom_value_label.setAlignment(Qt.AlignCenter)
        bottom_slider_container.addWidget(self.bottom_value_label)
        bottom_layout_container.addLayout(bottom_slider_container)
        vertical_margins_layout.addLayout(bottom_layout_container)

        crop_layout.addLayout(vertical_margins_layout)
        right_layout.addWidget(crop_group)

        # Add stretch to push everything to the top
        right_layout.addStretch()

        main_layout.addWidget(right_widget)

        # State variables
        self.ortho_mode = False
        self.crop_mode = False

        # Connect slider value changes to label updates
        self.left_margin_slider.valueChanged.connect(lambda v: self.left_value_label.setText(str(v)))
        self.right_margin_slider.valueChanged.connect(lambda v: self.right_value_label.setText(str(v)))
        self.top_margin_slider.valueChanged.connect(lambda v: self.top_value_label.setText(str(v)))
        self.bottom_margin_slider.valueChanged.connect(lambda v: self.bottom_value_label.setText(str(v)))
        self.load_crop_settings()

    def browse_save_path(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            os.path.expanduser("~"),
            options=options
        )
        
        if save_dir:
            self.path_input.setText(save_dir)

    def save_original_video(self):
        """保存当前的原始视频流到文件"""
        if self.original_frame is None:
            QMessageBox.warning(self, "错误", "没有视频流可保存")
            return

        save_dir = self.path_input.text()
        if not save_dir:
            QMessageBox.warning(self, "错误", "请先选择保存路径")
            return
        
        if not os.path.isdir(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建保存目录:\n{str(e)}")
                return

        # 检查是否已经在录制
        if self.recording:
            # 停止录制
            self.stop_recording()
            self.save_original_video_btn.setText("保存原视频")
            QMessageBox.information(self, "成功", f"视频录制已停止并保存到:\n{self.video_output_path}")
        else:
            # 开始录制
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"original_video_{timestamp}.mp4"
            video_path = os.path.join(save_dir, video_filename)
            
            if self.start_recording(video_path):
                self.save_original_video_btn.setText("停止录制")
                QMessageBox.information(self, "开始录制", f"开始录制原视频到:\n{video_path}")
            else:
                QMessageBox.critical(self, "错误", "无法开始录制视频")

    # === 修复版 start_recording 用于同步保存路径 ===


    def start_recording(self, output_path):
        """开始录制视频（原始视频 + 正射裁剪帧）"""
        if self.original_frame is None:
            return False

        try:
            height, width = self.original_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30.0
            self.video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not self.video_writer.isOpened():
                print("Failed to open video writer")
                return False

            self.recording = True
            self.video_output_path = output_path

            # 使用保存视频的同一个目录来保存 transformed_frames
            base_dir = os.path.dirname(output_path)
            self.transformed_frame_index = 0
            self.save_transformed_frames = True
            self.transformed_frame_dir = os.path.join(base_dir, "transformed_frames")
            os.makedirs(self.transformed_frame_dir, exist_ok=True)

            print(f"开始录制视频: {output_path}")
            print(f"裁剪图像帧保存至: {self.transformed_frame_dir}")
            return True

        except Exception as e:
            print(f"Error starting recording: {e}")
            return False


    def stop_recording(self):
        """停止录制视频（包括原始视频和正射裁剪帧）"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.recording = False

        # ===停止正射帧保存标志 ===
        self.save_transformed_frames = False

        # # ===选：清除帧保存路径或计数器（如果你在其他函数中会用到）===
        # self.transformed_frame_index = 0
        # self.transformed_frame_dir = ""

        print("停止录制视频，并停止保存正射裁剪帧")


    def write_frame_to_video(self, frame):
        """将帧写入视频文件"""
        if self.recording and self.video_writer and frame is not None:
            try:
                self.video_writer.write(frame)
            except Exception as e:
                print(f"Error writing frame to video: {e}")

    def save_frame(self):
        if self.current_frame is None:
            QMessageBox.warning(self, "警告", "没有图像可保存。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)"
        )
        if file_path:
            frame = self.current_frame.copy()
            if self.ortho_mode:
                try:
                    target_size = (self.video_label.width(), self.video_label.height())
                    frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame, target_size=target_size)
                except Exception as e:
                    print("Orthophoto transformation failed:", e)
                    return
            success = cv2.imwrite(file_path, frame)
            if success:
                QMessageBox.information(self, "成功", f"Image saved to: {file_path}")
            else:
                QMessageBox.critical(self, "错误", "保存失败！")

    def display_image(self, image):
        if image is None or not hasattr(image, "shape"):
            return

        # Convert to RGB format
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image

        img_h, img_w = rgb_image.shape[:2]

        # 不进行 resize，直接显示原始大小图像
        qimg = QImage(
            rgb_image.data,
            img_w, img_h,
            3 * img_w,
            QImage.Format_RGB888
        )

        self.video_label.setPixmap(QPixmap.fromImage(qimg))
        self.video_label.set_frame(image)  # 保留原图用于后续裁剪
        
        if self.crop_mode:
            self.video_label.update_display()

    def save_crop_settings(self):
        settings = {
            "left": self.left_margin_slider.value(),
            "right": self.right_margin_slider.value(),
            "top": self.top_margin_slider.value(),
            "bottom": self.bottom_margin_slider.value()
        }
        with open("crop_settings.json", "w") as f:
            json.dump(settings, f)

    def load_crop_settings(self):
        if not os.path.exists("crop_settings.json"):
            return
        try:
            with open("crop_settings.json", "r") as f:
                settings = json.load(f)
            self.left_margin_slider.setValue(settings.get("left", 10))
            self.right_margin_slider.setValue(settings.get("right", 10))
            self.top_margin_slider.setValue(settings.get("top", 10))
            self.bottom_margin_slider.setValue(settings.get("bottom", 10))
        except Exception as e:
            print("Failed to load crop settings:", e)

    def update_pitch_angle(self):
        try:
            new_angle = float(self.tilt_input.text())
            self.tilt_angle = new_angle
            self.update_transformer_from_inputs()

            if self.current_frame is not None:
                bird_eye_img, _ = self.bird_eye_transformer.get_bird_eye_view(self.current_frame)
                if bird_eye_img is not None:
                    self.display_image(bird_eye_img)
                else:
                    QMessageBox.warning(self, "Image Processing Failed", "Orthophoto transformation failed.")
        except ValueError:
            QMessageBox.warning(self, "输入无效", "请输入有效的俯仰角数值。")

    def change_video_source(self, index):
        if index == 0:
            self.video_source = "camera"
            self.stop_video()
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)")
            if file_path:
                self.video_source = file_path
                self.stop_video()
                self.start_video()
            else:
                self.source_combo.setCurrentIndex(0)
                self.video_source = "camera"

    def set_default_crop(self):
        self.left_margin_slider.setValue(10)
        self.right_margin_slider.setValue(10)
        self.top_margin_slider.setValue(10)
        self.bottom_margin_slider.setValue(10)
        self.video_label.set_show_crop_rect(True)
        self.update_crop_from_sliders()

   
    def start_video(self):
        self.stop_video()  # 先停止现有线程
    # 确保连接信号槽（取消注释）
        self.video_thread.frame_ready.connect(self.update_frame)
        if self.video_source == "camera":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            for backend in backends:
                print(f"[App] Trying backend: {backend}")
                if self.video_thread.start_capture(0, backend):
                    break
            else:
                QMessageBox.critical(self, "错误", "无法打开摄像头")
                return
        else:
            if not self.video_thread.start_capture(self.video_source):
                QMessageBox.critical(self, "错误", "无法打开视频文件")
                return

        # 更新UI状态
        self.start_btn.setText("停止视频")
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.stop_video)
        self.ortho_btn.setEnabled(True)
        self.crop_btn.setEnabled(True)
        self.save_original_video_btn.setEnabled(True)

    def process_display_queue(self):
        if not self.display_queue:
            return

        try:
            frame = self.display_queue.pop(0)

            # Orthophoto transform
            if self.ortho_mode and self.bird_eye_transformer:
                try:
                    display_frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
                    if display_frame is None:
                        display_frame = frame
                except Exception as e:
                    print(f"[Ortho] Failed: {e}")
                    display_frame = frame
            else:
                display_frame = frame

            # Set the frame in the video label first
            self.video_label.set_frame(display_frame)

            # Store current crop rect visibility
            crop_visible = self.video_label.show_crop_rect

            # Crop processing
            if self.crop_mode and self.video_label.crop_rect:
                try:
                    self.video_label.set_show_crop_rect(False)  # 👈 临时关闭绿色裁剪框

                    img_h, img_w = display_frame.shape[:2]
                    left = int(self.left_margin_slider.value() / 100 * img_w)
                    right = int(self.right_margin_slider.value() / 100 * img_w)
                    top = int(self.top_margin_slider.value() / 100 * img_h)
                    bottom = int(self.bottom_margin_slider.value() / 100 * img_h)

                    x1 = left
                    x2 = img_w - right
                    y1 = top
                    y2 = img_h - bottom

                    x1, x2 = max(0, x1), min(img_w, x2)
                    y1, y2 = max(0, y1), min(img_h, y2)
                    display_frame = display_frame[y1:y2, x1:x2]
                except Exception as e:
                    print(f"[Crop] Failed: {e}")

            # 最终显示（无绿色框）
            self.display_image(display_frame)

        except Exception as e:
            print(f"[DisplayQueue] Error: {e}")

    # def orthophoto_transform(self):
    #     if self.current_frame is None:
    #         QMessageBox.warning(self, "警告", "无可供变换的视频帧")
    #         return

    #     try:
    #         # Get user input parameters
    #         tilt = float(self.tilt_input.text())
    #         fov_x = float(self.fov_x_input.text())
    #         fov_y = float(self.fov_y_input.text())
    #         height = float(self.height_input.text())

    #         # Create new transformer object
    #         self.bird_eye_transformer = BirdEyeTransformer(
    #             camera_matrix=self.camera_matrix,
    #             dist_coeffs=self.dist_coeffs,
    #             fov_x=fov_x,
    #             fov_y=fov_y,
    #             camera_height=height / 100,  # Convert to meters
    #             tilt_angle=tilt
    #         )

    #         # Apply transformation
    #         transformed, _ = self.bird_eye_transformer.get_bird_eye_view(self.current_frame)
    #         if transformed is not None:
    #             self.display_image(transformed)
    #             self.ortho_mode = True
    #             self.ortho_btn.setText("停止正射")
    #         else:
    #             QMessageBox.warning(self, "失败", "正射变换失败，请检查参数")

    #     except Exception as e:
    #         QMessageBox.critical(self, "错误", f"Orthophoto transformation error: {e}")
    def orthophoto_transform(self):
        if self.ortho_mode:  # If already in ortho mode, stop it
            self.ortho_mode = False
            self.ortho_btn.setText("正射变换视频")
            if self.current_frame is not None:
                self.display_image(self.current_frame)
            return

        if self.current_frame is None:
            QMessageBox.warning(self, "警告", "无可供变换的视频帧")
            return

        try:
            # Get user input parameters
            tilt = float(self.tilt_input.text())
            fov_x = float(self.fov_x_input.text())
            fov_y = float(self.fov_y_input.text())
            height = float(self.height_input.text())

            # Create new transformer object
            self.bird_eye_transformer = BirdEyeTransformer(
                camera_matrix=self.camera_matrix,
                dist_coeffs=self.dist_coeffs,
                fov_x=fov_x,
                fov_y=fov_y,
                camera_height=height / 100,  # Convert to meters
                tilt_angle=tilt
            )

            # Apply transformation
            transformed, _ = self.bird_eye_transformer.get_bird_eye_view(self.current_frame)
            if transformed is not None:
                self.display_image(transformed)
                self.ortho_mode = True
                self.ortho_btn.setText("停止正射")
            else:
                QMessageBox.warning(self, "失败", "正射变换失败，请检查参数")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"Orthophoto transformation error: {e}")

    def stop_video(self):
        if self.video_thread:
            print("[App] Stopping video thread")
            self.video_thread.stop_capture()
            self.video_thread.wait()
        self.start_btn.setText("原始视频")
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.start_video)
        self.ortho_btn.setEnabled(False)
        self.crop_btn.setEnabled(False)


    def toggle_crop_view(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            self.crop_btn.setText("停止裁剪")
            self.video_label.set_show_crop_rect(True)
            self.update_crop_from_sliders()
        else:
            self.crop_btn.setText("裁剪视频")
            self.video_label.set_show_crop_rect(False)
            if self.current_frame is not None:
                self.display_image(self.current_frame)



    def update_transformer_from_inputs(self):
        try:
            fov_x = float(self.fov_x_input.text())
            fov_y = float(self.fov_y_input.text())
            height = float(self.height_input.text())
            tilt = float(self.tilt_input.text())

            self.tilt_angle = tilt
            self.fov_x = fov_x
            self.fov_y = fov_y
            self.camera_height = height

            h_m = height / 100  # Convert to meters
            self.bird_eye_transformer = BirdEyeTransformer(
                camera_matrix=self.camera_matrix,
                dist_coeffs=self.dist_coeffs,
                fov_x=fov_x,
                fov_y=fov_y,
                camera_height=h_m,
                tilt_angle=tilt
            )
        except Exception as e:
            print(f"[Transformer Update Failed] {e}")

    def save_action(self):
        if self.current_frame is None:
            QMessageBox.warning(self, "错误", "没有帧可保存")
            return

        save_dir = self.path_input.text()
        if not save_dir:
            QMessageBox.warning(self, "错误", "请先选择保存路径")
            return
        if not os.path.isdir(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"Cannot create save directory:\n{str(e)}")
                return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"screenshot_{timestamp}.jpg")

        cv2.imwrite(save_path, self.current_frame)
        QMessageBox.information(self, "成功", f"Screenshot saved to:\n{save_path}")
    # def update_frame(self, frame):
    #     if frame is None or frame.size == 0:
    #         return

    #     try:
    #         self.current_frame = frame.copy()
    #         self.original_frame = frame.copy()
            
    #         # Write to video if recording
    #         if self.recording and self.video_writer:
    #             self.video_writer.write(self.original_frame)

    #         display_frame = None
            
    #         # Apply orthophoto transformation if enabled
    #         if self.ortho_mode and self.bird_eye_transformer:
    #             try:
    #                 transformed, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
    #                 if transformed is not None:
    #                     display_frame = transformed
                        
    #                     # Save transformed frames if recording
    #                     if self.recording and self.save_transformed_frames:
    #                         filename = os.path.join(
    #                             self.transformed_frame_dir, 
    #                             f"frame_{self.transformed_frame_index:04d}.jpg"
    #                         )
    #                         cv2.imwrite(filename, transformed)
    #                         self.transformed_frame_index += 1
    #             except Exception as e:
    #                 print(f"Orthophoto transformation failed: {e}")
    #                 display_frame = frame.copy()
    #         else:
    #             display_frame = frame.copy()

    #         # Apply crop if enabled
    #         if self.crop_mode and hasattr(self.video_label, 'crop_rect') and self.video_label.crop_rect:
    #             try:
    #                 left_pct = self.left_margin_slider.value() / 100.0
    #                 right_pct = self.right_margin_slider.value() / 100.0
    #                 top_pct = self.top_margin_slider.value() / 100.0
    #                 bottom_pct = self.bottom_margin_slider.value() / 100.0

    #                 img_h, img_w = display_frame.shape[:2]
    #                 x = int(img_w * left_pct)
    #                 y = int(img_h * top_pct)
    #                 w = int(img_w * (1 - left_pct - right_pct))
    #                 h = int(img_h * (1 - top_pct - bottom_pct))

    #                 x = max(0, min(x, img_w - 1))
    #                 y = max(0, min(y, img_h - 1))
    #                 w = max(1, min(w, img_w - x))
    #                 h = max(1, min(h, img_h - y))

    #                 display_frame = display_frame[y:y+h, x:x+w]
    #                 self.video_label.set_show_crop_rect(False)
    #             except Exception as e:
    #                 print(f"Crop failed: {e}")

    #         # Display the frame
    #         if display_frame is not None:
    #             # Convert to RGB format first
    #             display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                
    #             label_w = self.video_label.width()
    #             label_h = self.video_label.height()
    #             img_h, img_w = display_frame.shape[:2]
                
    #             scale = min(label_w / img_w, label_h / img_h)
    #             new_w = int(img_w * scale)
    #             new_h = int(img_h * scale)
                
    #             resized = cv2.resize(display_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
    #             background = np.zeros((label_h, label_w, 3), dtype=np.uint8)
    #             x_offset = (label_w - new_w) // 2
    #             y_offset = (label_h - new_h) // 2
    #             background[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
                
    #             # Create QImage and set it to the label
    #             qimg = QImage(background.data, label_w, label_h, 3 * label_w, QImage.Format_RGB888)
    #             self.video_label.setPixmap(QPixmap.fromImage(qimg))
    #             self.video_label.set_frame(background)  # Update the current frame in CropWidget

    #     except Exception as e:
    #         print(f"Error processing frame: {e}")
    def update_frame(self, frame):
        if frame is None or frame.size == 0:
            return

        try:
            self.original_frame = frame.copy()
            self.current_frame = frame.copy()

            if self.recording and self.video_writer:
                self.video_writer.write(self.original_frame)
            self.display_queue.append(frame.copy())  # 用于 process_display_queue
            self.process_display_queue()  # 立即刷新画面
            # 加入显示队列（最多保留3帧，避免内存暴涨）
            if len(self.display_queue) < 3:
                self.display_queue.append(frame.copy())

        except Exception as e:
            print(f"[update_frame] Error: {e}")

        try:
            if frame is None or not hasattr(frame, 'shape') or frame.size == 0:
                print("[Frame] 跳过空帧")
                return

            self.original_frame = frame.copy()
            self.current_frame = frame.copy()

            if self.recording and self.video_writer:
                self.video_writer.write(self.original_frame)

            if len(self.display_queue) < 3:
                self.display_queue.append(frame.copy())
        except Exception as e:
            print(f"[update_frame] 捕获异常: {e}")

    def update_crop_from_sliders(self):
        if self.current_frame is None:
            return

        try:
            frame = self.current_frame.copy()
            if self.ortho_mode and self.bird_eye_transformer:
                frame, _ = self.bird_eye_transformer.get_bird_eye_view(frame)
                if frame is None:
                    return
        except Exception as e:
            print("Temporary orthophoto transformation failed:", e)
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

        if w > 0 and h > 0:
            self.video_label.set_crop_rect((x, y, w, h))
            self.video_label.set_show_crop_rect(True)
            self.video_label.update_display()  # Force update the display
        self.save_crop_settings()
def main():
    app = QApplication(sys.argv)
    window = OrthophotoApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    cv2.ocl.setUseOpenCL(False)
    cv2.setUseOptimized(False)
    print("[App] OpenCV GPU acceleration disabled.")
    main()

