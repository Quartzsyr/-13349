#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import json
import os
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QPushButton, QTextEdit, QLineEdit, 
                            QGroupBox, QGridLayout, QCheckBox, QSpinBox, QSplitter, 
                            QMenuBar, QMenu, QAction, QDialog, QTabWidget, QFormLayout,
                            QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QScrollArea)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt, QSettings, QRectF
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen


class GaugeWidget(QWidget):
    """仪表盘控件"""
    def __init__(self, title, unit, min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.current_value = min_val

        self.setMinimumSize(160, 160)

    def setValue(self, value):
        if self.min_val <= value <= self.max_val:
            self.current_value = value
        elif value < self.min_val:
            self.current_value = self.min_val
        else:
            self.current_value = self.max_val
        self.update()  # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # 绘制标题
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Microsoft YaHei", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(-100, -95, 200, 30), Qt.AlignCenter, self.title)

        # 绘制仪表盘背景
        painter.setPen(QPen(QColor(220, 220, 220), 15))
        painter.drawArc(QRectF(-70, -60, 140, 140), -45 * 16, 270 * 16)

        # 绘制当前值
        pen = QPen(QColor(90, 155, 213), 15)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        angle_range = 270.0
        value_range = self.max_val - self.min_val if self.max_val - self.min_val != 0 else 1
        
        span_angle = (self.current_value - self.min_val) / value_range * angle_range
        painter.drawArc(QRectF(-70, -60, 140, 140), -45 * 16, int(span_angle) * 16)
        
        # 绘制中心文本
        painter.setPen(QColor(0, 0, 0))
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-100, -20, 200, 40), Qt.AlignCenter, f"{self.current_value:.1f}")

        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(-100, 20, 200, 30), Qt.AlignCenter, self.unit)


