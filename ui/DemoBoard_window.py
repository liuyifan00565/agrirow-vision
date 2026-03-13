#DemoboardParameterWindow
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator
import os
from clientside.param import Parameter

class DemoBoardParameterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("开发板及视觉参数控制中心")
        self.setFixedSize(800, 700)
        self.main_window = parent


        self.is_modified = False
        
        self.setStyleSheet("""
        QDialog {
            background-color: #1E2736;
        }
        QLabel {
            color: #E0E0E0;
            font-family: 'Microsoft YaHei';
            font-size: 15px;
        }
        QPushButton {
            background-color: #1E88E5;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Microsoft YaHei';
            font-size: 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QLineEdit, QComboBox, QSpinBox, QCheckBox {
            background-color: #2E3B4E;
            color: #FFFFFF;
            border: 1px solid #3F4D63;
            padding: 5px;
            border-radius: 4px;
        }
        QComboBox QAbstractItemView {
            background-color: #2E3B4E;
            color: #FFFFFF;
            selection-background-color: #1E88E5;
            selection-color: white;
        }
""")

        self.inrow_param_filepath = os.path.abspath("inrow_param.txt")
        self.interrow_param_filepath = os.path.abspath("interrow_param.txt")
        
        self.inrow_parameter = Parameter(self.inrow_param_filepath)
        self.interrow_parameter = Parameter(self.interrow_param_filepath)
        
        self.load_parameters()
        self.init_ui()

    def _safe_split_list(self, raw):
        if isinstance(raw, list):
            return raw
        elif isinstance(raw, str):
            raw = raw.strip("[]")  # 清除[]括号
            raw = raw.replace("'", "").replace('"', '')  # 清除引号
            return [item.strip() for item in raw.split(',') if item.strip()]
        return []

    def load_parameters(self):
        self.params = {
            'system.device_name': self.interrow_parameter.get_param('system.device_name', 'HUAWEI Atlas 200I DK A2'),
            'system.model_list': self._safe_split_list(self.interrow_parameter.get_param('system.model_list', 'unet,unet++,yolo11_row')),
            'system.active_model': self.interrow_parameter.get_param('system.active_model', 'unet'),
            'system.type': self.interrow_parameter.get_param('system.type', 'interrow_weeder'),
            'system.active': self.interrow_parameter.get_param('system.active', False),
            'system.jp': self.interrow_parameter.get_param('system.jp', '192.168.137.100'),
            'system.video_tcp_port': int(self.interrow_parameter.get_param('system.video_tcp_port', 8090)),
            'system.instruction_tcp_port': int(self.interrow_parameter.get_param('system.instruction_tcp_port', 8091)),
            'system.video_stream': self.interrow_parameter.get_param('system.video_stream', 'camera'),
            'system.template_row_count': int(self.interrow_parameter.get_param('system.template_row_count', 3)),
            'system.param_file_name': self.interrow_parameter.get_param('system.param_file_name', 'interrow_param.txt')
        }

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("系统参数配置")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #FFFFFF; 
            padding-bottom: 15px;
            border-bottom: 3px solid #1E88E5;
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        # Device Name
        self.device_name_input = QLineEdit(self.params.get('system.device_name', ''))
        self.device_name_input.textChanged.connect(self.param_changed)
        form_layout.addRow("设备名称", self.device_name_input)

        # Model List
        self.model_list_widget = QListWidget()
        self.model_list_widget.addItems(self.params.get('system.model_list', []))
        add_model_btn = QPushButton("添加模型")
        add_model_btn.clicked.connect(self.add_model)
        del_model_btn = QPushButton("删除选中")
        del_model_btn.clicked.connect(self.del_model)
        model_btns = QHBoxLayout()
        model_btns.addWidget(add_model_btn)
        model_btns.addWidget(del_model_btn)
        model_group = QVBoxLayout()
        model_group.addWidget(QLabel("可用模型列表"))
        model_group.addWidget(self.model_list_widget)
        model_group.addLayout(model_btns)
        form_layout.addRow(model_group)

        # Active Model
        self.active_model_combo = QComboBox()
        # 确保在初始化时添加可用模型到下拉框
        if self.params.get('system.model_list', []):
            self.active_model_combo.addItems(self.params.get('system.model_list', []))
            # 设置当前选中的模型
            current_model = self.params.get('system.active_model', '')
            if current_model and current_model in self.params.get('system.model_list', []):
                self.active_model_combo.setCurrentText(current_model)
        self.active_model_combo.currentTextChanged.connect(self.param_changed)
        form_layout.addRow("当前工作模型", self.active_model_combo)

        # Weeder Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(['interrow_weeder', 'inrow_weeder'])
        self.type_combo.setCurrentText(self.params.get('system.type', ''))
        self.type_combo.currentTextChanged.connect(self.update_param_file)
        form_layout.addRow("除草机类型", self.type_combo)

        # System Active
        self.active_check = QCheckBox()
        self.active_check.setChecked(self.params.get('system.active', False))
        self.active_check.stateChanged.connect(self.param_changed)
        form_layout.addRow("系统工作状态", self.active_check)

        # IP Address
        ip_validator = QRegExpValidator(QRegExp(r'^(\d{1,3}\.){3}\d{1,3}$'))
        self.ip_input = QLineEdit(self.params.get('system.jp', ''))
        self.ip_input.setValidator(ip_validator)
        self.ip_input.textChanged.connect(self.param_changed)
        form_layout.addRow("边缘设备IP", self.ip_input)

        # Ports
        self.video_port_input = QSpinBox()
        self.video_port_input.setRange(0, 65535)
        self.video_port_input.setValue(self.params.get('system.video_tcp_port', 8090))
        self.video_port_input.valueChanged.connect(self.param_changed)
        form_layout.addRow("视频端口", self.video_port_input)

        self.instruction_port_input = QSpinBox()
        self.instruction_port_input.setRange(0, 65535)
        self.instruction_port_input.setValue(self.params.get('system.instruction_tcp_port', 8091))
        self.instruction_port_input.valueChanged.connect(self.param_changed)
        form_layout.addRow("指令端口", self.instruction_port_input)

        # Video Source
        self.video_source_combo = QComboBox()
        self.video_source_combo.addItems(['camera', 'video', 'mock'])
        self.video_source_combo.setCurrentText(self.params.get('system.video_stream', 'camera'))
        self.video_source_combo.currentTextChanged.connect(self.param_changed)
        form_layout.addRow("视频来源", self.video_source_combo)

        # Template Rows
        self.template_rows_input = QSpinBox()
        self.template_rows_input.setRange(1, 10)
        self.template_rows_input.setValue(self.params.get('system.template_row_count', 3))
        self.template_rows_input.valueChanged.connect(self.param_changed)
        form_layout.addRow("参考行数量", self.template_rows_input)

        # Param File
        self.param_file_combo = QComboBox()
        self.param_file_combo.addItems(['interrow_param.txt', 'inrow_param.txt'])
        self.param_file_combo.setCurrentText(self.params.get('system.param_file_name', 'interrow_param.txt'))
        self.param_file_combo.currentTextChanged.connect(self.param_changed)
        form_layout.addRow("参数文件", self.param_file_combo)

        layout.addLayout(form_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Save Button
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        buttons_layout.addWidget(save_btn)
        
        # Apply Button
        apply_btn = QPushButton("应用配置")
        apply_btn.clicked.connect(self.apply_config)
        buttons_layout.addWidget(apply_btn)
        
        layout.addLayout(buttons_layout)
        
        # Status indicator
        self.status_label = QLabel("状态: 未修改")
        self.status_label.setStyleSheet("color: #A0A0A0; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        
        # Load parameter file
        self.load_param_file()

    def add_model(self):
        model, ok = QInputDialog.getText(self, '添加模型', '输入模型名称:')
        if ok and model:
            # 添加到列表控件
            self.model_list_widget.addItem(model)
            
            # 更新下拉框
            self.active_model_combo.clear()  # 清空当前下拉框
            # 重新从列表控件获取所有项
            items = []
            for i in range(self.model_list_widget.count()):
                items.append(self.model_list_widget.item(i).text())
            self.active_model_combo.addItems(items)
            
            # 如果是第一个添加的模型，自动设为当前工作模型
            if self.model_list_widget.count() == 1:
                self.active_model_combo.setCurrentText(model)
                
            self.param_changed()

    def del_model(self):
        row = self.model_list_widget.currentRow()
        if row >= 0:
            item_text = self.model_list_widget.item(row).text()
            self.model_list_widget.takeItem(row)
            
            # 更新下拉框
            self.active_model_combo.clear()  # 清空当前下拉框
            # 重新从列表控件获取所有项
            items = []
            for i in range(self.model_list_widget.count()):
                items.append(self.model_list_widget.item(i).text())
            self.active_model_combo.addItems(items)
            
            self.param_changed()

    def update_param_file(self, text):
        new_file = f"{text.split('_')[0]}_param.txt"
        self.param_file_combo.setCurrentText(new_file)
        self.param_changed()
        self.load_param_file()

    def load_param_file(self):
        try:
            param_file = self.param_file_combo.currentText()
            if param_file == "inrow_param.txt":
                self.param_handler = self.inrow_parameter
            else:
                self.param_handler = self.interrow_parameter

            self.param_handler.load()

        # 重新加载模型列表
            raw_model_list = self.param_handler.get_param('system.model_list', '')
            model_list = self._safe_split_list(raw_model_list)

        # 更新列表控件
            self.model_list_widget.clear()
            self.model_list_widget.addItems(model_list)

        # 更新下拉框
            self.active_model_combo.clear()
            self.active_model_combo.addItems(model_list)

            active_model = self.param_handler.get_param('system.active_model', '')
            if active_model in model_list:
                self.active_model_combo.setCurrentText(active_model)

        except Exception as e:
            QMessageBox.warning(self, "警告", f"参数文件加载失败: {str(e)}")

    def param_changed(self):
        """标记参数已修改，但不立即保存"""
        self.is_modified = True
        self.status_label.setText("状态: 已修改（未保存）")
        self.status_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        
        # 更新内存中的参数
        self.update_params_in_memory()

    def update_params_in_memory(self):
        """更新内存中的参数，但不写入文件"""
        # 获取UI中的所有参数值
        self.params['system.device_name'] = self.device_name_input.text()
        
        model_list = []
        for i in range(self.model_list_widget.count()):
            model_list.append(self.model_list_widget.item(i).text())
        self.params['system.model_list'] = model_list
        
        self.params['system.active_model'] = self.active_model_combo.currentText()
        self.params['system.type'] = self.type_combo.currentText()
        self.params['system.active'] = self.active_check.isChecked()
        self.params['system.jp'] = self.ip_input.text()
        self.params['system.video_tcp_port'] = self.video_port_input.value()
        self.params['system.instruction_tcp_port'] = self.instruction_port_input.value()
        self.params['system.video_stream'] = self.video_source_combo.currentText()
        self.params['system.template_row_count'] = self.template_rows_input.value()
        self.params['system.param_file_name'] = self.param_file_combo.currentText()

    def save_config(self):
        if not self.main_window:
            QMessageBox.critical(self, "错误", "主窗口未绑定，无法保存配置"); return
        """将当前参数同时保存到 inrow_param.txt 和 interrow_param.txt"""
        try:
            # 更新两个参数文件的内容
            for param_handler in [self.inrow_parameter, self.interrow_parameter]:
                param_handler.set_param('system.device_name', self.device_name_input.text())
                
                model_list = []
                for i in range(self.model_list_widget.count()):
                    model_list.append(self.model_list_widget.item(i).text())
                param_handler.set_param('system.model_list', ",".join(model_list))
                
                param_handler.set_param('system.active_model', self.active_model_combo.currentText())
                param_handler.set_param('system.type', self.type_combo.currentText())
                param_handler.set_param('system.active', self.active_check.isChecked())
                param_handler.set_param('system.jp', self.ip_input.text())
                param_handler.set_param('system.video_tcp_port', self.video_port_input.value())
                param_handler.set_param('system.instruction_tcp_port', self.instruction_port_input.value())
                param_handler.set_param('system.video_stream', self.video_source_combo.currentText())
                param_handler.set_param('system.template_row_count', self.template_rows_input.value())
                
                # 为每个参数文件设置正确的文件名
                if param_handler == self.inrow_parameter:
                    param_handler.set_param('system.param_file_name', 'inrow_param.txt')
                else:
                    param_handler.set_param('system.param_file_name', 'interrow_param.txt')
                
                # 保存到文件
                param_handler.save()
            
            # 更新状态
            self.is_modified = False
            self.status_label.setText("状态: 已保存")
            self.status_label.setStyleSheet("color: #00FF00; font-size: 12px;")
            
            QMessageBox.information(
                self, "保存成功", 
                "参数已成功保存到 inrow_param.txt 和 interrow_param.txt"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存参数时出错: {str(e)}")

    def apply_config(self):
        """保存当前参数到当前选择的参数文件"""
        try:
            # 获取当前选择的参数文件和对应的处理器
            current_file = self.param_file_combo.currentText()
            if current_file == "inrow_param.txt":
                target_param = self.inrow_parameter
            else:
                target_param = self.interrow_parameter
            
            # 设置参数
            target_param.set_param('system.device_name', self.device_name_input.text())
            
            model_list = []
            for i in range(self.model_list_widget.count()):
                model_list.append(self.model_list_widget.item(i).text())
            target_param.set_param('system.model_list', ",".join(model_list))
            
            target_param.set_param('system.active_model', self.active_model_combo.currentText())
            target_param.set_param('system.type', self.type_combo.currentText())
            target_param.set_param('system.active', self.active_check.isChecked())
            target_param.set_param('system.jp', self.ip_input.text())
            target_param.set_param('system.video_tcp_port', self.video_port_input.value())
            target_param.set_param('system.instruction_tcp_port', self.instruction_port_input.value())
            target_param.set_param('system.video_stream', self.video_source_combo.currentText())
            target_param.set_param('system.template_row_count', self.template_rows_input.value())
            target_param.set_param('system.param_file_name', current_file)
            
            # 保存到文件
            target_param.save()
            
            # 更新状态
            self.is_modified = False
            self.status_label.setText("状态: 已保存")
            self.status_label.setStyleSheet("color: #00FF00; font-size: 12px;")
            
            QMessageBox.information(
                self, "保存成功", 
                f"参数已成功保存到 {current_file}\n"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"参数保存失败: {str(e)}")

    def closeEvent(self, event):
        try:
            if self.is_modified:
                reply = QMessageBox.question(
                    self, '未保存的更改', 
                    '您有未保存的更改，是否在关闭前保存？',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.save_config()
                    event.accept()
                elif reply == QMessageBox.No:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        except Exception as e:
            print(f"关闭窗口时发生错误: {str(e)}")
            event.accept()

    def fill_param_values(self):
        if not self.main_window:
            QMessageBox.critical(self, "错误", "主窗口未绑定，无法加载参数"); return
        params = self.main_window.get_clientio().load_params()
        self.device_name_input.setValue(int(params.get_param('system.device_name', 0)))
        self.active_model_combo.setCurrentText(str(params.get_param('system.active_model', '')))
        self.type_combo.setCurrentText(str(params.get_param('system.type', '')))
        self.active_check.setChecked(bool(params.get_param('system.active', False)))
        self.ip_input.setValue(int(params.get_param('system.jp', 0)))
        self.video_port_input.setValue(int(params.get_param('system.video_tcp_port', 0)))
        self.instruction_port_input.setValue(int(params.get_param('system.instruction_tcp_port', 0)))
        self.video_source_combo.setCurrentText(str(params.get_param('system.video_stream', '')))
        self.template_rows_input.setValue(int(params.get_param('system.template_row_count', 0)))
        self.param_file_combo.setCurrentText(str(params.get_param('system.param_file_name', '')))

    def get_param_values(self):
        new_params = Parameter()
        new_params.set_param('system.device_name', self.device_name_input.value())
        new_params.set_param('system.active_model', self.active_model_combo.currentText())
        new_params.set_param('system.type', self.type_combo.currentText())
        new_params.set_param('system.active', self.active_check.isChecked())
        new_params.set_param('system.jp', self.ip_input.value())
        new_params.set_param('system.video_tcp_port', self.video_port_input.value())
        new_params.set_param('system.instruction_tcp_port', self.instruction_port_input.value())
        new_params.set_param('system.video_stream', self.video_source_combo.currentText())
        new_params.set_param('system.template_row_count', self.template_rows_input.value())
        new_params.set_param('system.param_file_name', self.param_file_combo.currentText())
        return new_params

    def apply_parameters(self):
        if not self.main_window:
            QMessageBox.critical(self, "错误", "主窗口未绑定，无法保存参数"); return
        new_params = self.get_param_values()
        self.main_window.get_clientio().save_params(new_params)
        QMessageBox.information(self, "参数应用", "参数已成功应用。")
