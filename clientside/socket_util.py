import numpy as np
from clientside.predictions import Predictions
from clientside.system_enum import SystemType
from clientside import system_enum
width = system_enum.IMG_WIDTH
height = system_enum.IMG_HEIGHT


class SocketUtil:
    def send_txt(conn,txt):
        data_str = txt
        data = data_str.encode('utf-8')
        data_length = len(data)
        conn.sendall(data_length.to_bytes(8, byteorder='big'))  # 使用 8 字节表示数据长度
        total_sent = 0
        while total_sent < data_length:
            sent = conn.send(data[total_sent:total_sent + 1024])  # 每次发送最多 1024 字节
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            total_sent += sent
        # print(f"Sent {total_sent} bytes of data")



    def recv_txt(conn):
        # 接收数据长度（前 8 字节）
        data_length_bytes = conn.recv(8)
        data_length = int.from_bytes(data_length_bytes, byteorder='big')
        # print(f"Expecting {data_length} bytes of data")

        # 循环接收数据
        received_data = b""
        while len(received_data) < data_length:
            chunk = conn.recv(min(1024, data_length - len(received_data)))  # 每次最多接收 1024 字节
            if not chunk:
                raise RuntimeError("Socket connection broken")
            received_data += chunk
        # print(f"Received {len(received_data)} bytes of data")

        # 解码并打印接收到的数据
        return received_data.decode('utf-8')
    

    def send_img(conn,img):
        data = img.tobytes()
        data_length = len(data)
        conn.sendall(data_length.to_bytes(8, byteorder='big'))  # 使用 8 字节表示数据长度
        total_sent = 0
        while total_sent < data_length:
            sent = conn.send(data[total_sent:total_sent + 1024])  # 每次发送最多 1024 字节
            total_sent += sent
    

    def recv_img(conn):
        # 接收数据长度（前 8 字节）
        data_length_bytes = conn.recv(8)
        data_length = int.from_bytes(data_length_bytes, byteorder='big')
        # print(f"Expecting {data_length} bytes of data")
        # 循环接收数据
        received_data = b""
        while len(received_data) < data_length:
            chunk = conn.recv(min(1024, data_length - len(received_data)))  # 每次最多接收 1024 字节
            if not chunk:
                raise RuntimeError("Socket connection broken")
            received_data += chunk
        # print(f"Received {len(received_data)} bytes of data")
        return np.frombuffer(received_data, dtype=np.uint8)
    

    """
    prediction的类型是Predictions
    """
    def send_prediction(conn,prediction):
        pred_str = prediction.pred_to_str()
        SocketUtil.send_txt(conn,pred_str)
        pred_img = prediction.get_frame()
        SocketUtil.send_img(conn,pred_img)
    
    """
    返回值的类型是Predictions
    """
    # def recv_prediction(conn,shape=[240, 320, 3]):
    def recv_prediction(conn,shape=[height, width, 3]):
        pred_str = SocketUtil.recv_txt(conn)
        pred_img = SocketUtil.recv_img(conn)
        predictions = Predictions()
        if len(pred_str) == 0:
            predictions.set_flag(False)
        else:
            predictions.set_flag(True)
            predictions.str_to_pred(pred_str)
            # pred_img2 = pred_img.reshape(shape)
            # predictions.set_frame(pred_img2)
            predictions.set_frame(pred_img)
        return predictions