class SerialThread(QThread):
    """串口数据接收线程"""
    received = pyqtSignal(bytes)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.is_running = True

    def run(self):
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.received.emit(data)
            except Exception as e:
                print(f"串口读取错误: {e}")
                break
            time.sleep(0.01)  # 小延迟避免CPU占用过高

    def stop(self):
        self.is_running = False
        self.wait()


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None, cmd_buttons=None, data_format=None):
        super().__init__(parent)
        self.parent = parent
        self.cmd_buttons = cmd_buttons.copy() if cmd_buttons else {}
        self.data_format = data_format.copy() if data_format else {}
        
        self.setWindowTitle("设置")
        self.resize(600, 400)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.cmd_tab = QWidget()
        self.format_tab = QWidget()
        
        self.tabs.addTab(self.cmd_tab, "快捷指令")
        self.tabs.addTab(self.format_tab, "数据解析")
        
        # 初始化标签页内容
        self.init_cmd_tab()
        self.init_format_tab()
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def init_cmd_tab(self):
        """初始化快捷指令标签页"""
        layout = QVBoxLayout()
        
        # 指令表格
        self.cmd_table = QTableWidget(0, 2)
        self.cmd_table.setHorizontalHeaderLabels(["按钮名称", "发送内容"])
        self.cmd_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加现有的指令
        for name, cmd in self.cmd_buttons.items():
            row = self.cmd_table.rowCount()
            self.cmd_table.insertRow(row)
            self.cmd_table.setItem(row, 0, QTableWidgetItem(name))
            self.cmd_table.setItem(row, 1, QTableWidgetItem(cmd))
        
        layout.addWidget(self.cmd_table)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_cmd_row)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.del_cmd_row)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.cmd_tab.setLayout(layout)
    
    def init_format_tab(self):
        """初始化数据解析标签页"""
        layout = QVBoxLayout()
        
        # 说明标签
        layout.addWidget(QLabel("设置数据解析格式，定义如何从接收数据中提取传感器值"))
        layout.addWidget(QLabel("示例: T:25.5,H:60.2,L:1200 - 使用 'T', 'H', 'L' 作为键名"))
        
        # 解析格式表格
        self.format_table = QTableWidget(0, 3)
        self.format_table.setHorizontalHeaderLabels(["传感器名称", "键名", "单位"])
        self.format_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加现有的格式
        for name, info in self.data_format.items():
            row = self.format_table.rowCount()
            self.format_table.insertRow(row)
            self.format_table.setItem(row, 0, QTableWidgetItem(name))
            self.format_table.setItem(row, 1, QTableWidgetItem(info.get('key', '')))
            self.format_table.setItem(row, 2, QTableWidgetItem(info.get('unit', '')))
        
        layout.addWidget(self.format_table)
        
        # 分隔符设置
        separator_layout = QHBoxLayout()
        separator_layout.addWidget(QLabel("数据项分隔符:"))
        self.separator_edit = QLineEdit()
        self.separator_edit.setText(self.parent.data_separator if hasattr(self.parent, 'data_separator') else ",")
        separator_layout.addWidget(self.separator_edit)
        
        separator_layout.addWidget(QLabel("键值分隔符:"))
        self.kv_separator_edit = QLineEdit()
        self.kv_separator_edit.setText(self.parent.kv_separator if hasattr(self.parent, 'kv_separator') else ":")
        separator_layout.addWidget(self.kv_separator_edit)
        layout.addLayout(separator_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_format_row)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.del_format_row)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.format_tab.setLayout(layout)
    
    def add_cmd_row(self):
        """添加快捷指令行"""
        row = self.cmd_table.rowCount()
        self.cmd_table.insertRow(row)
        self.cmd_table.setItem(row, 0, QTableWidgetItem(f"按钮{row+1}"))
        self.cmd_table.setItem(row, 1, QTableWidgetItem(f"CMD:{row+1}"))
    
    def del_cmd_row(self):
        """删除快捷指令行"""
        current_row = self.cmd_table.currentRow()
        if current_row >= 0:
            self.cmd_table.removeRow(current_row)
    
    def add_format_row(self):
        """添加数据格式行"""
        row = self.format_table.rowCount()
        self.format_table.insertRow(row)
        self.format_table.setItem(row, 0, QTableWidgetItem(f"传感器{row+1}"))
        self.format_table.setItem(row, 1, QTableWidgetItem(f"KEY{row+1}"))
        self.format_table.setItem(row, 2, QTableWidgetItem(""))
    
    def del_format_row(self):
        """删除数据格式行"""
        current_row = self.format_table.currentRow()
        if current_row >= 0:
            self.format_table.removeRow(current_row)
    
    def get_cmd_buttons(self):
        """获取快捷指令按钮设置"""
        cmd_buttons = {}
        for row in range(self.cmd_table.rowCount()):
            name = self.cmd_table.item(row, 0).text().strip()
            cmd = self.cmd_table.item(row, 1).text().strip()
            if name and cmd:
                cmd_buttons[name] = cmd
        return cmd_buttons
    
    def get_data_format(self):
        """获取数据解析格式设置"""
        data_format = {}
        for row in range(self.format_table.rowCount()):
            name = self.format_table.item(row, 0).text().strip()
            key = self.format_table.item(row, 1).text().strip()
            unit = self.format_table.item(row, 2).text().strip()
            if name and key:
                data_format[name] = {'key': key, 'unit': unit}
        return data_format
    
    def get_separators(self):
        """获取分隔符设置"""
        return self.separator_edit.text(), self.kv_separator_edit.text()


