import os
import re
import sys
import time

from PyQt5 import QtWidgets
import connect

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, \
    QTableWidget, QTableWidgetItem, QLabel, QComboBox, QMessageBox, QMenu
from schedulers.list_scheduler import LISTSCHEDULER
BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

# 连接数据库
cursor, conn, lock = connect.connect()

STATUS_MAPPING = {
    0: "尚未开播",
    1: "正在直播",
    2: "已下播",
    10: "正在监测",
    11: "未监测",
    12: "已开始录制",
    13: "录制结束",
    20: "哔哩哔哩",
    21: "斗鱼直播",
    22: "虎牙直播",
    23: "抖音直播"
}

RUNNING = 1
STOPPING = 2
STOP = 3


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.switch = None
        self.drop_box_text = STATUS_MAPPING[20]   # 选中下拉框内容
        self.label_status = None
        self.table_widget = None
        self.txt_room_id = None

        # # 窗体标题和尺寸
        # self.setWindowTitle('网络视频下载系统')
        # # 窗体logo
        # self.setWindowIcon(QIcon('asset/favicon.ico'))
        # # 窗体的尺寸
        # self.resize(940, 450)
        # # 窗体的位置
        # qr = self.frameGeometry()
        # cp = QDesktopWidget().availableGeometry().center()
        # qr.moveCenter(cp)
        # 创建布局
        layout = QVBoxLayout()
        layout.addLayout(self.init_header())
        layout.addLayout(self.init_form())
        layout.addLayout(self.init_table())
        # layout.addLayout(self.init_footer())

        # 给窗体设置元素的排列方式
        self.setLayout(layout)
        self.show()

    def init_header(self):
        # 1、创建顶部菜单布局
        header_layout = QHBoxLayout()

        # # 1.1 创建按钮，加入header_layout
        # btn_start = QPushButton("开始监测")
        # # btn_start.setFixedHeight(100)
        # btn_start.clicked.connect(self.event_start_click)
        # header_layout.addWidget(btn_start)
        #
        # # 1.2 创建按钮
        # btn_stop = QPushButton("停止监测")
        # btn_stop.clicked.connect(self.event_stop_click)
        # # header_layout.addWidget(btn_stop)
        btn_manage_up = QPushButton("主播管理")
        btn_manage_up.clicked.connect(self.event_manage_click)
        header_layout.addWidget(btn_manage_up)

        btn_setting = QPushButton("输出配置")
        btn_setting.clicked.connect(self.event_setting_click)
        header_layout.addWidget(btn_setting)

        # 弹簧
        header_layout.addStretch()
        return header_layout

    def init_form(self):
        # 2、创建表单布局
        form_layout = QHBoxLayout()

        # 下拉框
        combo = QComboBox(self)
        combo.addItem(STATUS_MAPPING[20])
        combo.addItem(STATUS_MAPPING[21])
        # combo.addItem(STATUS_MAPPING[22])
        # combo.addItem(STATUS_MAPPING[23])

        combo.activated[str].connect(self.onActivated)
        form_layout.addWidget(combo)

        # 2.1 输入框
        txt_rid = QLineEdit()
        # txt_rid.setPlaceholderText("请输入直播间号，例如“999”")
        txt_rid.setPlaceholderText("请输入直播间链接，例如“https://live.bilibili.com/999”")
        self.txt_room_id = txt_rid
        form_layout.addWidget(txt_rid)

        # 2.2 添加按钮
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.event_add_click)
        form_layout.addWidget(btn_add)

        return form_layout

    def init_table(self):
        # 3、创建表格布局
        table_layout = QHBoxLayout()

        # 3.1 创建表格
        self.table_widget = table_widget = QTableWidget(0, 5)  # (行，列)
        table_header = [
            {"field": "platform", "text": "直播平台", 'width': 100},
            {"field": "room_id", "text": "房间号", 'width': 120},
            {"field": "name", "text": "主播名称", 'width': 180},
            {"field": "live_status", "text": "直播状态", 'width': 220},
            {"field": "save_dir", "text": "录制文件保存目录", 'width': 260},
        ]

        for idx, info in enumerate(table_header):  # idx起始默认0，info代表每个字典
            item = QTableWidgetItem()
            item.setText(info['text'])
            table_widget.setHorizontalHeaderItem(idx, item)
            table_widget.setColumnWidth(idx, info['width'])

        self.init_all_info()

        # 开启右键设置(开启右键复制功能， 在表格中点击右键时， 自动触发 right_menu 函数)
        table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        table_widget.customContextMenuRequested.connect(self.table_right_menu)

        table_layout.addWidget(table_widget)
        return table_layout

    def init_footer(self):
        # 4、创建底部菜单
        footer_layout = QHBoxLayout()

        # self.label_status = label_status = QLabel("未监测", self)
        self.label_status = label_status = QLabel("就绪", self)
        footer_layout.addWidget(label_status)

        footer_layout.addStretch()

        # btn_get_videos = QPushButton("视频下载")
        # btn_get_videos.clicked.connect(self.event_get_videos)
        # footer_layout.addWidget(btn_get_videos)

        btn_manage_up = QPushButton("主播管理")
        btn_manage_up.clicked.connect(self.event_manage_click)
        footer_layout.addWidget(btn_manage_up)

        btn_setting = QPushButton("输出配置")
        btn_setting.clicked.connect(self.event_setting_click)
        footer_layout.addWidget(btn_setting)

        return footer_layout

    # ------------init_header方法区----------------
    def event_start_click(self):
        if self.switch == STOP:
            QMessageBox.warning("错误", "正在执行获取终止中，请勿重复操作")
            return
        self.switch = RUNNING

        # 1 为每一行创建一个线程去执行  (所有的线程记录)
        LISTSCHEDULER.start(
            window=self,
            base_dir=BASE_DIR,
            fn_update_status=self.task_live_status_update
        )
        # 2 状态显示“监测中”
        # self.update_status_message("监测中...")

    def event_stop_click(self):
        if self.switch != RUNNING:
            QMessageBox.warning(self, "错误", "已停止或正在终止，请勿重复操作")

        self.switch = STOPPING

        # 1 执行中的线程逐一终止
        LISTSCHEDULER.stop()

    # ------------init_form方法区----------------
    # 获取下拉框内容函数
    def onActivated(self, text):
        self.drop_box_text = text

    # 添加直播间号按钮
    def event_add_click(self):
        # 1 获取输入框的内容
        url = self.txt_room_id.text()

        current_row_count = self.table_widget.rowCount()  # 当前表格有多少行
        print(current_row_count)

        # 2 根据获取到输入框的内容，获取到对应直播间的信息，创建一个线程发送请求自动获取信息(爬虫获取数据)
        if self.drop_box_text == STATUS_MAPPING[20]:    # 哔哩哔哩
            room_id = re.search(r'bilibili\.com/(\d+)', url).group(1)
            if not room_id:
                self.init_task_error_callback("请输入正确的网页链接")
                return
            from utils.bilibili_threads import GetInfoThread
            thread = GetInfoThread(current_row_count, room_id, self.drop_box_text, self)
            thread.success.connect(self.init_task_success_callback)
            thread.error.connect(self.init_task_error_callback)
            thread.start()
        elif self.drop_box_text == STATUS_MAPPING[21]:  # 斗鱼直播
            # response = requests.get(url)
            # room_id = re.search(r'apm_room_id *= *(\d+)', response.text).group(1)
            # room_id = room_id.strip()  # 去掉空白
            room_id = re.search(r'rid=(\d+)', url)
            if not room_id:
                room_id = re.search(r'\.com/(\d+)', url)
                if not room_id:
                    self.init_task_error_callback("请输入正确的网页链接")
                    return
                else:
                    room_id = room_id.group(1)
            else:
                room_id = room_id.group(1)
            if not room_id:
                self.init_task_error_callback("请输入正确的网页链接")
                return
            from utils.douyu_threads import GetInfoThread
            thread = GetInfoThread(current_row_count, room_id, self.drop_box_text, self)
            thread.success.connect(self.init_task_success_callback)
            thread.error.connect(self.init_task_error_callback)
            thread.start()
        elif self.drop_box_text == STATUS_MAPPING[22]:  # 虎牙直播
            pass
        elif self.drop_box_text == STATUS_MAPPING[23]:  # 抖音直播
            pass

    def init_task_success_callback(self, row_index, platform, room_id, name, live_status):
        try:
            # while True:
            #     print(1)
            # 设置文件保存目录
            log_folder = os.path.join(BASE_DIR, "live_videos", name)
            print(log_folder)
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)

            log_folder = re.sub(r'(:)', r'\1\\', log_folder)
            log_folder = re.sub(r'(octopus)', r'\1\\', log_folder)
            log_folder = re.sub(r"(videos)", r"\1\\", log_folder)

            values = (platform, room_id, name, live_status, log_folder, 0)
            sql = "INSERT INTO live_list_info(platform, room_id, name, live_status, save_dir, flag) VALUES (?, ?, ?, ?, ?, ?)"
            lock.acquire()
            cursor.execute(sql, values)
            conn.commit()

            self.table_widget.insertRow(row_index)

            # 更新窗体显示的数据
            for i, item in enumerate(values):
                cell = QTableWidgetItem(item)
                cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if i == 3:
                    cell.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.table_widget.setItem(row_index, i, cell)

            LISTSCHEDULER.start_item_thread(row_index=row_index, fn_update_status=self.task_live_status_update)

        except Exception as e:
            print(e)
            QMessageBox.warning(self, "错误", "主播添加未成功")
            conn.rollback()
        lock.release()

        # 输入框清空
        self.txt_room_id.clear()

    def init_task_error_callback(self, message):
        QMessageBox.warning(self, "错误", message)
        # 输入框清空
        self.txt_room_id.clear()

    def task_live_status_update(self, row_index, platform, rid, live_status):
        try:
            values = (live_status, platform, rid)
            sql = "UPDATE live_list_info SET live_status = ?  WHERE platform = ? and room_id = ?"
            lock.acquire()
            cursor.execute(sql, values)
            conn.commit()

            # 更新直播状态
            cell_live_status = QTableWidgetItem(live_status)
            cell_live_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            cell_live_status.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.table_widget.setItem(row_index, 3, cell_live_status)
        except:
            QMessageBox.warning(self, "错误", "直播状态更新未成功")
            conn.rollback()
        lock.release()

    def update_status_message(self, message):
        self.label_status.setText(message)
        self.label_status.repaint()


    # ------------init_table方法区----------------
    # 右键按钮
    def table_right_menu(self, pos):
        # 只有选中一行时，才支持右键
        selected_item_list = self.table_widget.selectedItems()
        if len(selected_item_list) == 0:
            return

        # 创建菜单
        menu = QMenu()
        item_start = menu.addAction("开始录制")
        item_stop = menu.addAction("停止录制")
        item_delete = menu.addAction("移除主播")
        item_modify_path = menu.addAction("修改路径")

        # action表示选中了哪个
        action = menu.exec_(self.table_widget.mapToGlobal(pos))
        row_index = selected_item_list[0].row()  # 选中的当前行

        if action == item_start:
            # if self.label_status.text() != "监测中...":
            #     QMessageBox.warning(self, "错误", "系统未开启监测，请点击左上角“开始监测”按钮")
            #     return

            LISTSCHEDULER.start_item_thread(row_index=row_index, fn_update_status=self.task_live_status_update)


        if action == item_stop:
            # if self.label_status.text() == "未监测":
            #     QMessageBox.warning(self, "错误", "系统未开启监测，请点击左上角“开始监测”按钮")
            #     return

            LISTSCHEDULER.stop_item_thread(row_index=row_index)

        if action == item_delete:
            # 删除主播
            row_index = selected_item_list[0].row()
            platform = self.table_widget.item(row_index, 0).text().strip()
            room_id = self.table_widget.item(row_index, 1).text().strip()

            try:
                # sql = 'DELETE FROM live_list_info WHERE platform="%s" and room_id="%s"' % (platform, room_id)
                sql = "UPDATE live_list_info SET flag = ? WHERE platform = ? and room_id = ?"
                values = (1, platform, room_id)
                lock.acquire()
                cursor.execute(sql, values)
                conn.commit()

                self.table_widget.removeRow(row_index)
            except:
                conn.rollback()
                QMessageBox.warning(self, "错误", "删除主播未成功")
            lock.release()

        if action == item_modify_path:
            dir_name = QtWidgets.QFileDialog.getExistingDirectory(self, "选取文件夹", BASE_DIR)
            if not dir_name:
                return
            try:
                platform = self.table_widget.item(row_index, 0).text()
                room_id = self.table_widget.item(row_index, 1).text()
                sql = "UPDATE live_list_info SET save_dir = ? WHERE platform = ? and room_id = ?"
                values = (dir_name, platform, room_id)
                lock.acquire()
                cursor.execute(sql, values)
                conn.commit()

                cell_save_dir = QTableWidgetItem(dir_name)
                cell_save_dir.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table_widget.setItem(row_index, 4, cell_save_dir)
            except:
                conn.rollback()
                QMessageBox.warning(self, "错误", "保存目录修改未成功")
            lock.release()

    # ------------init_footer方法区----------------
    # def event_get_videos(self):
    #     from dialogs.dialog import GetVideosWindow
    #     self.get_videos_window = GetVideosWindow(BASE_DIR)
    #     self.get_videos_window.setWindowModality(Qt.NonModal)
    #     self.get_videos_window.show()

    def event_manage_click(self):
        from windows.live_manage_window import LiveManageWindow
        self.live_manage_window = LiveManageWindow(BASE_DIR)
        self.live_manage_window.setWindowModality(Qt.ApplicationModal)
        self.live_manage_window.move_success.connect(self.add_new_line)
        self.live_manage_window.show()

    def add_new_line(self, platform, room_id):
        print(platform, room_id)
        try:
            sql = "SELECT * FROM live_list_info WHERE platform = ? and room_id = ? and flag = 0 limit 1"
            values = (platform, room_id)
            lock.acquire()
            cursor.execute(sql, values)
            data_list = cursor.fetchall()
            print(data_list)
            lock.release()

            current_row_count = self.table_widget.rowCount()  # 获取当前表格有多少行
            self.table_widget.insertRow(current_row_count)
            for i, ele in enumerate(data_list[0]):  # 添加enumerate后能多加一个序号i
                print(ele)
                cell = QTableWidgetItem(ele)
                cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if i == 3:
                    cell.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                if i == 5:
                    continue
                self.table_widget.setItem(current_row_count, i, cell)

        except Exception as e:
            QMessageBox.warning(self, "错误", "数据添加未成功")

    def event_setting_click(self):
        from windows.live_setting_window import LiveSettingWindow
        self.setting_window = LiveSettingWindow(BASE_DIR)
        self.setting_window.show()

    # ------------功能区----------------
    def init_all_info(self):
        try:
            sql = "SELECT * FROM live_list_info WHERE flag = 0"
            cursor.execute(sql)
            data_list = cursor.fetchall()
            print(data_list)

            current_row_count = self.table_widget.rowCount()  # 获取当前表格有多少行
            for row_list in data_list:
                # print(row_list)
                self.table_widget.insertRow(current_row_count)
                # 写真实数据
                for i, ele in enumerate(row_list):  # 添加enumerate后能多加一个序号i
                    cell = QTableWidgetItem(ele)
                    cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    if i == 3:
                        cell.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                    if i == 5:
                        continue
                    self.table_widget.setItem(current_row_count, i, cell)
                current_row_count += 1

            time.sleep(1)
            try:
                self.event_start_click()
            except Exception as e:
                print(e)
        except Exception as e:
            QMessageBox.warning(self, "错误", "未能获取到数据")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
