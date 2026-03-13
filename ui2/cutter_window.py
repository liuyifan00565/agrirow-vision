from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
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

class CutterParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("刀具参数控制中心")
        self.setFixedSize(550, 450)
        
        # 参数文件路径
        self.inrow_path = os.path.abspath("inrow_param.txt")
        self.interrow_path = os.path.abspath("interrow_param.txt")
        
        # 创建两个参数实例
        self.inrow_param = Parameter(self.inrow_path)
        self.interrow_param = Parameter(self.interrow_path)
        
        # 尝试加载参数文件
        try:
            self.inrow_param.load()
        except:
            pass
        try:
            self.interrow_param.load()
        except:
            pass
        
        # 深色主题配色
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
        """)
        
        self.init_ui()
        self.fill_param_values()
        self.add_shadows()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 标题
        title_label = QLabel("刀具参数配置")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #FFFFFF; 
            padding-bottom: 15px;
            border-bottom: 3px solid #1E88E5;
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 参数控制区域
        form_layout = QFormLayout()
        
        # 创建滑块控件
        self.slider_reserved_distance = StyledSlider(Qt.Horizontal)
        self.slider_reserved_distance.setRange(0, 100)
        
        self.slider_sibling_distance = StyledSlider(Qt.Horizontal)
        self.slider_sibling_distance.setRange(0, 300)
        
        # 创建显示值的标签
        self.lbl_reserved_value = QLabel()
        self.lbl_reserved_value.setStyleSheet("color: #1E88E5; font-weight: bold;")
        
        self.lbl_sibling_value = QLabel()
        self.lbl_sibling_value.setStyleSheet("color: #1E88E5; font-weight: bold;")
        
        # 添加到表单布局
        form_layout.addRow("安全距离 (mm)", self.slider_reserved_distance)
        form_layout.addRow("当前安全距离:", self.lbl_reserved_value)
        form_layout.addRow("弹齿间距 (mm)", self.slider_sibling_distance)
        form_layout.addRow("当前弹齿间距:", self.lbl_sibling_value)
        
        # 连接滑块值变化信号
        self.slider_reserved_distance.valueChanged.connect(
            lambda v: self.lbl_reserved_value.setText(f"{v}mm")
        )
        self.slider_sibling_distance.valueChanged.connect(
            lambda v: self.lbl_sibling_value.setText(f"{v}mm")
        )
        
        main_layout.addLayout(form_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("应用参数")
        self.btn_apply.clicked.connect(self.apply_parameters)
        btn_layout.addWidget(self.btn_apply)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def add_shadows(self):
        """为窗口添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

    def fill_param_values(self):
        try:
            param = self.inrow_param
            if not param:
                QMessageBox.critical(self, "错误", "无法加载参数文件")
                return
            
            # 设置滑块的值
            reserved_distance = int(param.get_param('reserved_distance', 50))
            sibling_distance = int(param.get_param('sibling_distance', 200))
            
            self.slider_reserved_distance.setValue(reserved_distance)
            self.slider_sibling_distance.setValue(sibling_distance)
            
            # 更新显示标签
            self.lbl_reserved_value.setText(f"{reserved_distance}mm")
            self.lbl_sibling_value.setText(f"{sibling_distance}mm")
        except Exception as e:
            QMessageBox.critical(self, "参数加载错误", f"加载参数失败: {str(e)}")
    
    def get_param_values(self):
        new_params = Parameter()
        new_params.set_param('reserved_distance', self.slider_reserved_distance.value())
        new_params.set_param('sibling_distance', self.slider_sibling_distance.value())
        return new_params
    
    def apply_parameters(self):
        try:
            new_params = self.get_param_values()
            reserved_value = new_params.get_param('reserved_distance')
            sibling_value = new_params.get_param('sibling_distance')
            
            # 保存到两个参数文件
            for handler in [self.inrow_param, self.interrow_param]:
                handler.set_param('reserved_distance', reserved_value)
                handler.set_param('sibling_distance', sibling_value)
                handler.save()

            QMessageBox.information(
                self, "参数应用",
                "参数已成功应用:\n"
                f"弹齿与作物之间的安全距离: {reserved_value}mm\n"
                f"一个刀架上前后两个弹齿的纵向间距: {sibling_value}mm"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存过程中发生异常:\n{str(e)}")