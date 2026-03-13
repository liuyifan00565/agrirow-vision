from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import os
from clientside.param import Parameter

class CropParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("作物参数控制中心")
        self.setFixedSize(600, 500)

        self.setStyleSheet("""
            QDialog { background-color: #1E2736; }
            QLabel {
                color: #E0E0E0;
                font-family: 'Microsoft YaHei';
                font-size: 15px;
            }
            QLineEdit, QSpinBox {
                color: white;
                background-color: #2E3B4E;
                border: 1px solid #3F4D63;
                padding: 5px;
                border-radius: 4px;
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
        """)

        self.inrow_param_filepath = os.path.abspath("inrow_param.txt")
        self.interrow_param_filepath = os.path.abspath("interrow_param.txt")

        self.inrow_parameter = Parameter(self.inrow_param_filepath)
        self.interrow_parameter = Parameter(self.interrow_param_filepath)

        self.load_parameters()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("作物参数配置")
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
        self.crop_type_input = QLineEdit(self.get_param_value('crop_type', 'maize'))

        self.interrow_input = QSpinBox()
        self.interrow_input.setRange(100, 1000)
        self.interrow_input.setValue(self.get_safe_int('crop_interrow_distance', '660', source='interrow'))

        self.inrow_input = QSpinBox()
        self.inrow_input.setRange(50, 500)
        self.inrow_input.setValue(self.get_safe_int('crop_inrow_distance', '250'))

        self.height_input = QSpinBox()
        self.height_input.setRange(50, 500)
        self.height_input.setValue(self.get_safe_int('crop_height', '200'))

        self.width_input = QSpinBox()
        self.width_input.setRange(50, 500)
        self.width_input.setValue(self.get_safe_int('crop_width', '100'))

        form_layout.addRow("作物类型", self.crop_type_input)
        form_layout.addRow("作物行间距 (mm)", self.interrow_input)
        form_layout.addRow("作物苗间距 (mm)", self.inrow_input)
        form_layout.addRow("作物高度 (mm)", self.height_input)
        form_layout.addRow("作物展开宽度 (mm)", self.width_input)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("应用参数")
        self.btn_apply.clicked.connect(self.apply_parameters)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_param_value(self, key, default_value):
        try:
            val = self.inrow_parameter.get_param(key)
            return val if val else self.interrow_parameter.get_param(key, default_value)
        except:
            return default_value

    def get_safe_int(self, key, default_value, source='inrow'):
        try:
            param = self.inrow_parameter if source == 'inrow' else self.interrow_parameter
            val = param.get_param(key, default_value)
            return int(val) if str(val).isdigit() else int(default_value)
        except:
            return int(default_value)

    def load_parameters(self):
        inrow_defaults = {
            "crop_type": "maize",
            "crop_inrow_distance": "250",
            "crop_height": "200",
            "crop_width": "100"
        }
        interrow_defaults = {
            "crop_type": "maize",
            "crop_interrow_distance": "660",
            "crop_height": "200",
            "crop_width": "100"
        }

        for handler, defaults in [(self.inrow_parameter, inrow_defaults), (self.interrow_parameter, interrow_defaults)]:
            try:
                if os.path.exists(handler.param_filepath):
                    handler.load()
                else:
                    for k, v in defaults.items():
                        handler.set_param(k, v)
                    handler.save()
            except:
                for k, v in defaults.items():
                    handler.set_param(k, v)
                try:
                    handler.save()
                except:
                    pass

    def apply_parameters(self):
        try:
            for handler in [self.inrow_parameter, self.interrow_parameter]:
                handler.set_param('crop_type', self.crop_type_input.text())
                handler.set_param('crop_height', str(self.height_input.value()))
                handler.set_param('crop_width', str(self.width_input.value()))

            self.inrow_parameter.set_param('crop_inrow_distance', str(self.inrow_input.value()))
            self.interrow_parameter.set_param('crop_interrow_distance', str(self.interrow_input.value()))

            self.inrow_parameter.save()
            self.interrow_parameter.save()

            QMessageBox.information(
                self, "参数应用",
                "参数已成功保存到 inrow_param.txt 和 interrow_param.txt"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"参数保存失败: {str(e)}")
