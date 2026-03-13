import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget
from res.chooseModel_ui import Ui_Form
# from ui.window import MyWindow
# from ui2.window import MyWindow
import ui
# import ui.window
import ui.new_window
import ui2
import ui2.window

# 切换到项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

class ChooseWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowTitle("智能除草机中控系统")
        self.ui.interrowbtn.clicked.connect(self.open_interrow_window)
        self.ui.inrowbtn.clicked.connect(self.open_inrow_window)

    def open_interrow_window(self):
        # self.hide()  # 隐藏选择界面
        self.main_window = ui.new_window.MyWindow(system_type='interrow_weeder')  # 传入 system_type 参数
        self.main_window.show()

    def open_inrow_window(self):
        # self.hide()
        self.main_window = ui2.window.MyWindow(system_type='inrow_weeder')
        self.main_window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    choose_window = ChooseWindow()
    choose_window.show()
    sys.exit(app.exec_())
