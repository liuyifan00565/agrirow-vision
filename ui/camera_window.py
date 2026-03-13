from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from clientside.param import Parameter

class CameraParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("摄像头参数配置")
        self.setFixedSize(600, 500)
        self.main_window = parent

        self.setStyleSheet("""
            QDialog {
                background-color: #1E2736;
            }
            QLabel {
                color: #E0E0E0;
                font-family: 'Microsoft YaHei';
                font-size: 15px;
            }
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-family: 'Microsoft YaHei';
                font-size: 15px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2E3A48;
                color: #E0E0E0;
                border: 1px solid #3F51B5;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        
        self.init_ui()
        self.fill_param_values()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("摄像头参数配置")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #FFFFFF; 
            padding-bottom: 15px;
            border-bottom: 3px solid #1E88E5;
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        
        # 使用QDoubleSpinBox替代QSpinBox以支持小数
        self.view_angle_input = QSpinBox()
        self.view_angle_input.setRange(0, 180)
        
        self.camera_height_input = QDoubleSpinBox()
        self.camera_height_input.setRange(0, 10)
        self.camera_height_input.setSingleStep(0.1)
        self.camera_height_input.setDecimals(1)
        
        self.vertical_angle_input = QSpinBox()
        self.vertical_angle_input.setRange(0, 90)
        
        self.row_count_input = QSpinBox()
        self.row_count_input.setRange(1, 10)

        self.view_finger_distance_input = QDoubleSpinBox()
        self.view_finger_distance_input.setRange(0, 5)
        self.view_finger_distance_input.setSingleStep(0.1)
        self.view_finger_distance_input.setDecimals(1)

        form_layout.addRow("摄像头视野开口角度", self.view_angle_input)
        form_layout.addRow("摄像头安装高度（米）", self.camera_height_input)
        form_layout.addRow("摄像头安装倾斜角度", self.vertical_angle_input)
        form_layout.addRow("拍摄苗行数", self.row_count_input)
        form_layout.addRow("画面底部到弹齿距离（米）", self.view_finger_distance_input)
        
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("应用参数")
        self.btn_apply.clicked.connect(self.apply_parameters)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def fill_param_values(self):
        params = self.main_window.clientio.load_params()
        # 安全转换参数，避免空值引发崩溃
        try:
            self.view_angle_input.setValue(int(float(params.get_param('camera.view_angle', 0))))
            self.camera_height_input.setValue(float(params.get_param('camera.height', 0)))
            self.vertical_angle_input.setValue(int(float(params.get_param('camera.vertical_angle', 0))))
            self.row_count_input.setValue(int(float(params.get_param('camera.row_count', 1))))
            self.view_finger_distance_input.setValue(float(params.get_param('camera.view_finger_distance', 0)))
        except Exception as e:
            QMessageBox.critical(self, "参数加载失败", f"读取参数时出错:\n{str(e)}")
        
    def get_param_values(self):
        new_params = Parameter()
        new_params.set_param('camera.view_angle', self.view_angle_input.value())
        new_params.set_param('camera.height', self.camera_height_input.value())
        new_params.set_param('camera.vertical_angle', self.vertical_angle_input.value())
        new_params.set_param('camera.row_count', self.row_count_input.value())
        new_params.set_param('camera.view_finger_distance', self.view_finger_distance_input.value())
        return new_params
    
    def apply_parameters(self):
       
            new_params = self.get_param_values()
            self.main_window.clientio.save_params(new_params) 

            QMessageBox.information(
                self, "参数应用",
                "参数已成功应用:\n"
                f"视角: {new_params.get_param('camera.view_angle')}°\n"
                f"高度: {new_params.get_param('camera.height')}m\n"
                f"倾角: {new_params.get_param('camera.vertical_angle')}°\n"
                f"行数: {new_params.get_param('camera.row_count')}\n"
                f"底部弹齿距离: {new_params.get_param('camera.view_finger_distance')}m"
            )
      