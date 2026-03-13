基于计算机视觉和国产边缘设备的智能农机自动对行系统

(Computer Vision-Based Intelligent Crop Row Alignment System on Domestic Edge Devices)

<p align="center">




![系统架构](https://github.com/user-attachments/assets/a046adaf-4651-42a9-9841-e5b83bd1dff9)



https://github.com/user-attachments/assets/2e22ffdc-bad2-45f8-921a-3a1bee74ff53




</p>

本项目是一个 基于计算机视觉的农机自动对行系统，用于辅助农业机械在田间作业过程中识别作物行并保持精准对齐。

系统结合 深度学习、计算机视觉与工业控制技术，通过视觉检测作物行位置，计算农业机械的偏移量，并为控制系统提供调整依据，从而提升农业机械作业效率与精度。

📌 项目亮点

✨ 作物行视觉识别

使用 YOLO/Unet++ 深度学习模型检测作物行

适应复杂田间环境

✨ 正射（俯视）变换

将摄像头画面转换为俯视视角

提高作物行中心计算精度

✨ 实时偏移量计算

计算农机中心与作物行中心之间的偏移量

✨ 边缘设备部署

将模型部署在国产华为昇腾开发板

适用于农机车载计算设备

✨ 工业设备集成

支持 PLC通信

可接入农机控制系统

🎥 系统演示
系统界面

检测效果

🏗 系统架构
            摄像头输入
                │
                ▼
           视频帧采集
                │
                ▼
         正射变换（Bird-Eye）
                │
                ▼
           YOLO作物检测
                │
                ▼
           作物行中心提取
                │
                ▼
           偏移量计算
                │
                ▼
           PLC控制系统
📂 项目结构
Smart-Agri-Row-Alignment
│
├── YOLO/                     # YOLO模型相关代码与权重
│
├── clientside/               # 客户端通信模块
│
├── constant/                 # 系统常量定义
│
├── controller/               # 控制逻辑模块
│
├── design/                   # 系统设计相关文件
│
├── ortho_record/             # 正射变换与记录模块
│
├── service/                  # 系统服务层
│
├── ui/                       # PyQt界面组件
│
├── ui2/                      # 第二版UI界面
│
├── view/                     # UI视图模块
│
├── App.py                    # 系统主程序入口
│
├── new_App.py                # 新版本主程序
│
├── CropOffset.py             # 作物行偏移量计算
│
├── artui_ui.py               # UI界面代码
│
├── console_ui.py             # 控制台界面
│
├── demo_onePageui.py         # 单页面UI演示
│
├── demo_onePageui2.py        # 单页面UI演示版本2
│
├── demo_twoPageui.py         # 双页面UI演示
│
├── mainContral-onePageui.py  # 中控系统主界面
│
├── interrow_param.txt        # 行间参数配置
│
├── test_client_side.py       # 客户端测试模块
│
├── try2.py                   # 实验测试代码
│
└── README.md
⚙️ 安装方法
1 克隆项目
git clone https://github.com/YOUR_USERNAME/Smart-Agri-Row-Alignment.git

cd Smart-Agri-Row-Alignment
2 安装依赖
pip install -r requirements.txt

主要依赖：

ultralytics
opencv-python
numpy
pyqt5
torch
▶️ 运行系统
python main.py

系统运行流程：

1️⃣ 初始化摄像头
2️⃣ 启动视频处理
3️⃣ 使用 YOLO 进行作物检测
4️⃣ 计算作物行中心位置
5️⃣ 计算农机偏移量
6️⃣ 在界面显示检测结果

📊 图像处理流程
视频输入
   │
   ▼
视频帧提取
   │
   ▼
正射变换
   │
   ▼
YOLO检测
   │
   ▼
作物行中心提取
   │
   ▼
偏移量计算
   │
   ▼
控制系统输出
🌱 应用场景

自动驾驶农业机械

智能除草机器人

精准农业设备

农业机器人视觉系统

🚀 未来工作

多作物行检测优化

GPS + 视觉融合导航

边缘计算设备优化

基于强化学习的自动控制策略

👨‍💻 作者

Yifan Liu

AI产品经理 | 计算机视觉 | 智慧农业

滑铁卢大学
Electrical and Computer Engineering (MEng)

🤝 贡献

欢迎提交 Issue 或 Pull Request 改进项目。

⭐ 支持项目

如果这个项目对你有帮助，欢迎给项目点一个 Star ⭐

📜 开源协议

本项目基于 MIT License 开源。
