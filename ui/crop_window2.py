from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from clientside.param import Parameter


class CropParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("作物参数控制中心")
        self.setFixedSize(600, 500)
        self.main_window=parent

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
        QLineEdit, QSpinBox {
            background-color: #2E3B4E;
            color: #FFFFFF;
            border: 1px solid #3F4D63;
            padding: 6px;
            border-radius: 4px;
            font-size: 15px;
            font-family: 'Microsoft YaHei';
        }
    """)

        
        # self.config_path = "crop_config.json"
        # self.params = self.load_config()
        self.init_ui()
        self.fill_param_values()
    
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
        self.crop_type_input = QLineEdit()
        self.interrow_input = QSpinBox()
        self.interrow_input.setRange(0, 1000)
        
        self.inrow_input = QSpinBox()
        self.inrow_input.setRange(0, 500)
        
        self.height_input = QSpinBox()
        self.height_input.setRange(0, 500)
        
        self.width_input = QSpinBox()
        self.width_input.setRange(0, 500)
        
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

    def fill_param_values(self):
        params = self.main_window.clientio.load_params()
        print(int(params.get_param('crop.interrow_distance')))
        print(int(params.get_param('crop.inrow_distance')))
        print(int(params.get_param('crop.height')))
        print(int(params.get_param('crop.width')))
        self.crop_type_input.setText(params.get_param('crop.type'))
        self.interrow_input.setValue(int(params.get_param('crop.interrow_distance')))
        self.inrow_input.setValue(int(params.get_param('crop.inrow_distance')))
        self.height_input.setValue(int(params.get_param('crop.height')))
        self.width_input.setValue(int(params.get_param('crop.width')))
    
    def get_param_values(self):
        new_params = Parameter()
        new_params.set_param('crop.type', self.crop_type_input.text())
        new_params.set_param('crop.interrow_distance', self.interrow_input.value())
        new_params.set_param('crop.inrow_distance', self.inrow_input.value())
        new_params.set_param('crop.height', self.height_input.value())
        new_params.set_param('crop.width', self.width_input.value())
        return new_params

    
    def apply_parameters(self):
        new_params = self.get_param_values()       
        self.main_window.clientio.save_params(new_params) 
        QMessageBox.information(
            self, "参数应用",
            "参数已成功应用:\n"
            f"作物类型: {new_params.get_param('crop.type')}\n"
            f"作物行间距: {new_params.get_param('crop.interrow_distance')}mm\n"
            f"作物苗间距: {new_params.get_param('crop.inrow_distance')}mm\n"
            f"作物高度: {new_params.get_param('crop.height')}mm\n"
            f"作物展开宽度: {new_params.get_param('crop.width')}mm"

        )
    

