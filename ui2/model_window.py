# 摄像头模式关闭灰色窗口，仅保留 OpenCV 显示
# import torch
# from ultralytics import YOLO
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QWidget, QButtonGroup
from PyQt5.QtCore import Qt, QTimer
import os
import sys
import cv2

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class ModelParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型选择")
        self.resize(400, 300)
        self.initUI()
        self.setStyleSheet("background-color: #2c3e50;")
        self.setStyleSheet("""
        QDialog {
            background-color: #1E2736;
        }

        QLabel {
            color: #E0E0E0;
            font-size: 15px;
            font-family: 'Microsoft YaHei';
        }

        QPushButton {
            background-color: #2F3E4E;
            color: #E0E0E0;
            border: 2px solid #3F5165;
            padding: 15px;
            font-size: 16px;
            border-radius: 8px;
        }

        QPushButton:hover {
            background-color: #3A4D5E;
            border-color: #607D8B;
        }

        QPushButton:checked {
            background-color: #1E88E5;
            color: #FFFFFF;
            border-color: #1976D2;
        }
    """)

    def initUI(self):
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 标题
        title = QLabel("请选择要使用的模型:")
        title.setAlignment(Qt.AlignCenter)
        # title.setStyleSheet("font-size: 18px; color: #ffffff; margin-bottom: 20px;")
        # title.setStyleSheet("font-size: 18px; color: #ffffff; margin-bottom: 20px;")
        # title.setStyleSheet("font-size: 18px; color: #E0E0E0; margin-bottom: 20px;")
        title.setStyleSheet("font-size: 18px; color: #ffffff; margin-bottom: 20px;")

        main_layout.addWidget(title)

        # 按钮容器
        btn_container = QWidget()
        btn_layout = QVBoxLayout()
        btn_container.setLayout(btn_layout)

        # 创建按钮组
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)

        # YOLO按钮
        self.yolo_btn = QPushButton("YOLO 目标检测模型")
        self.yolo_btn.setCheckable(True)
        self.yolo_btn.setStyleSheet(self.get_button_style())
        self.yolo_btn.toggled.connect(lambda: self.update_selection("YOLO"))

        # UNet按钮
        self.unet_btn = QPushButton("UNet 图像分割模型")
        self.unet_btn.setCheckable(True)
        self.unet_btn.setStyleSheet(self.get_button_style())
        self.unet_btn.toggled.connect(lambda: self.update_selection("UNet"))

        # 将按钮加入组和布局
        self.button_group.addButton(self.yolo_btn)
        self.button_group.addButton(self.unet_btn)
        btn_layout.addWidget(self.yolo_btn)
        btn_layout.addWidget(self.unet_btn)
        btn_layout.setSpacing(15)

        # 状态显示
        self.status_label = QLabel("当前未选择任何模型")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-top: 20px;")

        main_layout.addWidget(btn_container)
        main_layout.addWidget(self.status_label)

    # def get_button_style(self):
    #     return """
    #         QPushButton {
    #             background-color: #ecf0f1;
    #             color: #2c3e50;
    #             border: 2px solid #bdc3c7;
    #             padding: 15px;
    #             font-size: 16px;
    #             border-radius: 8px;
    #         }
    #         QPushButton:hover {
    #             background-color: #dfe6e9;
    #             border-color: #95a5a6;
    #         }
    #         QPushButton:checked {
    #             background-color: #3498db;
    #             color: white;
    #             border-color: #2980b9;
    #         }
    #     """
    def get_button_style(self):
        return """
            QPushButton {
                background-color: #2F3E4E;
                color: #E0E0E0;
                border: 2px solid #3F5165;
                padding: 15px;
                font-size: 16px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #3A4D5E;
                border-color: #607D8B;
            }
            QPushButton:checked {
                background-color: #1E88E5;
                color: #FFFFFF;
                border-color: #1976D2;
            }
        """

    def update_selection(self, model_name):
        if self.sender().isChecked():
            self.selected_model = model_name
            self.status_label.setText(f"已选择模型: {model_name}")
            # self.status_label.setStyleSheet("font-size: 14px; color: #27ae60; margin-top: 20px;")
            # self.status_label.setStyleSheet("font-size: 14px; color: #00ff99; margin-top: 20px;")
            # self.status_label.setStyleSheet("font-size: 14px; color: #ffffff; margin-top: 20px;")

            if model_name == "YOLO":
                self.run_yolo()

    def run_yolo(self):
        model_path = 'D:/crop/system-set/best_yolo11.pt'
        self.status_label.setText("正在加载 YOLO 模型...")

        try:
            self.yolo_model = YOLO(model_path)
            self.status_label.setText("YOLO 模型加载成功，选择输入方式")
            self.select_input_source()
        except Exception as e:
            self.status_label.setText(f"模型加载失败: {str(e)}")
            self.status_label.setStyleSheet("font-size: 14px; color: #e74c3c; margin-top: 20px;")

    def select_input_source(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("选择输入方式")
        msg_box.setText("请选择输入方式：")
        img_button = msg_box.addButton("本地图片", QMessageBox.AcceptRole)
        cam_button = msg_box.addButton("摄像头", QMessageBox.AcceptRole)
        msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.exec_()

        clicked_button = msg_box.clickedButton()
        if clicked_button == img_button:
            self.accept()
            self.process_local_image()
        elif clicked_button == cam_button:
            self.hide()  # 强制隐藏灰色弹窗
            QTimer.singleShot(100, self.process_camera)  # 延迟执行摄像头处理


    def process_local_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            results = self.yolo_model(file_path)
            results.show()

    def process_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return

        window_name = "YOLO 摄像头检测"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = self.yolo_model(frame)
            annotated_frame = results[0].plot()
            cv2.imshow(window_name, annotated_frame)

            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
