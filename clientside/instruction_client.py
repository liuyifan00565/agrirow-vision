import socket
from clientside.message import Message
from clientside.socket_util import SocketUtil


class InstructionClient:
    def __init__(self,server_ip,instruction_port):
        self.server_ip = server_ip
        self.instruction_port = instruction_port

    
    def send_instruction(self,instruction_msg):
        # print("向服务端发送指令数据：",str(instruction_msg))
        txt = str(instruction_msg)

        resp_msg = None
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with client_socket:
            client_socket.connect((self.server_ip, self.instruction_port))
            # self.send_txt(client_socket,txt)
            SocketUtil.send_txt(client_socket,txt)  

            # 接收反馈
            # result_txt = self.recv_txt(client_socket)
            result_txt = SocketUtil.recv_txt(client_socket)

        resp_msg = Message(msg_json=result_txt)
        # print("接收到服务端反馈：",resp_msg)
        return resp_msg

