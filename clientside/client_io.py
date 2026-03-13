from clientside.message import Message,MessageType
from clientside.instruction_client import InstructionClient
from clientside.video_client import InrowVideoClient
from ui.interrow_video_client import InterrowVideoClient
from clientside.param import Parameter
from clientside.system_enum import MessageType,SystemType
import os

class IOClient:
    def __init__(self,server_ip,video_port,instruction_port,system_type):
        self.server_ip = server_ip
        self.video_port = video_port
        self.instruction_port = instruction_port
        self.system_type = system_type

        self.instruction_client = InstructionClient(server_ip,instruction_port)
        self.set_system_type(system_type)

    #调用此方法可切换客户端系统
    def set_system_type(self,system_type):
        self.system_type = system_type
        if system_type == SystemType.INTERROW_WEEDER.value:
            self.video_client = InterrowVideoClient(self.server_ip,self.video_port)
        else:  # inrow_weeder
            self.video_client = InrowVideoClient(self.server_ip,self.video_port)


    def send_instruction(self,instruction_msg):
        return self.instruction_client.send_instruction(instruction_msg)
    

    #加载当前所有参数
    def load_params(self):
        param_file_name = "inrow_param.txt"
        if self.system_type == 'interrow_weeder':
            param_file_name = "interrow_param.txt"
        current_file_path = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file_path)
        # print(current_dir)
        param = Parameter(current_dir+'\..\\'+param_file_name)
        param.load()
        return param
    
    # new_params用来收集需要更新的参数和参数值
    def save_params(self,new_params):
        params = self.load_params()
        params.merge_param(new_params)
        params.save()


  
    """
    中控系统客户端点击“同步参数”按钮调用此方法，把中控系统的参数同步至后端开发板
    这个方法的调用属于指令发送，把参数封装到消息里面，然后发送给后端开发板
    """
    def sync_params(self):
        params = self.load_params()
        param_json = params.to_json()
        msg = Message(MessageType.SYNC_PARAM)
        msg.set_content(param_json)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)

    """
    中控系统客户端点击“启动模型”按钮调用此方法。
    这个方法调用后，中控系统请求连接后端视频通信端口，后端接收请求后即启动视觉系统和视觉模型
    """
    def start_model(self):
        self.get_prediction()

    def get_prediction(self):
        self.video_client.get_predictions()

    """
    中控系统客户端点击“停止模型”按钮调用此方法，把中控系统的停止模型的指令发送至后端开发板
    这个方法的调用属于指令发送，把指令封装到消息里面，然后发送给后端开发板，后端把当前模型的状态设置为停止状态，模型随即停止工作
    """
    def stop_model(self):
        msg = Message(MessageType.STOP_MODEL)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)

    """
    中控系统客户端选择新的模型，点击“切换模型”按钮调用此方法，把中控系统的切换模型的指令发送至后端开发板
    这个方法的调用属于指令发送，把指令和新模型名称封装到消息里面，然后发送给后端开发板，
    后端把当前正在模型的状态设置为停止状态，模型随即停止工作，并且把当前活跃模型名称设置为新模型名称

    切换模型后新模型并不自动启动，需要点击“启动模型”按钮，启动新的模型
    """
    def switch_model(self, model_name):
        msg = Message(MessageType.SWITCH_MODEL)
        msg.set_content(model_name)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)


    """
    切换后端系统：
    中控系统客户端选择另一个视觉任务系统，点击“切换系统”按钮调用此方法，把中控系统的切换系统的指令发送至后端开发板
    这个方法的调用属于指令发送，把指令和新系统名称封装到消息里面，然后发送给后端开发板，
    后端把当前正在模型的状态设置为停止状态，模型随即停止工作，并且把新系统设置为当前活跃系统

    切换系统后，新系统的模型并不自动启动，需要点击“启动模型”按钮，启动新系统的模型
    """
    def switch_system(self,system_name):
        msg = Message(MessageType.SWITCH_SYSTEM)
        msg.set_content(system_name)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)


    #启动后端和plc的通信
    def start_plc(self):
        msg = Message(MessageType.START_PLC)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)
    
    #停止后端和plc的通信
    def stop_plc(self):
        msg = Message(MessageType.STOP_PLC)
        resp_msg = self.send_instruction(msg)
        print(resp_msg)

