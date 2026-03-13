import json
class Predictions:
    def __init__(self,type = None,flag = True):

        """
        键值对定义：
        flag： True|False  是否有预测结果，True为有，False为无
        type： interrow_weeder|inrow_weeder  预测结果类型，interrow_weeder为行间除草，inrow_weeder为苗间除草
        row_bias: int  行间除草系统的苗行偏移结果，是个整数，正负零均有可能，单位为厘米
        crop_bias: list  苗间除草系统的作物与刀具偏移结果,全是整数，正负零均有可能，单位为厘米
                    作物与刀具偏移距离:三行苗，每一行苗离刀具最近的三颗苗与刀具的距离
                    形式为:
                    [[0,0,0],[0,0,0],[0,0,0]]
        """
        self.pred_dict= {'type':type,'flag':flag}
        """
        叠加预测结果的图像（视频帧）
        对行间除草，就是叠加苗行线；对苗间除草，就是叠加矩形检测框
        """
        self.frame = None

    #转换成json后便于传输
    def pred_to_str(self):
        return json.dumps(self.pred_dict)

    #接收到json字符串后恢复预测结果
    def str_to_pred(self,pred_str):
        self.pred_dict = json.loads(pred_str)
    
    def get_type(self):
        return self.pred_dict['type']

    def get_flag(self):
        return self.pred_dict['flag']
    
    def get_row_bias(self):
        return self.pred_dict['row_bias']
    
    def get_crop_bias(self):
        return self.pred_dict['crop_bias']
    
    def set_type(self,type):
        self.pred_dict['type'] = type

    def set_flag(self,flag):
        self.pred_dict['flag'] = flag

    def set_row_bias(self,row_bias):
        self.pred_dict['row_bias'] = row_bias
        
    def set_crop_bias(self,crop_bias):
        self.pred_dict['crop_bias'] = crop_bias


    def set_frame(self,frame):
        cpframe = frame.copy()
        # self.pred_dict['width'] = shape[1] 
        # self.pred_dict['height'] = shape[0] 
        frame_size = self.get_frame_size()
        self.frame = cpframe.reshape((frame_size[0], frame_size[1], 3)).copy()
    
    def get_frame_size(self):
        return (int(self.pred_dict['height']),int(self.pred_dict['width']))

    def get_frame(self):
        return self.frame