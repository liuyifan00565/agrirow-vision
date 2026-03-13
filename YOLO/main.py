import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPixmap, QImage
import cv2
from ultralytics import YOLO
from yolov8 import  Ui_Form

#主窗口类继承自QtWidgets.QWidget和Ui_Form
class MainWindow(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        try:
            super().__init__()#调用父类的构造函数
            self.setupUi(self)#设置用户界面
            self.model = YOLO("yolov8n.pt")#连接yolov8模型
            self.timer = QtCore.QTimer()# 初始化一个定时器对用于定时触发特定的事件或操作
            self.timer.timeout.connect(self.update_frame)# 绑定定时器的超时信号到update_frame函数

            self.cap = None
            # 视频捕获对象，初始化为None
            self.is_detection_active = False
            # 检测是否激活的标志，初始为False
            self.current_frame = None
            # 当前帧图像，初始为None


            # 各个按钮绑定功能
            self.picture_detect_pushButton.clicked.connect(self.load_picture)#照片检测
            self.video_detect_pushButton.clicked.connect(self.load_video)#视频检测
            self.camera_detect_pushButton.clicked.connect(self.start_camera)#连接电脑摄像头
            self.start_detect_pushButton.clicked.connect(self.start_detection)#开始检测
            self.stop_detect_pushButton.clicked.connect(self.stop_detection)#停止检测
            self.pause_detect_pushButton.clicked.connect(self.pause_detect)#   暂停检测


        except Exception as e:
            print(e)

#尝试加载图片文件并进行检测
    def load_picture(self):
        try:
            fileName, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Image Files (*.jpg *.png)")
            self.is_detection_active = False

            if fileName:
                if self.timer.isActive():
                    self.timer.stop()
                if self.cap:
                    self.cap.release()
                    self.cap = None

                self.current_frame = cv2.imread(fileName)
                self.display_image(self.current_frame, self.original_image)
                results = self.model.predict(self.current_frame)
                self.detected_frame = results[0].plot()  # 获取检测结果的帧并保存
                self.display_image(self.detected_frame, self.detected_image)
        except Exception as e:
            print(e)
  
#尝试加载视频文件并显示第一帧
    def load_video(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Video Files (*.mp4 *.avi)")
        if fileName:
            if self.cap:
                self.cap.release()
                self.cap = None

            self.cap = cv2.VideoCapture(fileName)
            
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()
                    self.display_image(frame, self.original_image)
                    self.display_image(frame, self.detected_image)
                else:
                    QtWidgets.QMessageBox.warning(self, 'Error', '无法读取视频文件的第一帧。')

    def start_camera(self):#检查视频捕获对象是否已创建且未打开，如果是，则尝试打开指定文件名的视频文件
        self.is_detection_active = False
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(0)
        self.timer.start(20)
#开始定时器，每隔20ms触发一次update_frame事件


#更新当前帧并进行检测
    def update_frame(self):
        # 读取视频流的下一帧
        if self.cap:
            ret, frame = self.cap.read()
            # 如果成功读取帧，则进行处理
            if ret:
                self.current_frame = frame.copy()
                self.display_image(frame, self.original_image)
 
                # 如果检测功能处于激活状态，则使用模型进行预测
                if self.is_detection_active:
                    results = self.model.predict(frame)
                    self.detected_frame = results[0].plot()  # 获取检测结果的帧并保存
                    self.display_image(self.detected_frame, self.detected_image)
#开始目标检测
    def start_detection(self):
        if self.cap and not self.cap.isOpened():
            self.cap.open(self.fileName)
        if self.cap and not self.timer.isActive():
            self.timer.start(20)
        self.is_detection_active = True

#将图像显示在指定的QLabel上
    def display_image(self, frame, target_label):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #将图像从BGR颜色空间转换为RGB颜色空间
        height, width, channel = frame.shape
        #获取图像的高度、宽度和通道数
        step = channel * width # 步长为图像宽度乘以通道数
        qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888) # 创建QImage对象以显示图像
        pixmap = QPixmap.fromImage(qImg) # 创建QPixmap对象以显示图像,并设置其大小为目标标签的大小
        scaled_pixmap = pixmap.scaled(target_label.size(), QtCore.Qt.KeepAspectRatio)# 缩放QPixmap对象以适应目标标签的大小
        target_label.setPixmap(scaled_pixmap)# 设置目标标签的显示内容为QPixmap对象
#暂停目标检测
    def pause_detect(self):
        self.is_detection_active = False

        if self.timer.isActive():
            self.timer.stop()
#停止目标检测并释放摄像头资源
    def stop_detection(self):
        self.is_detection_active = False

        if self.timer.isActive():
            self.timer.stop()

        if self.cap:
            self.cap.release()
            self.cap = None

        self.clear_display(self.original_image)
        self.clear_display(self.detected_image)
#清除目标标签的显示内容并设置为空字符串
    def clear_display(self, target_label):
        target_label.clear()
        target_label.setText('')


if __name__ == "__main__":
#创建一个QApplication实例，用于管理应用程序的控制流和主要设置
    app = QtWidgets.QApplication(sys.argv)
#创建一个MainWindow实例，并显示它
    main_window = MainWindow()
#运行应用程序
    main_window.show()
#进入应用程序的主循环，直到退出
    sys.exit(app.exec_())

