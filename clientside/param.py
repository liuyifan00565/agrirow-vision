import json
import os

"""
系统参数的管理类：
 * 读取系统参数文件
 * 保存系统参数文件
 * 获取系统参数
 * 设置系统参数
 * 将系统参数对象转换为json字符串，便于传输
 * 将json字符串转换为系统参数对象
"""
class Parameter:
    def __init__(self, param_filepath=None):
        self.param_filepath = param_filepath
        self.param_dict = {}

    def load(self):
        with open(self.param_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if len(line) == 0 or line.startswith('#'):  # 跳过注释行
                    continue
                if '=' not in line:
                    continue  # 跳过非法格式
                key, value = line.split('=', 1)  # 按第一个 = 分割
                self.param_dict[key.strip()] = value.strip()

    def save(self):
        with open(self.param_filepath, 'w', encoding='utf-8') as f:
            for key in sorted(self.param_dict):
                value = self.param_dict[key]
                print(f"{key}={value}")
                f.write(f"{key}={value}\n")

    def get_param(self, key, default=None):
        return self.param_dict.get(key, default)

    def set_param(self, key, value):
        self.param_dict[key] = value

    def merge_param(self, new_param):
        self.param_dict.update(new_param.param_dict)

    def to_json(self):
        return json.dumps(self.param_dict)

    def from_json(self, json_str):
        self.param_dict = json.loads(json_str)

if __name__ == '__main__':
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    print(current_dir)
    param = Parameter(os.path.join(current_dir, '..', 'inrow_param.txt'))
    param.load()
    print(param.get_param('camera.height', '200'))
    param.set_param('camera.height', '100')
    param.save()
    print(param.to_json())

    param2 = Parameter(os.path.join(current_dir, '..', 'inrow_param2.txt'))
    param2.from_json(param.to_json())
    print(param2.to_json())
