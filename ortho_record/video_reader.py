import cv2
import os
import time

class VideoReader:
    def __init__(self, video_source):
        self.video_source = video_source
        self.format = format
        #Linux系统用这个Linux: CAP_V4L2 默认cv2.CAP_ANY windows CAP_MSMF 或者CAP_DSHOW
        self.cap = cv2.VideoCapture(self.video_source)  
        # if format == 'avi':
        #     print("编码格式为Motion-JPEG")
        #     self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        #     self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        # else:   #mp4
        #     print("编码格式为MPEG-4")
        #     self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        #     # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))

        current_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        print(f"当前格式代码: {current_fourcc}")  # 1196444237 表示MJPG


    def start_reading(self, max_frame_count,output_folder="saved_videos"):
        # 创建保存视频的文件夹
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        

        frame_count = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                break

            frame_path = f'{output_folder}\\frame_{frame_count}.jpg'
            cv2.imwrite(frame_path, frame)  
            # cv2.imshow("External Camera", frame)
            frame_count += 1

            if frame_count >= max_frame_count:
                break


        self.cap.release()


if __name__ == "__main__":
    file = r'D:\myapplication\codeup\crop_web-client-pp\saved_videos\output_20250612_194449.avi'
    
    # file = r'D:\myapplication\codeup\crop_web-client-pp\saved_videos\output_20250612_194418.mp4'
    reader = VideoReader(file)  
    reader.start_reading(20)