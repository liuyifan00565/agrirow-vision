from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import json
import os
from clientside.param import Parameter

class StyledSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal):
        super().__init__(orientation)
        self.setStyleSheet("""
            QSlider {
                min-height: 24px;
            }
            QSlider::groove:horizontal {
                background: #4A5666;
                height: 12px;
                border-radius: 6px;
            }
            QSlider::handle:horizontal {
                background: #1E88E5;
                width: 22px;
                height: 22px;
                border-radius: 11px;
                margin: -5px 0;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            QSlider::handle:horizontal:hover {
                background: #1565C0;
            }
        """)

class OtherParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("其他参数控制中心")
        self.setFixedSize(550, 450)
        self.config_path = os.path.abspath("config/others_config.json")
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
            QComboBox {
                background: #4A5666;
                color: white;
                padding: 8px;
                border-radius: 4px;
                min-width: 100px;
            }
        """)
        
        self.inrow_path = os.path.abspath("inrow_param.txt")
        self.interrow_path = os.path.abspath("interrow_param.txt")
        self.inrow_param = Parameter(self.inrow_path)
        self.interrow_param = Parameter(self.interrow_path)

        try:
            self.inrow_param.load()
        except Exception:
            pass
        try:
            self.interrow_param.load()
        except Exception:
            pass

        self.params = {
            "tractor_velocity": int(self.interrow_param.get_param("tractor_velocity", 5)),
            "parallel_row_count": int(self.interrow_param.get_param("parallel_row_count", 3))
        }
    
        self.init_ui()
        self.add_shadows()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 标题
        title_label = QLabel("其他参数配置")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #FFFFFF; 
            padding-bottom: 15px;
            border-bottom: 3px solid #1E88E5;
            text-align: center;
        """)
        main_layout.addWidget(title_label)

        # 参数区域
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setSpacing(25)

        # 拖拉机速度
        speed_layout, self.slider_speed, self.lbl_speed = self.create_param_control(
            "拖拉机速度 (m/s)", 
            self.params.get('tractor_velocity', 5),
            10
        )
        params_layout.addLayout(speed_layout)

        # 苗行数选择
        row_layout, self.combo_row, self.lbl_row = self.create_combobox_control(
            "覆盖苗行数",
            self.params.get('parallel_row_count', 3),
            ["3", "6", "9", "12", "15"]
        )
        params_layout.addLayout(row_layout)

        main_layout.addWidget(params_widget)

        # 应用按钮
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("应用参数")
        self.btn_apply.clicked.connect(self.apply_parameters)
        btn_layout.addWidget(self.btn_apply)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def create_param_control(self, label_text, initial_value, max_value):
        layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        value_label = QLabel(f"{initial_value}")
        value_label.setStyleSheet("color: #1E88E5; font-weight: bold;")
        
        slider = StyledSlider(Qt.Horizontal)
        slider.setRange(0, max_value)
        slider.setValue(initial_value)
        slider.valueChanged.connect(
            lambda v: self.update_parameter_display("tractor_velocity", v, value_label)
        )
        
        label_layout.addWidget(label)
        label_layout.addStretch()
        label_layout.addWidget(value_label)
        layout.addLayout(label_layout)
        layout.addWidget(slider)
        
        return layout, slider, value_label

    def create_combobox_control(self, label_text, initial_value, options):
        layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        value_label = QLabel(str(initial_value))
        value_label.setStyleSheet("color: #1E88E5; font-weight: bold;")
        
        combo = QComboBox()
        combo.addItems(options)
        combo.setCurrentText(str(initial_value))
        combo.currentTextChanged.connect(
            lambda v: self.update_parameter_display("parallel_row_count", int(v), value_label)
        )
        
        label_layout.addWidget(label)
        label_layout.addStretch()
        label_layout.addWidget(value_label)
        layout.addLayout(label_layout)
        layout.addWidget(combo)
        
        return layout, combo, value_label

    def add_shadows(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

    def update_parameter_display(self, param, value, value_label):
        """只更新显示，不保存参数"""
        self.params[param] = value
        value_label.setText(str(value))

    def apply_parameters(self):
        if not self.main_window:
            QMessageBox.critical(self, "错误", "主窗口未绑定，无法执行参数操作"); return
        
        # 获取当前UI中的参数值
        current_params = {
            "tractor_velocity": self.slider_speed.value(),
            "parallel_row_count": int(self.combo_row.currentText())
        }
        
        try:
            # 保存到文件
            for handler in [self.inrow_param, self.interrow_param]:
                for key, value in current_params.items():
                    handler.set_param(key, value)
                handler.save()
            
            # 更新内部状态
            self.params.update(current_params)
            
            QMessageBox.information(
                self,
                "参数应用",
                f"参数已成功应用:\n"
                f"拖拉机行驶速度: {self.params['tractor_velocity']}m/s\n"
                f"覆盖苗行数: {self.params['parallel_row_count']}行"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"参数保存失败: {str(e)}")

    def load_config(self):
        default_config = {
            "tractor_velocity": 5,
            "parallel_row_count": 3
        }
        try:
            self.config_path = os.path.abspath(self.config_path)

            if not os.path.exists(self.config_path):
                return default_config
            with open(self.config_path, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"配置加载失败: {str(e)}")
            return default_config

    def fill_param_values(self):
        if not self.main_window:
            QMessageBox.critical(self, "错误", "主窗口未绑定，无法加载参数"); return
        params = self.main_window.get_clientio().load_params()
        self.slider_speed.setValue(int(params.get_param('tractor_velocity', 0)))
        self.combo_row.setCurrentText(str(params.get_param('parallel_row_count', '')))

    def get_param_values(self):
        new_params = Parameter()
        new_params.set_param('tractor_velocity', self.slider_speed.value())
        new_params.set_param('parallel_row_count', self.combo_row.currentText())
        return new_params