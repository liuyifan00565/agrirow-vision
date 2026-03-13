# coding:utf-8
'''
网络连接类
 * Protocol:socket,serial
 * Fuction:进行各种网络交互
'''
import socket

import numpy as np
from service import log_service as log

# 建立客户端(client)
def build_client(address):
    # 客户端
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(address)
        return client
    except Exception as e:
        log.info_msg(str(e),1)
        client.close()
        return None


# 接收图像(socket)
def recv_img(scokobj, length=230400, shape=[240, 320, 3]):
    # 完整数据包
    recv_data_whole = bytes()
    global img
    while True:
        # 接收数据
        recv_data = scokobj.recv(3000000)
        if len(recv_data) == 0:
            # 关闭链接
            scokobj.close()
            break
        else:
            # 拼接数据包
            recv_data_whole += recv_data
            if recv_data_whole.__len__() == length:
                # 720p RGB图像
                img = np.frombuffer(recv_data_whole, dtype=np.uint8).reshape(shape)
                # 回传信号
                scokobj.send("received!".encode("utf-8"))
                break
    return img


# 接收数据(socket)
def recv_data(scokobj):
    # 接收数据
    data = scokobj.recv(3000000).decode('utf-8')
    print(data)
    # 回传信号
    scokobj.send("received!".encode("utf-8"))
    return data


# 发送数据(socket)
def send_data(scokobj, data):
    scokobj.send(str(data[0]).encode('utf-8'))
    scokobj.recv(1024)
    scokobj.send(data[1].tobytes())
    scokobj.recv(1024)