class SerialAssistant(QMainWindow):
    """串口助手主窗口"""
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.serial_thread = None
        
        # 默认配置
        self.cmd_buttons = {
            '前进': 'CMD:FWD',
            '后退': 'CMD:BWD',
            '左转': 'CMD:LEFT',
            '右转': 'CMD:RIGHT',
            '停止': 'CMD:STOP',
            '自动模式': 'CMD:AUTO',
            '手动模式': 'CMD:MANUAL',
        }
        
        self.data_format = {
            '温度': {'key': 'T', 'unit': '℃', 'min': 0, 'max': 50},
            '湿度': {'key': 'H', 'unit': '%', 'min': 0, 'max': 100},
            '光照': {'key': 'L', 'unit': 'lux', 'min': 0, 'max': 2000},
            '土壤湿度': {'key': 'SM', 'unit': '%', 'min': 0, 'max': 100},
            '电池电量': {'key': 'BAT', 'unit': 'V', 'min': 3.0, 'max': 4.2},
            '太阳能电压': {'key': 'SOL', 'unit': 'V', 'min': 0, 'max': 6},
            '行进速度': {'key': 'SPD', 'unit': 'cm/s', 'min': 0, 'max': 50},
            '当前状态': {'key': 'ST', 'unit': ''}, # '当前状态' 作为特殊文本处理
        }
        
        self.data_separator = ","  # 数据项分隔符
        self.kv_separator = ":"    # 键值分隔符
        
        # 加载设置
        self.load_settings()
        
        # 初始化UI
        self.init_ui()
        self.refresh_ports()
        
        # 定时刷新串口列表
        self.port_timer = QTimer(self)
        self.port_timer.timeout.connect(self.refresh_ports)
        self.port_timer.start(5000)  # 每5秒刷新一次串口列表
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('太阳能植物监护小车串口助手')
        self.setMinimumSize(800, 600)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 主部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 上方串口控制区域
        port_control_group = QGroupBox('串口设置')
        port_control_layout = QHBoxLayout()
        port_control_group.setLayout(port_control_layout)
        
        # 串口选择
        port_control_layout.addWidget(QLabel('串口:'))
        self.port_combo = QComboBox()
        port_control_layout.addWidget(self.port_combo)
        
        # 波特率选择
        port_control_layout.addWidget(QLabel('波特率:'))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('115200')
        port_control_layout.addWidget(self.baud_combo)
        
        # 数据位
        port_control_layout.addWidget(QLabel('数据位:'))
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(['5', '6', '7', '8'])
        self.data_bits_combo.setCurrentText('8')
        port_control_layout.addWidget(self.data_bits_combo)
        
        # 停止位
        port_control_layout.addWidget(QLabel('停止位:'))
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(['1', '1.5', '2'])
        port_control_layout.addWidget(self.stop_bits_combo)
        
        # 校验位
        port_control_layout.addWidget(QLabel('校验位:'))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(['无', '奇校验', '偶校验'])
        port_control_layout.addWidget(self.parity_combo)
        
        # 控制按钮
        self.connect_btn = QPushButton('打开串口')
        self.connect_btn.clicked.connect(self.toggle_connection)
        port_control_layout.addWidget(self.connect_btn)
        
        self.refresh_btn = QPushButton('刷新')
        self.refresh_btn.clicked.connect(self.refresh_ports)
        port_control_layout.addWidget(self.refresh_btn)
        
        main_layout.addWidget(port_control_group)
        
        # 中间部分为左右分栏
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # --- 左侧: 数据收发 ---
        left_widget_scroll = QScrollArea()
        left_widget_scroll.setWidgetResizable(True)
        left_widget_scroll.setFrameShape(QScrollArea.NoFrame)
        splitter.addWidget(left_widget_scroll)

        left_widget = QWidget()
        data_layout = QVBoxLayout(left_widget)
        left_widget_scroll.setWidget(left_widget)
        
        # 接收区
        receive_group = QGroupBox('数据接收')
        receive_layout = QVBoxLayout(receive_group)
        
        receive_control_layout = QHBoxLayout()
        self.hex_display = QCheckBox('HEX显示')
        receive_control_layout.addWidget(self.hex_display)
        
        self.auto_scroll = QCheckBox('自动滚动')
        self.auto_scroll.setChecked(True)
        receive_control_layout.addWidget(self.auto_scroll)
        
        self.clear_receive_btn = QPushButton('清空接收')
        self.clear_receive_btn.clicked.connect(self.clear_receive)
        receive_control_layout.addWidget(self.clear_receive_btn)
        receive_control_layout.addStretch(1)
        receive_layout.addLayout(receive_control_layout)
        
        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        receive_layout.addWidget(self.receive_text)
        
        data_layout.addWidget(receive_group)
        
        # 发送区
        send_group = QGroupBox('数据发送')
        send_layout = QVBoxLayout(send_group)
        
        send_control_layout = QHBoxLayout()
        self.hex_send = QCheckBox('HEX发送')
        send_control_layout.addWidget(self.hex_send)
        
        send_control_layout.addWidget(QLabel('循环发送间隔(ms):'))
        self.send_interval = QSpinBox()
        self.send_interval.setRange(10, 10000)
        self.send_interval.setValue(1000)
        send_control_layout.addWidget(self.send_interval)
        
        self.auto_send = QCheckBox('循环发送')
        self.auto_send.setChecked(False)
        self.auto_send.stateChanged.connect(self.toggle_auto_send)
        send_control_layout.addWidget(self.auto_send)
        
        self.clear_send_btn = QPushButton('清空发送')
        self.clear_send_btn.clicked.connect(self.clear_send)
        send_control_layout.addWidget(self.clear_send_btn)
        send_control_layout.addStretch(1)
        send_layout.addLayout(send_control_layout)
        
        data_layout.addWidget(send_group)
        
        # 发送文本框和快捷指令移到发送组框外面
        self.send_text = QTextEdit()
        data_layout.addWidget(self.send_text)

        # 快捷指令区
        quick_cmd_group = QGroupBox('快捷指令')
        self.quick_cmd_layout = QGridLayout(quick_cmd_group)
        data_layout.addWidget(quick_cmd_group)
        self.update_cmd_buttons()

        # 发送按钮
        self.send_btn = QPushButton('发送')
        self.send_btn.clicked.connect(self.send_data)
        data_layout.addWidget(self.send_btn, 0, Qt.AlignRight)

        # --- 右侧: 传感器数据 ---
        right_widget_scroll = QScrollArea()
        right_widget_scroll.setWidgetResizable(True)
        right_widget_scroll.setFrameShape(QScrollArea.NoFrame)
        splitter.addWidget(right_widget_scroll)

        right_widget = QWidget()
        self.sensor_layout = QVBoxLayout(right_widget)
        right_widget_scroll.setWidget(right_widget)
        
        # 传感器数据显示组
        self.sensor_group = QGroupBox('传感器数据')
        self.sensor_layout.addWidget(self.sensor_group)
        self.sensor_layout.addStretch(1)
        
        # 传感器数据项
        self.sensor_fields = {}
        self.update_sensor_fields()
        
        # 设置分隔器比例和大小
        splitter.setStretchFactor(0, 1) # 左侧拉伸因子
        splitter.setStretchFactor(1, 2) # 右侧拉伸因子，给仪表盘更多空间
        splitter.setSizes([400, 800])   # 初始大小
        
        # 自动发送定时器
        self.send_timer = QTimer(self)
        self.send_timer.timeout.connect(self.send_data)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        save_settings_action = QAction('保存设置', self)
        save_settings_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_settings_action)
        
        load_settings_action = QAction('加载设置', self)
        load_settings_action.triggered.connect(self.load_settings_from_file)
        file_menu.addAction(load_settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        cmd_settings_action = QAction('快捷指令和数据格式', self)
        cmd_settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(cmd_settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def update_sensor_fields(self):
        """更新传感器字段为仪表盘"""
        self.sensor_fields = {}

        # 获取或创建传感器组的网格布局
        layout = self.sensor_group.layout()
        if layout is not None:
            # 如果布局已存在，清空其所有小部件
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        else:
            layout = QGridLayout()
            self.sensor_group.setLayout(layout)

        # 添加新的传感器小部件（仪表盘或文本）到网格布局
        row, col = 0, 0
        for name, info in self.data_format.items():
            if name == '当前状态':
                # 为状态创建特殊的文本显示
                status_widget = QWidget()
                status_layout = QVBoxLayout(status_widget)
                status_layout.setContentsMargins(10, 10, 10, 10)
                status_layout.setAlignment(Qt.AlignCenter)

                title_label = QLabel(name)
                title_label.setAlignment(Qt.AlignCenter)
                title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))

                value_label = QLineEdit("待机")
                value_label.setReadOnly(True)
                value_label.setAlignment(Qt.AlignCenter)
                value_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
                value_label.setStyleSheet("background-color: transparent; border: none;")

                status_layout.addWidget(title_label)
                status_layout.addWidget(value_label)

                self.sensor_fields[name] = value_label
                layout.addWidget(status_widget, row, col)
            else:
                # 为其他传感器创建仪表盘
                unit = info.get('unit', '')
                min_val = info.get('min', 0)
                max_val = info.get('max', 100)
                
                gauge = GaugeWidget(name, unit, min_val, max_val)
                self.sensor_fields[name] = gauge
                layout.addWidget(gauge, row, col)

            col += 1
            if col > 3:  # 每行最多4个小部件
                col = 0
                row += 1
    
    def update_cmd_buttons(self):
        """更新快捷指令按钮"""
        # 清除旧的按钮
        while self.quick_cmd_layout.count():
            item = self.quick_cmd_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新的按钮到网格布局
        buttons = list(self.cmd_buttons.items())
        cols = 4  # 每行4个按钮
        for i, (name, cmd) in enumerate(buttons):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=cmd: self.send_quick_command(c))
            row = i // cols
            col = i % cols
            self.quick_cmd_layout.addWidget(btn, row, col)
    
    def refresh_ports(self):
        """刷新可用的串口列表"""
        current_port = self.port_combo.currentText()
        
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.addItems(ports)
        
        # 尝试保持之前选择的串口
        if current_port and current_port in ports:
            self.port_combo.setCurrentText(current_port)
            
        if not ports:
            self.port_combo.addItem('无可用串口')
    
    def toggle_connection(self):
        """切换串口连接状态"""
        if self.serial_port and self.serial_port.is_open:
            self.disconnect_port()
        else:
            self.connect_port()
    
    def connect_port(self):
        """连接串口"""
        port_name = self.port_combo.currentText()
        if not port_name or port_name == '无可用串口':
            self.receive_text.append('没有可用的串口')
            return
            
        try:
            # 获取校验位设置
            parity_map = {'无': serial.PARITY_NONE, '奇校验': serial.PARITY_ODD, '偶校验': serial.PARITY_EVEN}
            parity = parity_map[self.parity_combo.currentText()]
            
            # 获取停止位设置
            stop_bits_map = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO}
            stop_bits = stop_bits_map[self.stop_bits_combo.currentText()]
            
            # 打开串口
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=int(self.baud_combo.currentText()),
                bytesize=int(self.data_bits_combo.currentText()),
                parity=parity,
                stopbits=stop_bits,
                timeout=0.1
            )
            
            if self.serial_port.is_open:
                self.connect_btn.setText('关闭串口')
                self.receive_text.append(f'已连接到 {port_name}')
                
                # 启动接收线程
                self.serial_thread = SerialThread(self.serial_port)
                self.serial_thread.received.connect(self.handle_received_data)
                self.serial_thread.start()
        except Exception as e:
            self.receive_text.append(f'连接失败: {str(e)}')
    
    def disconnect_port(self):
        """断开串口连接"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
            
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.connect_btn.setText('打开串口')
            self.receive_text.append('串口已关闭')
    
    def handle_received_data(self, data):
        """处理接收到的数据"""
        if self.hex_display.isChecked():
            # 十六进制显示
            hex_str = ' '.join([f"{byte:02X}" for byte in data])
            self.receive_text.append(f"接收: {hex_str}")
        else:
            # 尝试解码为UTF-8文本
            try:
                text = data.decode('utf-8')
                self.receive_text.append(f"接收: {text}")
            except UnicodeDecodeError:
                # 解码失败时显示十六进制
                hex_str = ' '.join([f"{byte:02X}" for byte in data])
                self.receive_text.append(f"接收(HEX): {hex_str}")
        
        # 解析传感器数据
        self.parse_sensor_data(data)
        
        # 自动滚动
        if self.auto_scroll.isChecked():
            self.receive_text.verticalScrollBar().setValue(
                self.receive_text.verticalScrollBar().maximum()
            )
    
    def parse_sensor_data(self, data):
        """解析传感器数据并更新UI"""
        try:
            # 尝试解码为UTF-8文本
            text = data.decode('utf-8').strip()
            
            # 数据格式判断与解析
            items = text.split(self.data_separator)
            data_map = {}
            
            for item in items:
                if self.kv_separator in item:
                    key, value = item.split(self.kv_separator, 1)
                    data_map[key.strip()] = value.strip()
            
            # 更新传感器字段
            for name, info in self.data_format.items():
                key = info.get('key', '')
                
                if key in data_map:
                    value_str = data_map[key]
                    
                    if name == '当前状态':
                        status_map = {
                            '0': '待机',
                            '1': '自动监控',
                            '2': '手动控制',
                            '3': '充电中',
                            '4': '报警'
                        }
                        display_text = status_map.get(value_str, value_str)
                        if name in self.sensor_fields:
                            self.sensor_fields[name].setText(display_text)
                    else:
                        # 更新仪表盘
                        try:
                            value_float = float(value_str)
                            if name in self.sensor_fields:
                                self.sensor_fields[name].setValue(value_float)
                        except ValueError:
                            print(f"无法将 '{value_str}' 转换为数值用于仪表盘 '{name}'")
        except Exception as e:
            print(f"解析数据错误: {e}")
    
    def send_data(self):
        """发送数据"""
        if not self.serial_port or not self.serial_port.is_open:
            self.receive_text.append('串口未打开，无法发送数据')
            return
            
        text = self.send_text.toPlainText().strip()
        if not text:
            return
            
        try:
            if self.hex_send.isChecked():
                # 十六进制发送
                # 移除所有空格和换行符
                text = text.replace(' ', '').replace('\n', '')
                # 确保字符数量是偶数
                if len(text) % 2 != 0:
                    text = text + '0'
                # 转换为字节序列
                data = bytes.fromhex(text)
            else:
                # 文本发送
                data = text.encode('utf-8')
                
            self.serial_port.write(data)
            
            # 显示发送的数据
            if self.hex_send.isChecked():
                hex_str = ' '.join([f"{byte:02X}" for byte in data])
                self.receive_text.append(f"发送: {hex_str}")
            else:
                self.receive_text.append(f"发送: {text}")
                
            # 自动滚动
            if self.auto_scroll.isChecked():
                self.receive_text.verticalScrollBar().setValue(
                    self.receive_text.verticalScrollBar().maximum()
                )
        except Exception as e:
            self.receive_text.append(f'发送失败: {str(e)}')
    
    def send_quick_command(self, command):
        """发送快捷指令"""
        self.send_text.setText(command)
        self.send_data()
    
    def toggle_auto_send(self, state):
        """切换自动发送状态"""
        if state:
            interval = self.send_interval.value()
            self.send_timer.start(interval)
        else:
            self.send_timer.stop()
    
    def clear_receive(self):
        """清空接收区"""
        self.receive_text.clear()
    
    def clear_send(self):
        """清空发送区"""
        self.send_text.clear()
    
    def open_settings_dialog(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self, self.cmd_buttons, self.data_format)
        if dialog.exec_() == QDialog.Accepted:
            # 更新快捷指令
            self.cmd_buttons = dialog.get_cmd_buttons()
            self.update_cmd_buttons()
            
            # 更新数据格式
            new_data_format = dialog.get_data_format()
            original_data_format = self.data_format.copy()

            # 如果新的数据格式为空，但之前不为空，则提示用户确认
            if not new_data_format and original_data_format:
                reply = QMessageBox.question(self, '确认清空',
                                             "您已清空所有传感器数据解析设置。确认保存这些更改吗？选择'否'将恢复之前的设置。",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    self.data_format = original_data_format # 恢复旧的设置
                    self.data_separator, self.kv_separator = dialog.get_separators() # 分隔符可以更新
                else:
                    self.data_format = new_data_format # 用户确认清空
                    self.data_separator, self.kv_separator = dialog.get_separators()
            else:
                self.data_format = new_data_format
                self.data_separator, self.kv_separator = dialog.get_separators()

            self.update_sensor_fields()
            
            # 保存设置到文件
            self.save_settings()
    
    def save_settings(self):
        """保存设置到文件"""
        try:
            settings = {
                'cmd_buttons': self.cmd_buttons,
                'data_format': self.data_format,
                'data_separator': self.data_separator,
                'kv_separator': self.kv_separator
            }
            
            with open('serial_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            self.receive_text.append('设置已保存')
        except Exception as e:
            self.receive_text.append(f'保存设置失败: {str(e)}')
    
    def load_settings(self):
        """加载设置"""
        try:
            if os.path.exists('serial_settings.json'):
                with open('serial_settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                if 'cmd_buttons' in settings:
                    self.cmd_buttons = settings['cmd_buttons']
                if 'data_format' in settings:
                    self.data_format = settings['data_format']
                if 'data_separator' in settings:
                    self.data_separator = settings['data_separator']
                if 'kv_separator' in settings:
                    self.kv_separator = settings['kv_separator']
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def load_settings_from_file(self):
        """从文件加载设置"""
        file_path, _ = QFileDialog.getOpenFileName(self, "加载设置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                if 'cmd_buttons' in settings:
                    self.cmd_buttons = settings['cmd_buttons']
                if 'data_format' in settings:
                    self.data_format = settings['data_format']
                if 'data_separator' in settings:
                    self.data_separator = settings['data_separator']
                if 'kv_separator' in settings:
                    self.kv_separator = settings['kv_separator']
                
                # 更新UI
                self.update_cmd_buttons()
                self.update_sensor_fields()
                
                self.receive_text.append(f'已从 {file_path} 加载设置')
            except Exception as e:
                self.receive_text.append(f'加载设置失败: {str(e)}')
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于",
                          "太阳能植物监护小车串口助手\n\n"
                          "这是一个专为基于手势识别的太阳能植物监护小车设计的串口助手程序。\n\n"
                          "为嵌入式大赛设计 队伍编号13349\n\n"
                          "支持自定义快捷指令和数据解析格式。")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        # 断开串口连接
        self.disconnect_port()
        # 停止定时器
        self.port_timer.stop()
        self.send_timer.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 设置应用全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 应用全局样式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f0f7ff, stop: 1 #cce7ff); /* 柔和的蓝色渐变背景 */
        }

        QGroupBox {
            font-weight: bold;
            border: 1px solid #b0c4de; /* 淡蓝色边框 */
            border-radius: 8px;
            margin-top: 1ex;
            background-color: rgba(255, 255, 255, 0.9); /* 轻微半透明白色背景 */
            padding: 15px;
            padding-top: 25px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 5px 10px;
            background-color: #4682b4; /* 钢蓝色标题背景 */
            color: white;
            border-radius: 5px;
        }

        /* 按钮 */
        QPushButton {
            background-color: #5a9bd5; /* 清新的蓝色 */
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
            border: 1px solid #4a8ac5;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #4a8ac5; /* 悬停时深一点的蓝色 */
            border: 1px solid #3a79b5;
        }

        QPushButton:pressed {
            background-color: #3a79b5; /* 按下时更深的蓝色 */
        }

        /* 连接按钮的特殊样式 */
        QPushButton#connect_btn {
            background-color: #5cb85c; /* 绿色表示连接 */
            border-color: #4cae4c;
        }
        QPushButton#connect_btn:hover {
            background-color: #4cae4c;
        }

        /* 组合框 */
        QComboBox {
            border: 1px solid #b0c4de;
            border-radius: 3px;
            padding: 5px;
            background-color: white;
        }

        QComboBox::drop-down {
            border: 0px;
        }

        /* 文本输入框和文本编辑框 */
        QLineEdit, QTextEdit {
            border: 1px solid #b0c4de;
            border-radius: 3px;
            padding: 5px;
            background-color: #ffffff;
        }

        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #5a9bd5; /* 聚焦时边框变蓝 */
        }

        /* 复选框 */
        QCheckBox {
            spacing: 5px;
        }

        QCheckBox::indicator {
            width: 15px;
            height: 15px;
            border: 1px solid #b0c4de;
            border-radius: 3px;
            background-color: white;
        }

        QCheckBox::indicator:checked {
            background-color: #5a9bd5; /* 选中时蓝色 */
            border: 1px solid #4a8ac5;
        }

        /* 表格控件 (用于设置对话框) */
        QTableWidget {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            gridline-color: #e0e0e0;
            background-color: white;
        }

        QHeaderView::section {
            background-color: #eaf6ff;
            padding: 5px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
        }

        /* 设置对话框特定样式 */
        QDialog {
            background-color: #f0f7ff;
        }

        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: #ffffff;
        }

        QTabBar::tab {
            background: #e0e0e0;
            border: 1px solid #d0d0d0;
            border-bottom-color: #d0d0d0;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom-color: #ffffff;
        }
    """)

    window = SerialAssistant()
    window.show()
    sys.exit(app.exec_()) 