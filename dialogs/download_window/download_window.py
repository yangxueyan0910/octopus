import os
import random
import time
from queue import Queue

from octopus import connect
from octopus.asset import resources

from PyQt5.QtCore import Qt, QMutex, QWaitCondition, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QPushButton,  QMessageBox, QHBoxLayout, \
    QTableWidgetItem, QTableWidget, QWidget, \
    QTabWidget, QProgressBar, QMenu

#连接数据库
cursor, conn, lock = connect.connect()


import cgitb
cgitb.enable(format='text')

class DownloadVideosWindow(QTabWidget):
    def __init__(self, basedir, *args, **kwargs):
        super(DownloadVideosWindow, self).__init__(*args, **kwargs)
        self.basedir = basedir
        self.pause_icon = QIcon(':/pause.ico')
        self.start_icon = QIcon(':/play.ico')
        self.cancel_icon = QIcon(':/cancel.ico')
        self.dir_icon = QIcon(':/dir.ico')
        self.mutex = QMutex()
        self.wait_cond = QWaitCondition()
        self.queue = Queue()
        self.timer = QTimer(self)
        #新增并发控制属性
        self.max_concurrent = 3  #最大并发数
        self.current_tasks = 0  # 前运行任务数

        self.init_ui()

    def init_ui(self):
        # 窗体logo
        self.setWindowIcon(QIcon(':/favicon.ico'))
        self.setWindowTitle("下载列表")
        self.resize(1350, 650)

        # 创建2个选项卡小控件窗口
        self.processing_widget = QWidget()
        self.finished_widget = QWidget()

        # 将2个选项卡添加到顶层窗口中
        self.addTab(self.processing_widget, "进行中")
        self.addTab(self.finished_widget, "已完成")

        # 每个选项卡自定义的内容
        self.processing_widget_UI()
        self.finisher_widget_UI()

    # 进行中界面样式
    def processing_widget_UI(self):
        layout = QVBoxLayout()

        table_layout = QHBoxLayout()
        self.table_widget = table_widget = QTableWidget(0, 5)  # (行，列)
        table_header = [
            {"field": "name", "text": "名称", 'width': 400},
            {"field": "processing", "text": "下载进度", 'width': 450},
            {"field": "operator", "text": "", 'width': 140},
            {"field": "cancel", "text": "", 'width': 100},
            {"field": "bitrate", "text": "实时速度", 'width': 180},
        ]
        for idx, info in enumerate(table_header):  # idx起始默认0，info代表每个字典
            item = QTableWidgetItem()
            item.setText(info['text'])
            table_widget.setHorizontalHeaderItem(idx, item)
            table_widget.setColumnWidth(idx, info['width'])
        # 显示水平表头
        self.table_widget.horizontalHeader().setVisible(True)
        # 表头显示分割线
        self.table_widget.setShowGrid(True)
        # 表头显示数字
        self.table_widget.verticalHeader().setVisible(True)
        self.table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.init_table()

        # 开启右键设置(开启右键复制功能， 在表格中点击右键时， 自动触发 right_menu 函数)
        table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        table_widget.customContextMenuRequested.connect(self.table_right_menu)

        table_layout.addWidget(table_widget)

        # self.show()
        # for item_video in self.download_video_list:
        #     self.add_table_item(item_video)
        layout.addLayout(self.init_header())
        layout.addLayout(table_layout)

        self.processing_widget.setLayout(layout)

    # 顶部菜单布局
    def init_header(self):
        # 1、创建顶部菜单布局
        header_layout = QHBoxLayout()

        # 弹簧
        header_layout.addStretch()

        # # 1.1 创建按钮，加入header_layout
        # btn_start = QPushButton("全部开始")
        # # btn_start.setFixedHeight(100)
        # btn_start.clicked.connect(self.event_all_start)
        # header_layout.addWidget(btn_start)

        # # 1.2 创建按钮
        # btn_stop = QPushButton("全部暂停")
        # btn_stop.clicked.connect(self.event_all_stop)
        # header_layout.addWidget(btn_stop)

        # 1.3 创建按钮
        btn_cancel = QPushButton("全部清空")
        btn_cancel.clicked.connect(self.event_all_cancel)
        header_layout.addWidget(btn_cancel)

        return header_layout

    # 初始化表格
    def init_table(self):
        try:
            sql = "SELECT * FROM download_video_list WHERE finish_flag < 100"  #仅加载未完成的任务
            lock.acquire()
            cursor.execute(sql)
            video_info_list = cursor.fetchall()
            lock.release()
            # 清空现有表格
            self.table_widget.setRowCount(0)
            # 重新添加数据
            for row_list in video_info_list:
                item_video = {
                    'bvid': row_list[1],
                    'video_url': row_list[0],
                    'video_title': row_list[2],
                    'finish_flag': row_list[3]
                }
                self.add_table_item(item_video)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"初始化表格失败: {str(e)}")

    # -----header方法区------
    def event_all_start(self,automatic=False):
        if not automatic:
            #手动触发时保留确认对话框
            response = QMessageBox.warning(self, '警告', '是否要全部开始当前视频下载进程',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response != QMessageBox.Yes:
                return

            #确保队列清空并重新填充
        while not self.queue.empty():
            self.queue.get()

            #遍历所有行，将未开始的任务加入队列
        for row in range(self.table_widget.rowCount()):
            processbar = self.table_widget.cellWidget(row, 1)
            if processbar.play_button.text() == "开始":
                self.queue.put(processbar)

            #强制触发下载池
        self.add_download_pool(True)

    def event_all_stop(self):
        A = QMessageBox.warning(self, '警告', '是否要全部暂停当前视频下载进程', QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No)
        if A == QMessageBox.Yes:
            for row in range(self.table_widget.rowCount()):
                processbar = self.table_widget.cellWidget(row, 1)
                if processbar.play_button.text() == "开始":
                    processbar.play_button.setText("暂停")
                self.start_progress(processbar)
        else:
            return

    def event_all_cancel(self):
        A = QMessageBox.warning(self, '警告', '是否要全部取消当前视频下载进程', QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No)
        if A == QMessageBox.Yes:
            lock.acquire()
            try:
                # 清空队列并停止所有线程
                while not self.queue.empty():
                    self.queue.get()
                for row in range(self.table_widget.rowCount() - 1, -1, -1):
                    processbar = self.table_widget.cellWidget(row, 1)
                    processbar.thread.download_flag = False
                    bvid = processbar.thread.item_video_info['bvid']
                    # 删除数据库记录
                    sql = "DELETE FROM download_video_list WHERE bvid = ?"
                    values = (bvid,)
                    cursor.execute(sql, values)
                    conn.commit()
                    # 移除表格行
                    self.table_widget.removeRow(row)
            except Exception as e:
                conn.rollback()
                QMessageBox.warning(self, "错误", f"取消下载失败: {str(e)}")
            finally:
                lock.release()
        else:
            return

    # -----table方法区------
    def add_table_item(self, item_video):
        current_row_count = self.table_widget.rowCount()
        self.table_widget.insertRow(current_row_count)
        self.table_widget.setRowHeight(current_row_count, 20)

        # 设置标题
        title_item = QTableWidgetItem(item_video['video_title'])
        title_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table_widget.setItem(current_row_count, 0, title_item)

        # 显示下载速度
        tip_item = QTableWidgetItem('')
        tip_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tip_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table_widget.setItem(current_row_count, 4, tip_item)

        # 创建进度条
        progress_bar = QProgressBar(self)
        progress_bar.setValue(0)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                border-radius: 6px;
                text-align: center;
                height: 12px;
                margin: 0px 5px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 6px;
            }
            QProgressBar::chunk:hover {
                background-color: #45a049;
            }
            QProgressBar:disabled {
                background-color: #E0E0E0;
            }
            QProgressBar::chunk:disabled {
                background-color: #A0A0A0;
            }
        """)
        progress_bar.setValue(item_video['finish_flag'])

        # 开始按钮
        play_button = QPushButton(self.start_icon, "开始", self)
        play_button.setStyleSheet("border:none;")
        play_button.clicked.connect(lambda: self.add_queue(progress_bar))

        # 取消按钮
        cancel_button = QPushButton(self.cancel_icon, "取消", self)
        cancel_button.setStyleSheet("border:none; ")
        cancel_button.clicked.connect(lambda: self.cancel_progress(item_video['bvid']))

        self.table_widget.setCellWidget(current_row_count, 1, progress_bar)

        self.table_widget.setCellWidget(current_row_count, 2, play_button)

        self.table_widget.setCellWidget(current_row_count, 3, cancel_button)
        # 创建线程
        from octopus.dialogs.utils.download_threads import DownloadInfoThread
        thread = DownloadInfoThread(self.basedir, item_video, play_button, current_row_count, progress_bar, tip_item, self)
        thread.current_value = item_video['finish_flag']
        thread.progress_signal.connect(progress_bar.setValue)
        thread.progress_finish_update.connect(self.table_update)
        thread.progress_pause.connect(self.add_download_pool)
        thread.tip_signal.connect(self.add_tip_item)
        #新增信号连接
        thread.progress_finish.connect(self.task_finished)#连接完成信号到槽函数
        progress_bar.thread = thread
        progress_bar.current_row_count = current_row_count
        progress_bar.play_button = play_button
        progress_bar.tip_item = tip_item
        progress_bar.bvid = item_video['bvid']

    #新增任务完成处理方法
    def task_finished(self):
        self.current_tasks -= 1 #减少当前任务计数
        self.add_download_pool(True) #触发新任务启动

    def add_tip_item(self, tip):
        thread = self.table_widget.sender()
        tip_item = thread.tip_item
        tip_item.setText(tip)

    def start_progress(self, progress_bar):
        if progress_bar.play_button.text() == "开始":
            progress_bar.setRange(0, 100)
            progress_bar.thread.download_flag = True
            progress_bar.thread.start()
            progress_bar.play_button.setIcon(self.pause_icon)
            progress_bar.play_button.setText("暂停")
        elif progress_bar.play_button.text() == "暂停":
            # progress_bar.thread.stop()
            progress_bar.thread.download_flag = False
            progress_bar.play_button.setIcon(self.start_icon)
            progress_bar.play_button.setText("开始")

    def cancel_progress(self, bvid):
        # 事件发送,有时候我们会想知道是哪个组件发出了一个信号，PyQt5里的sender()方法能搞定这件事
        button = self.table_widget.sender()
        index = self.table_widget.indexAt(button.pos())
        current_row_count = index.row()
        processbar = self.table_widget.cellWidget(current_row_count, 1)
        A = QMessageBox.warning(self, '警告', '是否确定要删除当前视频下载进程', QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No)
        if A == QMessageBox.Yes:
            lock.acquire()
            try:
                processbar.thread.download_flag = False
                sql = "DELETE FROM download_video_list WHERE bvid = ?"
                values = (bvid,)
                cursor.execute(sql, values)
                conn.commit()
                self.table_widget.removeRow(current_row_count)
            except:
                conn.rollback()
                QMessageBox.warning(self, "错误", "删除视频未成功")
            lock.release()
        else:
            return

    # 添加需要下载的视频
    def add_queue(self, processbar):
        time.sleep(random.random())
        self.queue.put(processbar)
        processbar.play_button.setIcon(self.pause_icon)
        if self.queue.qsize() == 1:
            self.add_download_pool(True)

    def add_download_pool(self, flag):
        if flag:
            while self.current_tasks<self.max_concurrent and not self.queue.empty():
                time.sleep(random.randint(1, 2))
                processbar = self.queue.get()
                self.current_tasks+=1 #更新当前任务计数
                self.start_progress(processbar)

    # 进度条完成后进行表格更新
    def table_update(self, item_video):
        thread = self.table_widget.sender()
        button = thread.play_button
        index = self.table_widget.indexAt(button.pos())
        current_row_count = index.row()
        self.table_widget.removeRow(current_row_count)
        self.add_finish_table_item(item_video)
        thread.quit()
        thread.wait()


    # 右键选项
    def table_right_menu(self, pos):
        # 只有选中一行时，才支持右键
        selected_item_list = self.table_widget.selectedItems()
        if len(selected_item_list) == 0:
            return

        # 创建菜单
        menu = QMenu()
        item_start = menu.addAction("开始下载")
        item_stop = menu.addAction("暂停下载")
        item_delete = menu.addAction("删除任务")

        # action表示选中了哪个
        action = menu.exec_(self.table_widget.mapToGlobal(pos))
        # row_index = selected_item_list[0].row()  # 选中的当前行
        # processbar = self.table_widget.cellWidget(row_index, 1)

        if action == item_start:
            for item in selected_item_list:
                row_index = item.row()  # 选中的当前行
                processbar = self.table_widget.cellWidget(row_index, 1)
                self.add_queue(processbar)

        if action == item_stop:
            for item in selected_item_list:
                row_index = item.row()  # 选中的当前行
                processbar = self.table_widget.cellWidget(row_index, 1)
                if processbar.play_button.text() == "开始":
                    processbar.play_button.setText("暂停")
                self.start_progress(processbar)

        if action == item_delete:
            selected_item_list.reverse()
            for item in selected_item_list:
                # 如何获取到这个bvid
                row_index = item.row()
                processbar = self.table_widget.cellWidget(row_index, 1)
                bvid = processbar.bvid
                lock.acquire()
                try:
                    processbar.thread.download_flag = False
                    sql = "DELETE FROM download_video_list WHERE bvid = ?"
                    values = (bvid,)
                    cursor.execute(sql, values)
                    conn.commit()
                    self.table_widget.removeRow(row_index)
                except:
                    conn.rollback()
                    QMessageBox.warning(self, "错误", "视频删除失败")
                lock.release()

    def closeEvent(self, event):
        for row in range(self.table_widget.rowCount()):
            widget = self.table_widget.cellWidget(row, 1)
            # print(153, widget.thread)
            if widget.thread.isRunning():
                A = QMessageBox.warning(self, '警告', '您有正在下载的进程，是否确认关闭窗口', QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No)
                if A == QMessageBox.Yes:
                    for index in range(self.table_widget.rowCount()):
                        widget = self.table_widget.cellWidget(index, 1)
                        if widget.thread.isRunning():
                            widget.thread.download_flag = False
                    event.accept()
                else:
                    event.ignore()
                    return
        event.accept()

    # 已完成界面样式
    def finisher_widget_UI(self):
        table_layout = QHBoxLayout()
        self.finish_table_widget = finish_table_widget = QTableWidget(0, 4)  # (行，列)
        table_header = [
            {"field": "bvid", "text": "BV号", 'width': 260},
            {"field": "name", "text": "名称", 'width': 400},
            {"field": "delete", "text": "", 'width': 100},
            {"field": "dir_path", "text": "", 'width': 90},
        ]
        for idx, info in enumerate(table_header):  # idx起始默认0，info代表每个字典
            item = QTableWidgetItem()
            item.setText(info['text'])
            finish_table_widget.setHorizontalHeaderItem(idx, item)
            finish_table_widget.setColumnWidth(idx, info['width'])
        # 显示水平表头
        finish_table_widget.horizontalHeader().setVisible(True)
        # 表头显示分割线
        finish_table_widget.setShowGrid(True)
        # 表头显示数字
        finish_table_widget.verticalHeader().setVisible(True)
        finish_table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.init_finish_table()

        # 开启右键设置(开启右键复制功能， 在表格中点击右键时， 自动触发 right_menu 函数)
        finish_table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        finish_table_widget.customContextMenuRequested.connect(self.finish_table_right_menu)

        table_layout.addWidget(finish_table_widget)

        self.finished_widget.setLayout(table_layout)

    def init_finish_table(self):
        try:
            sql = "SELECT * FROM download_video_list WHERE finish_flag >= 100"
            lock.acquire()
            cursor.execute(sql)
            video_info_list = cursor.fetchall()
            print("已完成下载的视频列表：",video_info_list)
            lock.release()

            # print(current_row_count)
            for row_list in video_info_list:
                item_video = {}
                print(row_list)
                # 写真实数据
                item_video['bvid'] = row_list[1]
                item_video['video_url'] = row_list[0]
                item_video['video_title'] = row_list[2]
                self.add_finish_table_item(item_video)

        except Exception as e:
            QMessageBox.warning(self, "错误", "未能获取到数据")

    def add_finish_table_item(self, item_video):
        current_row_count = self.finish_table_widget.rowCount()
        print(current_row_count)
        self.finish_table_widget.insertRow(current_row_count)
        self.finish_table_widget.setRowHeight(current_row_count, 20)

        # 设置bvid
        bvid_item = QTableWidgetItem(item_video['bvid'])
        bvid_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bvid_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.finish_table_widget.setItem(current_row_count, 0, bvid_item)

        # 设置标题
        title_item = QTableWidgetItem(item_video['video_title'])
        title_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.finish_table_widget.setItem(current_row_count, 1, title_item)

        # 删除按钮
        delete_button = QPushButton(self.cancel_icon, ".", self) #"."原来是"删除"
        delete_button.setStyleSheet("border:none; color:transparent")
        delete_button.clicked.connect(lambda: self.delete_progress(item_video['bvid']))

        # 打开文件夹按钮
        find_dir_button = QPushButton(self.dir_icon, ".", self) #"."原来是"目录"
        find_dir_button.setStyleSheet("border:none;color:transparent")
        find_dir_button.clicked.connect(lambda: self.find_dir(item_video['video_url']))

        self.finish_table_widget.setCellWidget(current_row_count, 2, delete_button)
        self.finish_table_widget.setCellWidget(current_row_count, 3, find_dir_button)

    def delete_progress(self, bvid):
        #事件发送,有时候我们会想知道是哪个组件发出了一个信号，PyQt5里的sender()方法能搞定这件事
        button = self.finish_table_widget.sender()
        index = self.finish_table_widget.indexAt(button.pos())
        current_row_count = index.row()
        A = QMessageBox.warning(self, '警告', '是否确定要删除下载记录', QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No)
        if A == QMessageBox.Yes:
            lock.acquire()
            try:
                sql = "DELETE FROM download_video_list WHERE bvid = ?"
                values = (bvid,)
                cursor.execute(sql, values)
                conn.commit()
                self.finish_table_widget.removeRow(current_row_count)
            except:
                conn.rollback()
                QMessageBox.warning(self, "错误", "删除视频未成功")
            lock.release()
        else:
            return

    def find_dir(self, video_url):
        try:
            sql = 'SELECT save_path FROM download_video_list WHERE video_url = ? limit 1'
            values = (video_url,)
            lock.acquire()
            cursor.execute(sql, values)
            result = cursor.fetchall()
            lock.release()
            if result and result[0][0]:
                save_path = result[0][0]
                folder_path = os.path.dirname(save_path)  #获取文件所在目录
                os.startfile(folder_path)  #打开目录
            else:
                QMessageBox.warning(self, "错误", "未找到保存路径")
            print("保存的路径：", save_path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开目录失败: {str(e)}")

    def finish_table_right_menu(self, pos):
        # 只有选中一行时，才支持右键
        selected_item_list = self.finish_table_widget.selectedItems()
        if len(selected_item_list) == 0:
            return

        # 创建菜单
        menu = QMenu()
        item_open = menu.addAction("打开所在文件夹")
        item_delete = menu.addAction("删除记录")    # 删除记录，但不删除已下载好的文件

        # action表示选中了哪个
        action = menu.exec_(self.finish_table_widget.mapToGlobal(pos))
        # row_index = selected_item_list[0].row()  # 选中的当前行
        # processbar = self.table_widget.cellWidget(row_index, 1)

        if action == item_open:
            for item in selected_item_list:
                row_index = item.row()  # 选中的当前行
                bvid = self.finish_table_widget.item(row_index, 0).text()
                try:
                    sql = "SELECT save_path FROM download_video_list WHERE bvid = ?"
                    values = (bvid,)
                    lock.acquire()
                    cursor.execute(sql, values)
                    save_path = cursor.fetchall()[0][0]
                    lock.release()
                    folder_path = os.path.dirname("{}\\".format(save_path))  # 获取文件所在文件夹路径
                    os.startfile(folder_path)  # 打开文件夹
                except:
                    QMessageBox.warning(self, "错误", "目录不存在或者已删除")


        if action == item_delete:
            selected_item_list.reverse()
            A = QMessageBox.warning(self, '警告', '是否确定要删除该视频', QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
            if A == QMessageBox.Yes:
                for item in selected_item_list:
                    row_index = item.row()
                    bvid = self.finish_table_widget.item(row_index, 0).text()
                    lock.acquire()
                    try:
                        sql = "DELETE FROM download_video_list WHERE bvid = ?"
                        values = (bvid,)
                        cursor.execute(sql, values)
                        conn.commit()
                        self.finish_table_widget.removeRow(row_index)
                    except:
                        conn.rollback()
                        QMessageBox.warning(self, "错误", "视频删除失败")
                    lock.release()
            else:
                return
