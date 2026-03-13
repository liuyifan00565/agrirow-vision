# 用于控制设备模型切换的类
import requests

class ModelController:
    def __init__(self, device_urls):
        """
        :param device_urls: 设备地址字典
           {"device_1": "http://192.168.1.100:5000"}
        """
        self.devices = device_urls

    def switch_model(self, device_id, model_path):
        """切换指定设备的模型"""
        if device_id not in self.devices:
            raise ValueError(f"未知设备 {device_id}")
        
        url = f"{self.devices[device_id]}/switch_model"
        try:
            response = requests.post(
                url,
                json={"model_path": model_path},
                timeout=10  # 设置超时时间
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"通信失败: {str(e)}"}

    def batch_switch(self, model_path, device_ids=None):
        """批量切换设备模型"""
        results = {}
        target_devices = device_ids or self.devices.keys()
        
        for dev_id in target_devices:
            results[dev_id] = self.switch_model(dev_id, model_path)
        
        return results

# 使用示例
if __name__ == "__main__":
    # 初始化设备列表
    devices = {
        "lab_bench_1": "http://192.168.1.100:5000",
        "field_unit_2": "http://192.168.1.101:5000"
    }
    
    controller = ModelController(devices)
    
    # 切换单个设备
    print(controller.switch_model("lab_bench_1", "/models/resnet_v2.h5"))
    
    # 批量切换所有设备
    print(controller.batch_switch("/models/efficientnet_b0.h5"))