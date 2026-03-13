import socket
from clientside.socket_util import SocketUtil
import cv2
import string
import random
from PyQt5.QtCore import QThread  #, QObject, pyqtSignal,QTimer


class VideoClient(QThread):
    def __init__(self,server_ip,video_port):
        super().__init__()
        self.server_ip = server_ip
        self.video_port = video_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def get_predictions(self):
        # 保留以下代码
        # self.qthread = QThread()   #此时 VideoClient的父类为QObject
        # self.moveToThread(self.qthread)
        # self.do_connect()
        # self.qthread.started.connect(self.start_predict)
        # self.qthread.start()
        self.start()

    def do_connect(self,connect_func):
        connect_func()

    # 保留以下代码
    # def start_predict(self):
    #     self.client_socket.connect((self.server_ip, self.video_port))
    #     self.timer = QTimer(self)
    #     self.timer.setInterval(0)
    #     self.timer.timeout.connect(self._get_predictions)
    #     self.timer.start()


    # 保留以下代码
    # def _get_predictions(self):
    #     predictions = SocketUtil.recv_prediction(self.client_socket)
        
    #     if predictions.get_flag():
    #         self.process_predictions(predictions)   
    #     else:
    #         self.timer.stop()

    def run(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.client_socket:
            self.client_socket.connect((self.server_ip, self.video_port))
            while True:
                predictions = SocketUtil.recv_prediction(self.client_socket)
                
                if predictions.get_flag():
                    self.process_predictions(predictions)   
                else:
                    break

    
    #子类覆盖，实现具体的处理逻辑
    def process_predictions(self,predictions):
        pass
        


    def _randomStr(self):
        chs = string.ascii_letters + string.digits
        rs = ''.join(random.choices(chs, k=6))
        return rs



# class InterrowVideoClient(VideoClient):
#     def __init__(self,server_ip,video_port):
#         super().__init__(server_ip,video_port)


#     """
#     下面的代码只是临时展示用，需要替换
#     """
#     def process_predictions(self,predictions):
#         print(predictions.get_row_bias())
#         cv2.imwrite(self._randomStr()+'.jpg',predictions.get_frame())



class InrowVideoClient(VideoClient):
    def __init__(self,server_ip,video_port):
        super().__init__(server_ip,video_port)


    """
    下面的代码只是临时展示用，需要替换
    """
    def process_predictions(self,predictions):
        print(predictions.get_crop_bias())
        cv2.imwrite(self._randomStr()+'.jpg',predictions.get_frame())