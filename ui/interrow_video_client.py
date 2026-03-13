from clientside.video_client import VideoClient
# from PyQt5.Qt import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
import time
import numpy as np
from clientside import system_enum 

class InterrowVideoClient(VideoClient):

    # image_data = pyqtSignal(QtGui.QImage)
    image_data = pyqtSignal(np.ndarray)
    plot_signal = pyqtSignal(list, list)

    def __init__(self,server_ip,video_port):
        super().__init__(server_ip,video_port)
        self.start_time = time.time()
        self.Time = []
        self.Bias = []


    def connect_video_displayer(self,displayer):  #添加（关联）视频显示组件
        self.image_data.connect(displayer)

    def connect_plotter(self,plotter):     #添加（关联）曲线显示组件
        self.plot_signal.connect(plotter)

    """
    下面的代码只是临时展示用，需要替换
    """
    def process_predictions(self,predictions):
        print(predictions.get_row_bias())
        # cv2.imwrite(self._randomStr()+'.jpg',predictions.get_frame())
        # start_time = time.time()
        # Time = []
        # Bias = []



        bias = predictions.get_row_bias()

        now = time.time() - self.start_time
        if len(self.Bias) < 50:
            self.Bias.append(bias)
            self.Time.append(now)
        else:
            self.Bias.pop(0)
            self.Time.pop(0)
            self.Bias.append(bias)
            self.Time.append(now)

        self.plot_signal.emit(self.Time.copy(), self.Bias.copy())

        # 接收图像数据
        raw = predictions.get_frame()
        # frame_size = predictions.get_frame_size()
        # print("frame_size=",frame_size)

        # pred = raw.reshape((system_enum.IMG_HEIGHT, system_enum.IMG_WIDTH, 3)).copy()
        # pred = raw.reshape((frame_size[0], frame_size[1], 3)).copy()
        # self.image_data.emit(pred)
        
        self.image_data.emit(raw)


