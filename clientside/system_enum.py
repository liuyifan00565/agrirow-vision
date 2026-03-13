from enum import Enum


IMG_WIDTH = 320
IMG_HEIGHT = 240


class MessageType(Enum):
    SYNC_PARAM = "sync_param"  # 同步参数
    SYNC_PARAM_RESP = "sync_param_resp" # 同步参数响应
    SWITCH_MODEL = "switch_model"  # 切换模型
    SWITCH_MODEL_RESP = "switch_model_resp"  # 切换模型响应
    START_MODEL = "start_model"  # 启动模型
    START_MODEL_RESP = "start_model_resp"  # 启动模型响应
    STOP_MODEL = "stop_model" # 停止模型
    STOP_MODEL_RESP = "stop_model_resp" # 停止模型响应
    SWITCH_SYSTEM = "switch_system" # 切换系统
    SWITCH_SYSTEM_RESP = "switch_system_resp" # 切换系统响应
    START_PLC = "start_plc" # 启动和PLC的通信
    START_PLC_RESP = "start_plc_resp" # 启动和PLC的通信响应
    STOP_PLC = "stop_plc" # 停止和PLC的通信
    STOP_PLC_RESP = "stop_plc_resp" # 停止和PLC的通信响应

    def __str__(self):
        return self.value

class ResponseType(Enum):
    SYNC_SUCCESS = "100" # 同步成功
    SYNC_FAILURE = "10" # 同步失败
    START_MODEL_SUCCESS = "200" # 启动模型成功
    START_MODEL_FAILURE = "20" # 启动模型失败
    STOP_MODEL_SUCCESS = "300" # 停止模型成功
    STOP_MODEL_FAILURE = "30"     # 停止模型失败
    SWITCH_MODEL_SUCCESS = "400"  # 切换模型成功
    SWITCH_MODEL_FAILURE = "40"   # 切换模型失败
    START_PLC_SUCCESS = "500" # 成功启动和PLC的通信
    START_PLC_FAILURE = "50" # 成功启动和PLC的通信
    STOP_PLC_SUCCESS = "600" # 成功停止和PLC的通信
    STOP_PLC_FAILURE = "60" # 成功停止和PLC的通信
    SWITCH_SYSTEM_SUCCESS = "666"  # 切换系统成功
    SWITCH_SYSTEM_FAILURE = "66"   # 切换系统失败


    def __str__(self):
        return self.value

class SystemType(Enum):
    INROW_WEEDER = "inrow_weeder" # 苗间系统
    INTERROW_WEEDER = "interrow_weeder" # 行间系统
    MOCK_WEEDER = "mock_weeder" # 模拟系统

    def __str__(self):
        return self.value
    

class VideoSourceType(Enum):
    CAMERA = "camera" # 相机
    VIDEO = "video" # 视频
    MOCK = "mock" # 模拟

    def __str__(self):
        return self.value