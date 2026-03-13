import sys
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPixmap, QImage
from ultralytics import YOLO
from YOLO.yolov8 import Ui_Form

class OffsetPlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        self.offsets = []
        self.threshold = 100  # 报警阈值 ±100px

    def update_plot(self, new_offset):
        self.offsets.append(new_offset)
        if len(self.offsets) > 100:
            self.offsets.pop(0)
        self.ax.clear()
        self.ax.plot(self.offsets, label='偏移量(px)', color='blue')
        self.ax.axhline(0, color='gray', linestyle='--')
        self.ax.axhline(self.threshold, color='red', linestyle='--', label='+100 px 报警线')
        self.ax.axhline(-self.threshold, color='red', linestyle='--', label='-100 px 报警线')
        self.ax.set_title("实时偏移曲线")
        self.ax.set_ylabel("偏移(px)")
        self.ax.set_xlabel("帧")
        self.ax.legend()
        self.draw()

class MainWindow(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.model = YOLO("yolov8n.pt")
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.cap = None
        self.is_detection_active = False
        self.current_frame = None

        self.picture_detect_pushButton.clicked.connect(self.load_picture)
        self.video_detect_pushButton.clicked.connect(self.load_video)
        self.camera_detect_pushButton.clicked.connect(self.start_camera)
        self.start_detect_pushButton.clicked.connect(self.start_detection)
        self.stop_detect_pushButton.clicked.connect(self.stop_detection)
        self.pause_detect_pushButton.clicked.connect(self.pause_detect)

        self.offset_canvas = OffsetPlotCanvas(self)
        self.verticalLayout.addWidget(self.offset_canvas)

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
                self.detected_frame = results[0].plot()
                self.display_image(self.detected_frame, self.detected_image)
                self.update_offset_from_result(results, self.current_frame.shape[1])
        except Exception as e:
            print(e)

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

    def start_camera(self):
        self.is_detection_active = False
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(0)
        self.timer.start(20)

    def update_frame(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_image(frame, self.original_image)
                if self.is_detection_active:
                    results = self.model.predict(frame)
                    self.detected_frame = results[0].plot()
                    self.display_image(self.detected_frame, self.detected_image)
                    self.update_offset_from_result(results, frame.shape[1])

    def update_offset_from_result(self, results, width):
        boxes = results[0].boxes.xyxy.cpu().numpy()
        center_x = width // 2
        offsets = []
        for box in boxes:
            x1, y1, x2, y2 = box[:4]
            cx = (x1 + x2) / 2
            offset = cx - center_x
            offsets.append(offset)
        if offsets:
            avg_offset = sum(offsets) / len(offsets)
            self.offset_canvas.update_plot(avg_offset)
            if abs(avg_offset) > self.offset_canvas.threshold:
                print(f"偏移超限！当前偏移: {avg_offset:.1f} px")

    def start_detection(self):
        if self.cap and not self.cap.isOpened():
            self.cap.open(self.fileName)
        if self.cap and not self.timer.isActive():
            self.timer.start(20)
        self.is_detection_active = True

    def display_image(self, frame, target_label):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame.shape
        step = channel * width
        qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qImg)
        scaled_pixmap = pixmap.scaled(target_label.size(), QtCore.Qt.KeepAspectRatio)
        target_label.setPixmap(scaled_pixmap)

    def pause_detect(self):
        self.is_detection_active = False
        if self.timer.isActive():
            self.timer.stop()

    def stop_detection(self):
        self.is_detection_active = False
        if self.timer.isActive():
            self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.clear_display(self.original_image)
        self.clear_display(self.detected_image)

    def clear_display(self, target_label):
        target_label.clear()
        target_label.setText('')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
