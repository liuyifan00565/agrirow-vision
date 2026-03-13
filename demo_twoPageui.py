import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.Ui_parameter import Ui_Form  # 导入参数设置窗口
from ui.cutter_window import CutterParameterWindow  # 导入刀具参数窗口
from ui.crop_window2 import CropParameterWindow  # 导入作物参数窗口
from ui.DemoBoard_window import DemoBoardParameterWindow  # 导入开发板参数调整窗口
from ui.others_window import OtherParameterWindow  # 导入其他参数设置窗口
from ui.model_window import ModelParameterWindow  # 导入模型参数窗口
from ui.camera_window import CameraParameterWindow #导入摄像头参数窗口
from PyQt5.QtCore import Qt
from clientside.client_io import IOClient
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from clientside.param import Parameter

class MainWindow(QMainWindow, Ui_Form):
    def __init__(self, parent=None,
                 server_ip='192.168.137.100',
                 video_port=8090,
                 instruction_port=8091,
                 system_type='interrow_weeder'
                 ):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("除草机控制系统")
        self.setFixedSize(1000, 800)
        
        self.clientio = IOClient(server_ip, video_port, instruction_port, system_type)
        # 连接按钮信号
        self.cutter_parameter.clicked.connect(self.open_cutter_window)
        self.Crop_parameter.clicked.connect(self.open_crop_window)
        self.DemoBoard_parameter.clicked.connect(self.open_DemoBoard_window)
        self.closeBtn.clicked.connect(self.close_window)
        self.Other_parameter.clicked.connect(self.open_others_window)
        self.modelBtn.clicked.connect(self.open_model_window)
        self.Camera_parameter.clicked.connect(self.open_camera_window)

        # 存储子窗口引用
        self.cutter_window = None
        self.crop_window = None
        self.model_window = None
        self.DemoBoard_window = None
        self.others_window = None 
        self.camera_window = None

    def get_clientio(self):
        """获取IOClient实例"""
        return self.clientio
    
    def close_window(self):
        """关闭主窗口"""
        self.close()

    def open_cutter_window(self):
        """打开刀具参数窗口"""
        if not self.cutter_window:  # 避免重复创建
            self.cutter_window = CutterParameterWindow(self)
            self.cutter_window.setWindowModality(Qt.NonModal)  # 非模态窗口
        self.cutter_window.show()

    def open_crop_window(self):
        """打开作物参数窗口"""
        if not self.crop_window:  # 避免重复创建
            self.crop_window = CropParameterWindow(self)
            self.crop_window.setWindowModality(Qt.NonModal)  # 非模态窗口
        self.crop_window.show()
    def open_DemoBoard_window(self):
        """打开开发板参数窗口"""
        if not self.DemoBoard_window:  # 避免重复创建
            self.DemoBoard_window = DemoBoardParameterWindow(self)
            self.DemoBoard_window.setWindowModality(Qt.NonModal)  # 非模态窗口
        self.DemoBoard_window.show()
    def open_others_window(self):
        """打开其他参数窗口"""
        if not self.others_window:  # 避免重复创建
            self.others_window = OtherParameterWindow(self)
            self.others_window.setWindowModality(Qt.NonModal)  # 非模态窗口
        self.others_window.show()
    def open_model_window(self):
        """打开模型参数窗口"""
        if not self.model_window:  # 避免重复创建
            self.model_window = ModelParameterWindow(self)
            self.model_window.setWindowModality(Qt.NonModal)  # 非模态窗口
        self.model_window.show()    
    def open_camera_window(self):
        if not self.camera_window:
            self.camera_window = CameraParameterWindow(self)  # 传入 self
            self.camera_window.setWindowModality(Qt.NonModal)
        self.camera_window.show()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())