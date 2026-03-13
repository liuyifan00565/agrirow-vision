
import os
import time
import cv2
import shutil
import socket
import json
import numpy as np
from PyQt5 import QtGui, QtWidgets
from PyQt5.Qt import *
from PyQt5.QtCore import *

from constant.constant import *
from service.web_service import *
from ui.window import *
from clientside.socket_util import SocketUtil

class CameraThread1(QThread):
    image_data = pyqtSignal(QImage)
    plot_signal = pyqtSignal(list, list)

    def __init__(self, parent=None):
        super(CameraThread1, self).__init__(parent)
        self.parent = parent
        self.working = True

    def run(self):
        try:
            client = build_client(ADDRESS)
            print(f"[CameraThread1] 成功连接到 {ADDRESS}")
        except Exception as e:
            print(f"[CameraThread1] 连接失败：{e}")
            return

        start_time = time.time()
        Time = []
        Bias = []

        while self.working:
            try:
                # 接收偏移值（JSON 格式）
                # try:
                #     bias_json = SocketUtil.recv_txt(client)
                #     bias_obj = json.loads(bias_json)
                #     bias = int(bias_obj.get("row_bias", 0))
                # except Exception as e:
                #     print(f"[CameraThread1] 偏移解析失败：{e}")
                #     continue
                predictions = SocketUtil.recv_prediction(client)
                bias = predictions.get_row_bias()

                now = time.time() - start_time
                if len(Bias) < 5:
                    Bias.append(bias)
                    Time.append(now)
                else:
                    Bias.pop(0)
                    Time.pop(0)
                    Bias.append(bias)
                    Time.append(now)

                self.plot_signal.emit(Time.copy(), Bias.copy())

                # 接收图像数据
                # raw = SocketUtil.recv_img(client)
                raw = predictions.get_frame()
                if raw is None or raw.size != 240 * 320 * 3:
                    print(f"[CameraThread1] 图像数据大小异常：{raw.size if raw is not None else 'None'}")
                    continue

                pred = raw.reshape((240, 320, 3)).copy()
                img = QtGui.QImage(pred.data, pred.shape[1], pred.shape[0], QImage.Format_RGB888)

                if img.isNull():
                    print("[CameraThread1] QImage 无效")
                    continue

                self.image_data.emit(img)
            except Exception as e:
                print(f"[CameraThread1] Error: {e}")
class CameraThread2(QThread):
    image_data = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super(CameraThread2, self).__init__(parent)
        self.parent = parent
        self.working = True
    def __del__(self):
        self.working = False
    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            img = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.image_data.emit(img)


class CameraThread3(QThread):
    image_data = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super(CameraThread3, self).__init__(parent)

    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            img = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.image_data.emit(img)


class CameraThread4(QThread):
    image_data = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super(CameraThread4, self).__init__(parent)
        self.parent = parent
        self.working = True
    def __del__(self):
        self.working = False

    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            img = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.image_data.emit(img)


class FileCopyThread(QThread):
    progress_signal = pyqtSignal(int)

    def __init__(self, source_path, target_path):
        super().__init__()
        self.source_path = source_path
        self.target_path = target_path

    def run(self):
        dst_dir = os.path.dirname(self.target_path)

        # 如果目标目录不存在，则创建
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
            print(f"目标目录 {dst_dir} 已创建。")
        try:
            shutil.copy2(self.source_path, self.target_path)
            log.info_msg(f"文件从 {self.source_path} 成功复制到 {self.target_path}")
            self.progress_signal.emit(100)
        except FileNotFoundError:
            print("源文件不存在，请检查路径是否正确。")
        except PermissionError:
            print("没有足够的权限复制文件，请确保你有写入目标位置的权限。")
        except Exception as e:
            print(f"复制过程中发生错误：{e}")
            self.progress_signal.emit(-1)


# 查看文件线程
# 因为开启视频后，点击查看会卡顿，而不开则不会，所以应该是占用主线程了，毕竟读写很耗费时间
class CheckedThread(QThread):
    finished = pyqtSignal()

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        os.system(rf'notepad {self.path}')
        self.finished.emit()


# 留个小bug，文件一多就会触发，到时候把文件读写变成一个线程
# 但是线程太多了，如果有公共资源占用会引发死锁等一系列问题，后期测试后考虑优化线程的写法和管理

# 日志读写文件线程
# class FileReadWorker(QThread):  # 定义后台工作线程
#     fileContent = pyqtSignal(str)  # 用于传递文件内容的信号
#
#     def __init__(self, operation_file, parent=None):
#         super(FileReadWorker, self).__init__(parent)
#
#     def run(self):
#         if operation_file:
#             with open(fileName, 'r') as file:
#                 content = file.read()
#                 # 发射信号，传递文件内容
#                 self.fileContent.emit(content)
#
''' 写线程或者说不让程序莫名停止规范
为了确保线程安全和良好的用户体验，你需要采取一些策略和技术来设计你的 PyQt 应用程序。以下是一些关键点：

使用信号和槽机制：

在 PyQt 中，使用信号和槽机制来在不同线程之间进行通信是安全的。
当子线程完成时，可以通过发射一个信号来通知主线程。
避免直接在子线程中更新 GUI：

GUI 操作应当始终在主线程（也称为 GUI 线程）中执行。
如果子线程需要更新 GUI，它应该发出信号，让主线程来进行实际的 GUI 更新。
使用 QThread 的正确方式：

在 QThread 的子类中重写 run() 方法，并在该方法中执行线程任务。
不要在 __init__ 方法中执行长时间运行的操作，因为这会阻塞构造函数，可能导致死锁。
对于耗时的任务使用 QProcess：

QProcess 可以用于替代 os.system 或 subprocess.call，因为它允许你处理进程的输入、输出和错误管道，并且可以监控进程的状态。
优雅的处理异常和错误：

捕获可能发生的异常，并给出相应的用户反馈，例如使用消息框显示错误信息。
确保外部命令失败时有恢复策略或向用户提供明确的错误信息。
提供用户反馈：

当启动耗时的操作时，可以使用进度条或状态信息来通知用户操作正在进行。
如果可能，提供一个取消操作的选项，使用户可以中断正在执行的任务。
使用 QTimer 来避免阻塞：

如果你需要在一段时间后执行某项任务，而不是立即执行，可以使用 QTimer 来安排任务，这样就不会冻结 GUI。
资源清理：

完成任务后，确保释放资源并正确结束线程。
使用 deleteLater() 方法可以帮助管理对象的生命周期。
测试不同场景：

在不同的平台和环境下测试你的应用，以确保线程安全和良好的用户体验。

'''
'''
任务:
    1、进入此系统生成日志未写
    2、点击某一操作记录日志未写
    3、需要自定义日志类型，是在service的log
'''
