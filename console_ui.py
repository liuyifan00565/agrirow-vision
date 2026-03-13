
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

"""
这个python文件作为中控系统的入口

"""

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow(               
                server_ip='192.168.137.100',
                 video_port=8090,
                 instruction_port=8091,
                 system_type='interrow_weeder'
                )
    main_window.show()
    sys.exit(app.exec_())

