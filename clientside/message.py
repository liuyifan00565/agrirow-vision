import json
from clientside.system_enum import MessageType,ResponseType
from clientside.system_enum import SystemType

class Message:
    def __init__(self, type : MessageType = None, msg_json: str = None):
        if type is not None:
            self.msg_dict = {'type': type.value}
        elif msg_json is not None:
            self.msg_dict = json.loads(msg_json)
        else:
            raise ValueError("Either type_enum or msg_json_str must be provided.")


    def set_type(self, type):
        self.msg_dict['type'] = type.value

    def set_content(self, content):
        self.msg_dict['content'] = content



    def __str__(self):
        return json.dumps(self.msg_dict)  
    
    def get_type(self):
        return MessageType(self.msg_dict['type'])

    def get_content(self):
        return self.msg_dict['content']
    

if __name__ == '__main__':
    # msg_json = '{"type":"sync_param","content":{"height":"100","angle":"30"}}'
    # msg = Message(msg_json=msg_json)
    # print(type(MessageType.SYNC_PARAM))
    # print(MessageType.SYNC_PARAM.name)
    # if msg.get_type() == MessageType.SYNC_PARAM:
    #     print(msg.get_content())
    # print(msg)

    # msg=Message(type=MessageType.START_MODEL)
    # msg.set_content("")
    # print(msg)
    msg=Message(type=MessageType.SYNC_PARAM_RESP)
    msg.set_content(ResponseType.SYNC_SUCCESS.value)
    print(msg)
    msg_json='{"type": "sync_param_resp", "content": "100"}'
    msg2=Message(msg_json=msg_json)
    print(msg2)