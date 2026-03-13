import os
import sys
import re
import unicodedata
import pandas as pd
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.font_manager import FontProperties
from qtpy import QtWidgets, QtGui

from service import log_service as log
from service.web_service import build_client
from ui.thread1 import *
from ui.cutter_window import CutterParameterWindow
from ui.crop_window2 import CropParameterWindow
from ui.camera_window import CameraParameterWindow
from ui.model_window import ModelParameterWindow
from ui.DemoBoard_window import DemoBoardParameterWindow
from ui.others_window import OtherParameterWindow
from clientside.client_io import IOClient


font_set = FontProperties(fname=r"res/msyh.ttc", size=10)


"""
株间除草系统主界面
"""


class SystemSettings():
    unetModel = 0
    yoloModel = 1


class CameraBigVideo():
    camera1 = 0
    camera2 = 1
    camera3 = 2
    camera4 = 3


class MyWindow(QWidget):
    double_clicked_item = pyqtSignal(str)

    # 构造函数
    def __init__(self, parent=None,
                server_ip='127.0.0.1',
                video_port=8090,
                instruction_port=8091,
                system_type='inrow_weeder'):
        super().__init__(parent)

        self.server_ip = server_ip
        self.video_port = video_port
        self.instruction_port = instruction_port
        self.system_type = system_type

        self.unit_ui()

        self.camera_thread1.plot_signal.connect(self.plot_from_thread)

        # 统一管理参数设置页面
        self.init_parameter_pages()
        # self.ui.cutter_parameter.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(0))
        # self.ui.Crop_parameter.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(1))
        # self.ui.Camera_parameter.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(2))
        # self.ui.modelBtn.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(3))
        # self.ui.DemoBoard_parameter.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(4))
        # self.ui.Other_parameter.clicked.connect(lambda: self.parameter_stack.setCurrentIndex(5))

        self.clientio = IOClient(server_ip, video_port, instruction_port, system_type)
        


    def get_clientio(self):
        """获取IOClient实例"""
        return self.clientio

   
    def init_parameter_pages(self):
        self.ui.parameter_stack.setVisible(False)
        self.ui.parameter_stack_holder.setVisible(False)
       

        self.ui.cutter_parameter.clicked.connect(self.show_cutter_window)
        self.ui.Crop_parameter.clicked.connect(self.show_crop_window)
        self.ui.Camera_parameter.clicked.connect(self.show_camera_window)
        self.ui.modelBtn.clicked.connect(self.show_model_window)
        self.ui.DemoBoard_parameter.clicked.connect(self.show_demoboard_window)
        self.ui.Other_parameter.clicked.connect(self.show_other_window)
        self.ui.CLOSEDOWN.clicked.connect(self.close_application)

    # def close_application(self):
    #     QApplication.quit()  #退出整个程序
    def close_application(self):
        reply = QMessageBox.question(
            self,
            "退出确认",
            "确定要退出系统吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            QApplication.quit()
    def show_cutter_window(self):
        dialog = CutterParameterWindow(self)
        dialog.exec_()

    def show_crop_window(self):
        dialog = CropParameterWindow(self)
        dialog.exec_()

    def show_camera_window(self):
        dialog = CameraParameterWindow(self)
        dialog.exec_()

    def show_model_window(self):
        dialog = ModelParameterWindow(self)
        dialog.exec_()

    def show_demoboard_window(self):
        dialog = DemoBoardParameterWindow(self)
        dialog.exec_()

    def show_other_window(self):
        dialog = OtherParameterWindow(self)
        dialog.exec_()

    def plot_from_thread(self, time_list, bias_list):
        self.ax.clear()
        self.ax.plot(time_list, bias_list, color='b')
        self.canvas.draw()

    def unit_ui(self):
        # self.ui = uic.loadUi("res/artui.ui", self)
        from res.artui_ui import Ui_home
        self.ui = Ui_home()
        self.ui.setupUi(self)
        self.ui.set_system_name("株间除草系统主界面")

        # 设置无边框
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # --------------------------------日志组件-----------------------------
        # 日志的textBrowser
        self.textBrowser = self.ui.textBrowser
        # 将日志放在textBrowser里
        log.set_log(self.textBrowser)
        log.info_msg("成功启动系统")
        # 内容
        # log.info_msg("textBrowser内容")

        # ------------------------------画布----------------------------
        self.fig = plt.figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.vlayout = QVBoxLayout()

        self.vlayout.addWidget(self.canvas)
        self.widget = self.ui.graph
        self.vlayout.setContentsMargins(2, 0, 0, 0)

        self.widget.setLayout(self.vlayout)
        self.widget.setObjectName("偏移量")
        # 初始化matplotlib显示区域
        self.ax = self.fig.subplots()
        self.ax.spines['top'].set_visible(False)  # 顶边界不可见
        self.ax.spines['right'].set_visible(False)  # 右边界不可见
        self.ax.spines['bottom'].set_position(('data', 0))  # data表示通过值来设置x轴的位置，将x轴绑定在y=0的位置
        self.ax.set_title('Camera1偏移量', fontproperties=font_set)

        # -----------------小屏幕的三个Qlabel----------------------------------
        # all屏幕时间
        self.c1_time = self.ui.camera1_time
        self.c2_time = self.ui.camera2_time
        self.c3_time = self.ui.camera3_time
        self.c4_time = self.ui.camera4_time
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_time)  # 这个通过调用槽函数来刷新时间
        self.timer.start(1000)  # 每隔一秒刷新一次，这里设置为1000ms

        # ------------------------小屏幕----------------------------
        # 四个相机的无信号的Qlabel
        self.status1 = self.ui.status_c1
        self.status2 = self.ui.status_c1_2
        self.status3 = self.ui.status_c1_3
        self.status4 = self.ui.status_c1_4

        self.big_status = self.ui.big_status

        self.camera1 = self.ui.showc1
        self.camera2 = self.ui.showc2
        self.camera3 = self.ui.showc3
        self.camera4 = self.ui.showc4
        self.video_transform = self.ui.stackedWidget

        self.video_transform.setCurrentIndex(0)

        # 双击切换
        cameras = [self.camera1, self.camera2, self.camera3, self.camera4]
        for camera in cameras:
            camera.mouseDoubleClickEvent = lambda event, cam=camera: self.handle_camera_double_clicked_small2big(event,
                                                                                                                 cam)
        # 创建摄像头线程
        self.camera_thread1 = CameraThread1(self)
        self.camera_thread2 = CameraThread2(self)
        self.camera_thread3 = CameraThread3(self)
        self.camera_thread4 = CameraThread4(self)
        self.camera_thread1.image_data.connect(self.display_image_1)
        self.camera_thread2.image_data.connect(self.display_image_2)
        self.camera_thread3.image_data.connect(self.display_image_3)
        self.camera_thread4.image_data.connect(self.display_image_4)

        # self.camera_thread1 = CameraThread1(self)
        # print(self.ui.__dict__)
        # ----------------------------------大屏幕---------------------------------
        # 大屏幕
        self.big_video = self.ui.show_big_video
        self.big_video.mouseDoubleClickEvent = lambda event: self.handle_camera_double_clicked_big2small(event)
        # 大屏幕时间
        self.big_camera_time = self.ui.big_time
        # 大屏幕时间
        self.camera_name = self.ui.camera_name
        # 注意如果qt文件没有要创建一个名为camera_name的qlabel放在大屏幕左下角

        # -------------------------------------日志-------------------------------------

        # ------------logs---------------
        # --------------------------logs and errors--------------------------
        # logs和errors表都用self.diary_table_logs都用这个表
        self.diary_table_logs = self.ui.TabWidget_logs
        self.diary_table_logs.setEditTriggers(QTableWidget.NoEditTriggers)  # 设置表格为不可编辑
        # 根据中控及设置表格大小
        self.diary_table_logs.setColumnWidth(0, 50)
        self.diary_table_logs.setColumnWidth(1, 100)
        self.diary_table_logs.setColumnWidth(2, 250)
        self.diary_table_logs.setColumnWidth(3, 150)
        self.diary_table_logs.setColumnWidth(4, 150)
        self.diary_table_logs.verticalHeader().setDefaultSectionSize(45)
        self.diary_table_logs.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        # 隐藏垂直表头
        self.diary_table_logs.verticalHeader().setVisible(False)
        # 将第0列全变成方块儿
        for i in range(10):
            widget = QWidget()
            widget.checkbox = QCheckBox()  # 将checkbox放在widget中
            # widget.checkbox.setCheckState(Qt.Unchecked)  # 默认全部勾选
            playout = QHBoxLayout(widget)
            playout.addWidget(widget.checkbox)  # 为小部件添加checkbox属性
            playout.setAlignment(Qt.AlignCenter)  # 设置小控件水平居中
            playout.setContentsMargins(5, 2, 5, 2)
            widget.setLayout(playout)  # 在QWidget放置布局

            self.diary_table_logs.setCellWidget(i, 0, widget)
        # # 设置操作那一列,btnsForRow是自己实现的方法
        for i in range(10):
            self.diary_table_logs.setCellWidget(i, 4, self.btnsForRow())
        # 点击logs和errors切换界面
        self.logs = self.ui.logs
        self.errors = self.ui.errors

        # 两个按钮的切换目前并没有引起线程问题，最后可能还是推荐开个线程去处理每一个任务
        # 线程里只用来发射信号，处理操作全交给主线程去做，线程类最好里不要有任何处理逻辑
        # log -> 0
        # error -> 1
        self.status_log_error = 0
        self.logs.clicked.connect(self.diary_load_logs)

        self.errors.clicked.connect(self.diary_load_errors)

        # ------------------------将日志写入表格-----------------------
        # 定义 lines 变量
        self.lines = []

        # 当前页数和总页数
        self.current_page = 1
        self.total_pages = 1
        self.total_records = 0

        self.records_label = self.ui.records_label
        self.page_label = self.ui.page_label
        self.page_input = self.ui.page_input
        self.next_button = self.ui.next_button
        self.prev_button = self.ui.prev_button
        self.confirm_button = self.ui.confirm_button

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.confirm_button.clicked.connect(self.go_to_page)

        # 全选
        # 点击过logs后才能按全选
        self.tag = 0
        self.selectall = self.ui.selectall
        self.selectall.clicked.connect(self.selectalllog)

        # 删除选中
        self.delChked = self.ui.del_checked
        self.delChked.clicked.connect(self.deleteCheckedlog)

        # 下载选择
        self.dlChked = self.ui.download_checked
        self.dlChked.clicked.connect(self.downloadCheckedlog)
        # ----------------------摄像头管理----------------------------------------
        
        # parameter
        self.parameter = self.ui.parameter
        self.parameter.setColumnWidth(0, 100)
        self.parameter.setColumnWidth(1, 200)
        self.parameter.setColumnWidth(2, 200)
        self.parameter.setColumnWidth(3, 200)
        self.parameter.verticalHeader().setDefaultSectionSize(45)
        self.parameter.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.Submit_param = self.ui.Submit_param
        self.Submit_param.clicked.connect(self.updateparam)
        self.Submit_status = self.ui.Submit_status
        self.Submit_status.clicked.connect(self.updatestatus)

        # status
        self.status = self.ui.status
        self.parameter.verticalHeader().setDefaultSectionSize(45)
        self.parameter.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.Submit_status.clicked.connect(self.updatestatus)
        self.paramread()
        self.statusread()
        # 默认要开始加载的东西
        self.diary_load_logs()

        # -------------------------------------系统设置-----------------------------
        # self.unetModel = self.ui.unet_model
        # self.yoloModel = self.ui.yolo_model
        # self.unetModel.clicked.connect(self.unetModel_clicked)
        # self.yoloModel.clicked.connect(self.yoloModel_clicked)

    # --------------------------------------监控大屏-------------------------------------------------
    # mvc这些处理都应该写在service
    # 显示时间
    def show_time(self):
        time = QDateTime.currentDateTime()  # 获取当前时间
        timedisplay = time.toString("yyyy-MM-dd hh:mm:ss dddd")  # 格式化一下时间
        # print(timedisplay)
        self.c1_time.setText(timedisplay)
        self.c2_time.setText(timedisplay)
        self.c3_time.setText(timedisplay)
        self.c4_time.setText(timedisplay)
        self.big_camera_time.setText(timedisplay)

    # 监控页面屏幕转换优化
    def handle_camera_double_clicked_small2big(self, event, camera):
        self.big_status.setVisible(False)
        camera_mapping = {
            "showc2": (self.status2, self.camera_thread2, "camera2"),
            "showc3": (self.status3, self.camera_thread3, "camera3"),
            "showc4": (self.status4, self.camera_thread4, "camera4"),
            "showc1": (self.status1, self.camera_thread1, "camera1"),
        }
        status, camera_thread, camera_name = camera_mapping[camera.objectName()]

        self.camera_big_video = int(camera_name[-1:]) - 1

        status.setVisible(False)
        camera_thread.start()
        # if not camera_thread.isRunning():
        #     camera_thread.start()
        # else:
        #     log.info_msg("Thread already running")
        self.video_transform.setCurrentIndex(1)
        self.camera_name.setText(camera_name)
        log.info_msg(camera_name)

    # 这四个函数最后会捏成一块儿，方便维护
    # todo
    def display_image_1(self, img):
        pixmap = QtGui.QPixmap.fromImage(img)
        self.camera1.setPixmap(pixmap)
        self.camera1.setScaledContents(True)
        if self.camera_big_video == CameraBigVideo.camera1:
            self.big_video.setPixmap(pixmap)
            self.big_video.setScaledContents(True)
            self.big_status.setVisible(False)
            print("当前camera_big_video 在1中的为{}".format(self.camera_big_video))
        QtWidgets.QApplication.processEvents()

    def display_image_2(self, img):
        pixmap = QtGui.QPixmap.fromImage(img)
        self.camera2.setPixmap(pixmap)
        self.camera2.setScaledContents(True)  # 自适应大小
        if self.camera_big_video == CameraBigVideo.camera2:
            self.big_video.setPixmap(pixmap)
            self.big_video.setScaledContents(True)
            self.big_status.setVisible(False)
            print("当前camera_big_video 在2中的为{}".format(self.camera_big_video))
        QtWidgets.QApplication.processEvents()

    def display_image_3(self, img):
        pixmap = QtGui.QPixmap.fromImage(img)
        self.camera3.setPixmap(pixmap)
        self.camera3.setScaledContents(True)  # 自适应大小
        if self.camera_big_video == CameraBigVideo.camera3:
            self.big_video.setPixmap(pixmap)
            self.big_video.setScaledContents(True)
            self.big_status.setVisible(False)
            print("当前camera_big_video 在3中的为{}".format(self.camera_big_video))
        QtWidgets.QApplication.processEvents()

    def display_image_4(self, img):
        pixmap = QtGui.QPixmap.fromImage(img)
        self.camera4.setPixmap(pixmap)
        self.camera4.setScaledContents(True)  # 自适应大小
        if self.camera_big_video == CameraBigVideo.camera4:
            self.big_video.setPixmap(pixmap)
            self.big_video.setScaledContents(True)
            self.big_status.setVisible(False)
            print("当前camera_big_video 在4中的为{}".format(self.camera_big_video))
        QtWidgets.QApplication.processEvents()

    ## 大屏幕切换到小屏幕
    def handle_camera_double_clicked_big2small(self, event):
        self.video_transform.setCurrentIndex(0)

    # ---------------------------------------监控界面画布--------------------------------------------------
    # 画布
    def plotfig(self):
        self.ax.autoscale_view()
        # 绘图
        self.ax.plot(self.t_list, self.y_list, c=self.line_color, linewidth=1)
        self.fig.canvas.draw()  # 画布重绘，self.figs.canvas
        self.fig.canvas.flush_events()  # 画布刷新 self.figs.canvas
        self.t_list.append(self.t[self.i])  # 更新数据
        self.y_list.append(self.y[self.t[self.i]])  # 每次给原来数据加入新数据
        self.i += 10
        if self.i >= len(self.t):
            self.testTimer.stop()

    # -----------------------------------------摄像头管理-------------------------------------------------
    def updateparam(self):
        # 读取当前改动
        ilist = []
        for row in range(4):
            ilist.append([])
            for col in range(4):
                ilist[row].append(self.parameter.item(row, col).text())
        try:
            client = build_client(ADDRESS)
            client.send(str(ilist).encode("utf-8"))
            client.recv(1024)
            log.info_msg("参数设置成功")
            # 写入文件
            self.paramwrite(ilist)
        except Exception as e:
            log.info_msg("参数设置失败", 1)
            self.paramread()

    def paramwrite(self, ilist):
        column = ['角度', '高度', '型号', '像素']
        data2 = ['Camera1', 'Camera2', 'Camera3', 'Camera4']
        df = pd.DataFrame(ilist, columns=column, index=data2)
        # 写入
        df.to_csv('res/Param.csv')

    def updatestatus(self):
        # 读取当前改动
        ilist = []
        for row in range(4):
            col = 0
            ilist.append(self.status.item(row, col).text())
        if len(ilist) == 0:
            log.info_msg("更新摄像头状态失败", 1)
            # 更新失败后要重新加载文件
            self.statusread()
        else:
            log.info_msg("更新摄像头运行状态：" + str(ilist))
            # 写入文件
            self.statuswrite(ilist)

    def statuswrite(self, ilist):
        column = ['运行状态']
        data2 = ['Camera1', 'Camera2', 'Camera3', 'Camera4']
        df = pd.DataFrame(ilist, columns=column, index=data2)
        # 写入
        df.to_csv('res/Status.csv')

    def statusread(self):
        _translate = QtCore.QCoreApplication.translate
        try:
            status = pd.read_csv('res/Status.csv', encoding="utf-8")
            S = status.iloc[:, :].values
            # 用读取的参数为页面赋值
            for row in range(4):
                col = 0
                item = self.status.item(row, col)
                item.setText(_translate("status", str(S[row, col + 1])))
        except FileNotFoundError as e:
            log.info_msg(str(e), 1)
        except IOError as e:
            log.info_msg(str(e), 1)

    def paramread(self):
        _translate = QtCore.QCoreApplication.translate
        try:
            import pandas as pd
            param = pd.read_csv('res/Param.csv')
            P = param.iloc[:, :].values
            # 用读取的参数为页面赋值
            for row in range(4):
                for col in range(4):
                    item = self.parameter.item(row, col)
                    item.setText(_translate("parameter", str(P[row, col + 1])))
        except FileNotFoundError as e:
            log.info_msg(str(e), 1)

    # -----------------------------------------摄像头管理-------------------------------------------------

    # -----------------------------------------日志查询---------------------------------------------------

    def diary_load_logs(self):
        if os.path.exists("res/logs/run/run.txt"):
            self.load_file('res/logs/run/run.txt')
            self.status_log_error = 0
        else:
            log.info_msg("无运行日志")

    def diary_load_errors(self):
        if os.path.exists("res/logs/error/error.txt"):
            self.load_file('res/logs/error/error.txt', reset_page=True)
            self.status_log_error = 1
        else:
            log.info_msg("无异常日志")

    def load_file(self, file_path, reset_page=False):
        def is_safe(line):
            try:
            # 排除太短的
                if not line or len(line.strip()) < 24:
                    return False
            # 检测是否纯 ASCII
                line.encode('ascii')
                return True
            except UnicodeEncodeError:
                return False

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            raw_lines = file.readlines()
            self.lines = [line for line in raw_lines if is_safe(line)]

        print("最终过滤后最后5行：")
        for line in self.lines[-5:]:
            print(repr(line))

        self.total_pages = (len(self.lines) + 9) // 10
        self.total_records = len(self.lines)
        self.records_label.setText(f"共{self.total_records}条记录")

        if reset_page:
            self.current_page = 1

        self.update_table(file_path)
        self.next_button.setEnabled(True)




    
    def create_checkbox_widget(self):
        widget = QWidget()
        checkbox = QCheckBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(5, 2, 5, 2)
        widget.setLayout(layout)
        widget.checkbox = checkbox  
        return widget

    def update_table(self, file_path):
        self.diary_table_logs.setRowCount(0)
        start_row = (self.current_page - 1) * 10
        end_row = min(start_row + 10, len(self.lines))

        for i in range(start_row, end_row):
            row_position = self.diary_table_logs.rowCount()
            self.diary_table_logs.insertRow(row_position)

            self.diary_table_logs.setCellWidget(row_position, 0, self.create_checkbox_widget())

            item = QTableWidgetItem(str(i + 1))
            item.setForeground(QColor('white'))
            self.diary_table_logs.setItem(row_position, 1, item)

            try:
                line = self.lines[i].strip()
                filename = line[-23:-4] if len(line) >= 23 else "未知文件"
                item = QTableWidgetItem(filename)
                item.setForeground(QColor('white'))
                self.diary_table_logs.setItem(row_position, 2, item)
            except Exception as e:
                item = QTableWidgetItem("解析失败")
                item.setForeground(QColor('white'))
                self.diary_table_logs.setItem(row_position, 2, item)

            try:
                line = self.lines[i].strip()
                match = re.search(r'\d{4}-\d{2}-\d{2}', line)
                logdate = match.group() if match else "未知日期"
                item = QTableWidgetItem(logdate)
                item.setForeground(QColor('white'))
                self.diary_table_logs.setItem(row_position, 3, item)
            except Exception as e:
                item = QTableWidgetItem("解析失败")
                item.setForeground(QColor('white'))
                self.diary_table_logs.setItem(row_position, 3, item)

            self.diary_table_logs.setCellWidget(row_position, 4, self.btnsForRow())

        for _ in range(10 - (end_row - start_row)):
            row_position = self.diary_table_logs.rowCount()
            self.diary_table_logs.insertRow(row_position)
            for j in range(5):
                item = QTableWidgetItem('')
                self.diary_table_logs.setItem(row_position, j, item)

        self.page_label.setText(f'当前第 {self.current_page} 页,共 {self.total_pages} 页')
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def prev_page(self):
        # 切换到上一页
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table('')  # 更新当前页的内容
            self.tag = 0

    def next_page(self):
        # 切换到下一页
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.tag = 0
            self.update_table('')  # 更新当前页的内容

    def go_to_page(self):
        # 跳转到指定页
        try:
            page_to_jump = int(self.page_input.text())
            if 1 <= page_to_jump <= self.total_pages:
                self.current_page = page_to_jump
                self.update_table('')  # 更新当前页的内容
                self.tag = 0
            else:
                QMessageBox.warning(self, "提示", "没有此页", QMessageBox.Ok)
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效的页码", QMessageBox.Ok)

    def btnsForRow(self):
        widget = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QHBoxLayout()

        checkBtn = QtWidgets.QPushButton("查看")
        downloadBtn = QtWidgets.QPushButton("下载")
        deleteBtn = QtWidgets.QPushButton("删除")

        checkBtn.clicked.connect(self.check)
        downloadBtn.clicked.connect(self.download)
        deleteBtn.clicked.connect(self.delete)

        buttonLayout.addWidget(checkBtn)
        buttonLayout.addWidget(deleteBtn)
        buttonLayout.addWidget(downloadBtn)
        buttonLayout.setContentsMargins(5, 2, 5, 2)
        widget.setLayout(buttonLayout)

        return widget

    def download(self):
        button = self.sender()
        if button:
            # 确定位置的时候这里是关键
            row = self.diary_table_logs.indexAt(button.parent().pos()).row()
            col = 2
            tableitem = self.diary_table_logs.item(row, col)
            if tableitem != None:
                filename = tableitem.text()
                folder = re.match("^.{10}", filename).group()
                log.info_msg(f"下载文件 {filename}")
                if self.status_log_error == 0:
                    path = f'res/logs/run/{folder}/{filename}.txt'
                    sub_file = 'run'
                else:
                    path = f'res/logs/error/{folder}/{filename}.txt'
                    sub_file = 'error'
                if (os.path.isfile(path)):
                    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')

                    # 指定目标子目录名称，若目录不存在则创建
                    subdirectory1 = os.path.join('logs', sub_file)
                    # logs\run\2024-04-09
                    subdirectory2 = os.path.join(subdirectory1, filename[:10])
                    subdirectory = os.path.join(subdirectory2, filename + '.txt')
                    target_subdirectory_path = os.path.join(desktop_path, subdirectory)

                    # 源文件路径（要复制的文件）
                    source_path = path

                    # 目标文件路径（复制到的位置）
                    target_path = target_subdirectory_path

                    # 创建并启动线程
                    file_copy_thread = FileCopyThread(source_path, target_path)
                    file_copy_thread.progress_signal.connect(lambda progress: print("Progress:", progress))
                    file_copy_thread.start()

                    # 等待线程完成
                    file_copy_thread.wait()

                    log.info_msg(f"下载成功")
                else:
                    log.info_msg("文件不存在")
            else:
                log.info_msg("无指定路径")

    def check(self):
        button = self.sender()
        if button:
            try:
                row = self.diary_table_logs.indexAt(button.parent().pos()).row()
                col = 2
                tableitem = self.diary_table_logs.item(row, col)
                if tableitem is None:
                    log.info_msg("未找到文件名项")
                    return

                filename = tableitem.text()
                if not filename:
                    log.info_msg("文件名为空")
                    return

                log.info_msg(f"查看文件 {filename}")
                folder = re.match("^.{10}", filename)
                if not folder:
                    log.info_msg("文件名格式不正确，无法提取日期")
                    return
                folder = folder.group()

                if self.status_log_error == 0:
                    path = f'res/logs/run/{folder}/{filename}.txt'
                else:
                    path = f'res/logs/error/{folder}/{filename}.txt'

                if not os.path.isfile(path):
                    log.info_msg("文件不存在")
                    QMessageBox.warning(self, "错误", f"文件不存在：{path}")
                    return

                self.checked_thread = CheckedThread(path)
                self.checked_thread.finished.connect(self.on_thread_finished)
                self.checked_thread.start()
                log.info_msg("查看线程已启动")

            except Exception as e:
                log.info_msg(f"查看失败: {str(e)}", 1)
                QMessageBox.critical(self, "错误", f"查看日志时发生异常：\n{str(e)}")


    def delete(self):
        button = self.sender()
        if button:
            # 确定位置的时候这里是关键
            row = self.diary_table_logs.indexAt(button.parent().pos()).row()
            col = 2
            tableitem = self.diary_table_logs.item(row, col)
            if tableitem != None:
                filename = tableitem.text()
                log.info_msg(f"删除文件 {filename}")
                folder = re.match("^.{10}", filename).group()
                if self.status_log_error == 0:
                    path = f'res/logs/run/{folder}/{filename}.txt'
                    run_file_path = f'res/logs/run/run.txt'  # 路径可能需要改
                    target_path = f'res/logs/run/{folder}/{filename}.txt'  # 文件里存的文件格式
                    # run目录下的文件夹路径
                    run_file_judge = f'res/logs/run/{folder}'
                else:
                    path = f'res/logs/error/{folder}/{filename}.txt'
                    run_file_path = f'res/logs/error/error.txt'  # 路径可能需要改
                    target_path = f'res/logs/error/{folder}/{filename}.txt'  # 文件里存的文件格式
                    # run目录下的文件夹路径
                    run_file_judge = f'res/logs/error/{folder}'

                if (os.path.isfile(path)):
                    os.remove(path)
                    # 如果目录里没有文件则删除这个目录
                    if (len(os.listdir(run_file_judge)) == 0):
                        os.rmdir(run_file_judge)

                    # 删除run文件下对应记录
                    with open(run_file_path, 'r') as file:
                        lines = file.readlines()

                    with open(run_file_path, 'w') as file:
                        for line in lines:
                            if target_path not in line:
                                file.write(line)

                    log.info_msg(f"删除成功")
                else:
                    log.info_msg("文件不存在")
            else:
                log.info_msg("无指定路径")
        self.diary_load_logs()

    # ------------------------------------      全选 删除选中 下载选中    -------------------------------------------

    def get_checkbox_from_table(self, row):
        widget = self.diary_table_logs.cellWidget(row, 0)
        if widget and hasattr(widget, 'checkbox'):
            return widget.checkbox
        return None

    def selectalllog(self):
        start_row = (self.current_page - 1) * 10
        end_row = min(start_row + 10, len(self.lines))
        log.info_msg("进入全选方法")

        try:
            should_check = self.tag == 0
            self.tag = 1 if should_check else 0

            for current_row in range(0, end_row - start_row):
                checkbox = self.get_checkbox_from_table(current_row)
                if checkbox:
                    checkbox.setChecked(should_check)

        except Exception as e:
            log.info_msg(f"全选操作失败：{str(e)}", 1)
            QMessageBox.warning(self, "错误", "执行全选操作时出现异常，请检查数据或联系管理员。")

    def deleteCheckedlog(self):
        start_row = (self.current_page - 1) * 10
        end_row = min(start_row + 10, len(self.lines))
        log.info_msg("进入批量删除方法")
        col = 2
        to_delete = []

        for row in range(0, end_row - start_row):
            checkbox = self.get_checkbox_from_table(row)
            if checkbox and checkbox.isChecked():
                tableitem = self.diary_table_logs.item(row, col)
                if tableitem:
                    to_delete.append(tableitem.text())

        for filename in to_delete:
            folder = re.match("^.{10}", filename).group()
            if self.status_log_error == 0:
                path = f'res/logs/run/{folder}/{filename}.txt'
                run_file_path = f'res/logs/run/run.txt'
                run_file_judge = f'res/logs/run/{folder}'
            else:
                path = f'res/logs/error/{folder}/{filename}.txt'
                run_file_path = f'res/logs/error/error.txt'
                run_file_judge = f'res/logs/error/{folder}'

            if os.path.isfile(path):
                os.remove(path)
                if len(os.listdir(run_file_judge)) == 0:
                    os.rmdir(run_file_judge)

                with open(run_file_path, 'r') as file:
                    lines = file.readlines()
                with open(run_file_path, 'w') as file:
                    for line in lines:
                        if path not in line:
                            file.write(line)

                log.info_msg(f"删除成功: {filename}")
            else:
                log.info_msg(f"文件不存在: {filename}")

        self.diary_load_logs()

    def downloadCheckedlog(self):
        start_row = (self.current_page - 1) * 10
        end_row = min(start_row + 10, len(self.lines))
        col = 2
        log.info_msg("进入批量下载方法")

        for row in range(0, end_row - start_row):
            checkbox = self.get_checkbox_from_table(row)
            if checkbox and checkbox.isChecked():
                tableitem = self.diary_table_logs.item(row, col)
                if tableitem:
                    filename = tableitem.text()
                    folder = re.match("^.{10}", filename).group()
                    if self.status_log_error == 0:
                        path = f'res/logs/run/{folder}/{filename}.txt'
                        sub_file = 'run'
                    else:
                        path = f'res/logs/error/{folder}/{filename}.txt'
                        sub_file = 'error'

                    if os.path.isfile(path):
                        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                        subdirectory = os.path.join('logs', sub_file, filename[:10])
                        target_path = os.path.join(desktop_path, subdirectory, filename + '.txt')

                        file_copy_thread = FileCopyThread(path, target_path)
                        file_copy_thread.progress_signal.connect(lambda progress: print("Progress:", progress))
                        file_copy_thread.start()
                        file_copy_thread.wait()

                        log.info_msg(f"下载成功: {filename}")
                    else:
                        log.info_msg(f"文件不存在: {filename}")

    def on_thread_finished(self):
        QMessageBox.information(self, "完成", "日志文件查看已结束。")
        log.info_msg("查看线程执行完成")
    # ----------------------------------        系统设置-unet-yolo     ----------------------------------------------

    # def unetModel_clicked(self):
    #     try:
    #         client = build_client(ADDRESS)
    #         client.send("unet".encode("utf-8"))
    #         client.recv(1024)
    #         log.info_msg("成功切换为行间除草")
    #     except Exception as e:
    #         log.info_msg("切换行间除草失败", 1)

    # def yoloModel_clicked(self):
    #     try:
    #         client = build_client(ADDRESS)
    #         client.send("yolo".encode("utf-8"))
    #         client.recv(1024)
    #         log.info_msg("成功切换为株间除草")
    #     except Exception as e:
    #         log.info_msg("切换株间除草失败", 1)
