import os
import sys
from PyQt5.QtWidgets import QApplication
from ui.window import MyWindow


"""
行间除草的前端系统代码
"""

# 切换到项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
