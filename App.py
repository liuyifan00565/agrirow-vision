import sys

from PyQt5.QtWidgets import QApplication
from demo_onePageui2 import OrthophotoApp


def main() -> int:
    """启动 AgriRow Vision 单页桌面原型。"""
    app = QApplication(sys.argv)
    window = OrthophotoApp()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
