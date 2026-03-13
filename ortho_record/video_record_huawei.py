import cv2
import os
import time

MAX_FRAME_COOUNT = 120

"""
这个代码在华为开发板上运行
"""
class VideoRecoder:
    def __init__(self, video_source):
        self.video_source = video_source
        #Linux系统用这个Linux: CAP_V4L2 默认cv2.CAP_ANY windows CAP_MSMF 或者CAP_DSHOW
        self.cap = cv2.VideoCapture(self.video_source,cv2.CAP_V4L2)  

        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = None
        print("摄像头打开成功")

    def set_width_and_height(self, width, height):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # 获取实际分辨率
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"🎥 录制分辨率: {self.frame_width}x{self.frame_height}")

    def set_fps(self, fps):
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        print(f"🎞 录制 FPS: {fps}")

        if self.fps == 0:
            self.fps = fps  # 部分摄像头不支持 60 FPS，会自动回落到 30 FPS
        print(f"🎞 FPS: {self.fps}")

    def validate_fps(self,output_filename):
        cap2 = cv2.VideoCapture(output_filename)

        # 检查视频流是否打开成功
        if not cap2.isOpened():
            print("Error: Could not open video stream.")
            exit()

        # 获取视频的帧率（FPS）
        fps = cap2.get(cv2.CAP_PROP_FPS)
        print(f"Video FPS: {fps}")
        if fps > self.fps or fps < self.fps:    
            print("录制视频文件的帧率异常")


    def start_recording(self, output_folder=None):
        # 创建保存视频的文件夹
        if  output_folder is None:
            output_folder = "saved_videos"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 生成带时间戳的文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = os.path.join(output_folder, f"output_{timestamp}.mp4")

        self.out = cv2.VideoWriter(output_filename, self.fourcc, self.fps, (self.frame_width, self.frame_height))
        
        print(f"📁 正在保存视频到: {output_filename}")
        # cv2.namedWindow("External Camera", cv2.WINDOW_NORMAL)
        # cv2.namedWindow("External Camera", cv2.WINDOW_AUTOSIZE)
        # cv2.setWindowProperty("External Camera", cv2.WINDOW_GUI_NORMAL, cv2.WINDOW_AUTOSIZE)

        start_time = time.perf_counter()  # 高精度计时
        frame_count = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                break


            self.out.write(frame)  
            # cv2.imshow("External Camera", frame)
            frame_count += 1

            if frame_count >= MAX_FRAME_COOUNT:
                break

            # **键盘控制变焦**
            # key = cv2.waitKey(1) & 0xFF
            # if key == ord('q'):  # 按 'q' 退出
            #     break

        end_time = time.perf_counter()  # 高精度计时
        self.cap.release()
        self.out.release()
        # cv2.destroyAllWindows()

        self.validate_fps(output_filename)
        print("end_time - start_time",(end_time - start_time))
        print("总写入帧数:", frame_count, "播放时长:", frame_count / self.fps, "秒")

if __name__ == '__main__':
    # 选择外接摄像头
    video_source = 1
    recorder = VideoRecoder(video_source)
    recorder.set_width_and_height(640, 480)
    recorder.set_fps(30)
    recorder.start_recording()

