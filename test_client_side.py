from clientside.client_io import IOClient
from clientside.param import Parameter
import os



#测试同步参数
def test_sync_params():
    client.sync_params()

def test_load_params():
    param = client.load_params()
    print(param.to_json())

 #测试切换系统
def test_switch_system(system_type):
    client.switch_system(system_type)

#测试切换模型
def test_switch_model(model_name):
    client.switch_model(model_name)

 #测试停止模型
def test_stop_model():
    client.stop_model()

#测试启动模型
def test_start_model():
    client.start_model()


def test_save_params(new_params):
    client.save_params(new_params)

def test_switch_start_model(model_name):
    client.switch_model(model_name)
    client.start_model()


client = IOClient("192.168.137.100",8090,8091,'inrow_weeder')
# client = IOClient("127.0.0.1",8090,8091,'inrow_weeder')

if __name__ == "__main__":

    # # test_switch_system("inrow_weeder")
    # test_switch_model('yolo8')
    # test_start_model()

    # test_switch_system("interrow_weeder")
    # test_switch_model('yolo11_row')
    # test_start_model()

    # test_load_params()

    # new_params = Parameter()
    # new_params.set_param("camera.vertical_angle","12.5")    
    test_start_model()

# import socket
# import numpy as np
# import cv2

# # 图像参数
# IMG_SHAPE = (240, 320, 3)
# IMG_SIZE = np.prod(IMG_SHAPE)

# # 与开发板连接参数（IP 和端口必须与你开发板一致）
# HOST = '192.168.137.100'  # 或者 '127.0.0.1'，取决于你的实际连接
# PORT = 8090               # 视频流端口

# def recv_exact(sock, size):
#     """确保接收指定大小的字节"""
#     data = b''
#     while len(data) < size:
#         packet = sock.recv(size - len(data))
#         if not packet:
#             return None
#         data += packet
#     return data

# def main():
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.connect((HOST, PORT))
#     print(f"连接到开发板 {HOST}:{PORT}")

#     try:
#         while True:
#             raw_data = recv_exact(sock, IMG_SIZE)
#             if raw_data is None:
#                 print("接收失败或连接断开")
#                 break

#             img = np.frombuffer(raw_data, dtype=np.uint8).reshape(IMG_SHAPE)
#             cv2.imshow("开发板视频流", img)

#             # 按 'q' 退出
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break

#     except Exception as e:
#         print(f"发生异常: {e}")
#     finally:
#         sock.close()
#         cv2.destroyAllWindows()

# if __name__ == "__main__":
#     main()
