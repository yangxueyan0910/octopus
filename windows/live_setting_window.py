import time

from PyQt5 import QtWidgets
import connect
from asset import resources
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QMessageBox, QHBoxLayout, \
    QTableWidgetItem, QTableWidget, QWidget, \
    QMenu, QLabel, QGridLayout, QLineEdit, QComboBox, QPushButton

# 连接数据库
cursor, conn, lock = connect.connect()
class LiveSettingWindow(QWidget):

    move_success = pyqtSignal(str, str)

    def __init__(self, basedir, *args, **kwargs):
        super(LiveSettingWindow, self).__init__(*args, **kwargs)
        self.setting_choice = None
        self.basedir = basedir
        self.current_item = {}
        self.settings = {}
        self.init_ui()
        self.init_first_info()

    def init_ui(self):
        # 窗体logo
        self.setWindowIcon(QIcon(':/favicon.ico'))
        self.setWindowTitle("输出配置")
        self.resize(600, 400)

        layout = QVBoxLayout()
        layout.addLayout(self.init_header())
        position = QLabel("")
        layout.addWidget(position)

        table_layout = QHBoxLayout()
        self.table_widget = table_widget = QTableWidget(4, 2)  # (行，列)
        # 表头不显示分割线
        self.table_widget.setShowGrid(True)
        # 表头不显示数字
        self.table_widget.horizontalHeader().setVisible(False)
        self.table_widget.verticalHeader().setVisible(False)

        table_widget.setColumnWidth(0, 220)
        table_widget.setColumnWidth(1, 350)
        table_header = [
            {"field": "s", "text": "     分辨率", "width": 400},
            {"field": "bv", "text": "     码率", "width": 400},
            {"field": "r", "text": "     每秒帧数", "width": 400},
            {"field": "path", "text": "     保存路径", "width": 400},
        ]
        for idx, info in enumerate(table_header):  # idx起始默认0，info代表每个字典
            item = QTableWidgetItem()
            item.setText(info['text'])
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            table_widget.setItem(idx, 0, item)
            table_widget.setRowHeight(idx, 50)

        # 创建resolution下拉框
        self.resolution = resolution = QComboBox()
        resolution.setFixedHeight(30)
        resolution.addItem("600x360")
        resolution.addItem("1280x720")
        resolution.addItem("1920x1080")
        self.table_widget.setCellWidget(0, 1, resolution)

        # 创建code_rate下拉框
        self.code_rate = code_rate = QComboBox()
        code_rate.setFixedHeight(30)
        code_rate.addItem("256")
        code_rate.addItem("384")
        code_rate.addItem("512")
        code_rate.addItem("768")
        code_rate.addItem("1024")
        self.table_widget.setCellWidget(1, 1, code_rate)

        # 创建frame_rate下拉框
        self.frame_rate = frame_rate = QComboBox()
        frame_rate.setFixedHeight(30)
        frame_rate.addItem("15")
        frame_rate.addItem("18")
        frame_rate.addItem("20")
        frame_rate.addItem("24")
        frame_rate.addItem("30")
        self.table_widget.setCellWidget(2, 1, frame_rate)

        # 创建QLabel和QPushButton
        self.label = label = QLabel()
        button = QPushButton('选择保存路径')
        button.clicked.connect(self.edit_path)

        # 创建QWidget，将QLabel和QPushButton添加到QWidget中
        com_widget = QWidget()
        com_layout = QHBoxLayout()
        com_layout.addWidget(label)
        com_layout.addWidget(button)
        com_layout.setAlignment(label, Qt.AlignLeft)
        com_layout.setAlignment(button, Qt.AlignRight)
        com_widget.setLayout(com_layout)

        # # 创建QTableWidgetItem，将QWidget设置为单元格的小部件
        # com_item = QTableWidgetItem()
        # com_item.setData(Qt.WidgetShortcut, com_widget)
        #
        # # 将QTableWidgetItem添加到QTableWidget中的指定单元格
        self.table_widget.setCellWidget(3, 1, com_widget)

        table_layout.addWidget(self.table_widget)

        layout.addLayout(table_layout)
        layout.addLayout(self.init_footer())
        self.setLayout(layout)

    def edit_path(self):
        dir_name = QtWidgets.QFileDialog.getExistingDirectory(self, "选取文件夹", self.basedir)
        if not dir_name:
            return
        self.label.setText(dir_name)
        # try:
        #     index = self.setting_choice.currentIndex()
        #     sql = "UPDATE live_setting SET path = ? WHERE id = ?"
        #     values = (dir_name, index+1)
        #     lock.acquire()
        #     cursor.execute(sql, values)
        #     conn.commit()
        #
        #     self.settings[index]['path'] = dir_name
        #     print(105, self.settings[index])
        # except:
        #     conn.rollback()
        #     QMessageBox.warning(self, "错误", "保存目录修改未成功")
        # lock.release()

    # 顶部菜单布局
    def init_header(self):
        # 1、创建顶部菜单布局
        header_layout = QHBoxLayout()

        # 1.1 创建配置选择下拉框，加入header_layout
        self.setting_choice = setting_choice = QComboBox()
        setting_choice.currentIndexChanged.connect(self.show_event)
        # setting_choice.addItem('最优化的质量和大小')
        # setting_choice.addItem('高质量和大小')
        # setting_choice.addItem('低质量和大小')
        header_layout.addWidget(setting_choice)

        # 弹簧
        header_layout.addStretch()

        # 1.2 创建按钮
        btn_save_setting = QPushButton("另存为")
        btn_save_setting.clicked.connect(self.event_save_setting)
        header_layout.addWidget(btn_save_setting)

        return header_layout

    def event_save_setting(self):
        from windows.setting_dialog import SettingDialog
        num = len(self.settings) - 2
        dialog = SettingDialog(num)
        dialog.success.connect(self.save_setting)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.exec_()

    def save_setting(self, name):
        try:
            resolution = str(self.resolution.currentIndex())
            code_rate = str(self.code_rate.currentIndex())
            frame_rate = str(self.frame_rate.currentIndex())
            path = self.label.text()
            index = self.setting_choice.currentIndex()
            num = len(self.settings)
            sql = "INSERT INTO live_setting(id, name, resolution, code_rate, frame_rate, path, flag) VALUES (?, ?, ?, ?, ?, ?, ?)"
            values = (num+1, name, resolution, code_rate, frame_rate, path, 0)
            print(180, values)
            lock.acquire()
            cursor.execute(sql, values)
            conn.commit()

            self.setting_choice.addItem(name)
            self.setting_choice.setCurrentIndex(num)
            self.settings[num] = {'id': num+1, 'name': name, 'resolution': resolution,
                                'code_rate': code_rate, 'frame_rate': frame_rate, 'path': path}
            QMessageBox.information(self, "保存成功", "已成功添加！")
        except:
            conn.rollback()
            QMessageBox.warning(self, "错误", "添加未成功")
            lock.release()
        lock.release()

    def show_event(self):
        row_list = self.settings[self.setting_choice.currentIndex()]
        print(row_list)

        item_resolution = row_list['resolution']
        self.resolution.setCurrentIndex(int(item_resolution))

        item_code_rate = row_list['code_rate']
        self.code_rate.setCurrentIndex(int(item_code_rate))

        item_frame_rate = row_list['frame_rate']
        self.frame_rate.setCurrentIndex(int(item_frame_rate))

        item_path = row_list['path']
        self.label.setText(item_path)

    # 底部菜单布局
    def init_footer(self):
        # 4、创建底部菜单
        footer_layout = QHBoxLayout()

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.event_cancel_click)
        footer_layout.addWidget(btn_cancel)

        footer_layout.addStretch()

        btn_confirm = QPushButton("确定")
        btn_confirm.clicked.connect(self.event_confirm_click)
        footer_layout.addWidget(btn_confirm)

        return footer_layout

    def event_cancel_click(self):
        self.close()

    def event_confirm_click(self):
        try:
            resolution = str(self.resolution.currentIndex())
            code_rate = str(self.code_rate.currentIndex())
            frame_rate = str(self.frame_rate.currentIndex())
            path = self.label.text()
            index = self.setting_choice.currentIndex()
            # 将原来的flag设置为0
            sql = "UPDATE live_setting SET flag = ? WHERE id = ?"
            values = (0, self.current_item['id'])
            cursor.execute(sql, values)

            # 更新当前数据
            sql = "UPDATE live_setting SET resolution = ?, code_rate = ?, frame_rate = ?,  path = ?, flag = ? WHERE id = ?"
            values = (resolution, code_rate, frame_rate, path, 1, index+1)
            lock.acquire()
            cursor.execute(sql, values)

            conn.commit()

            self.settings[index]['resolution'] = resolution
            self.settings[index]['code_rate'] = code_rate
            self.settings[index]['frame_rate'] = frame_rate
            self.settings[index]['path'] = path
            self.current_item = self.settings[index]
            print(151, self.settings[index])
            QMessageBox.information(self, "保存成功", "修改已成功保存！")
        except:
            conn.rollback()
            QMessageBox.warning(self, "错误", "保存修改未成功")
            lock.release()
        lock.release()

    def init_first_info(self):
        try:
            sql = "SELECT * FROM live_setting"
            lock.acquire()
            cursor.execute(sql)
            data_list = cursor.fetchall()
            print(152, data_list)
            for i, row_list in enumerate(data_list):
                self.setting_choice.addItem(row_list[1])
                self.settings[i] = {'id': row_list[0], 'name': row_list[1], 'resolution': row_list[2], 'code_rate': row_list[3], 'frame_rate': row_list[4], 'path': row_list[5]}
                if row_list[6] == 1:
                    self.current_item = self.settings[i]
                    self.setting_choice.setCurrentIndex(i)

                    item_resolution = row_list[2]
                    self.resolution.setCurrentIndex(int(item_resolution))

                    item_code_rate = row_list[3]
                    self.code_rate.setCurrentIndex(int(item_code_rate))

                    item_frame_rate = row_list[4]
                    self.frame_rate.setCurrentIndex(int(item_frame_rate))

                    item_path = row_list[5]
                    self.label.setText(item_path)

        except Exception as e:
            QMessageBox.warning(self, "错误", "未能获取到数据")
        lock.release()