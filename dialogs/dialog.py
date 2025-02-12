import time
from octopus import connect

from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QPushButton, QCheckBox, QMessageBox, QHBoxLayout, \
    QLineEdit, QTableWidgetItem, QTableWidget, QHeaderView, QStyleOptionButton, QStyle, QWidget, QStyleOptionHeader

from octopus.dialogs.download_window.download_window import DownloadVideosWindow
# 连接数据库
cursor, conn, lock = connect.connect()

all_header_combobox = []

class GetVideosWindow(QWidget):
    download_window = None
    def __init__(self, basedir, *args, **kwargs):
        super(GetVideosWindow, self).__init__(*args, **kwargs)
        self.thread = None
        self.txt_url = None
        self.basedir = basedir
        self.if_check = False
        self.table_widget = None
        self.label_status = None
        self.current_row_count = None
        self.init_ui()
        self.videos_url_list = []

    def init_ui(self):
        # 窗体logo
        # self.setWindowIcon(QIcon('asset/favicon.ico'))
        # self.setWindowTitle("视频下载")
        # self.resize(650, 400)

        layout = QVBoxLayout()

        # lbl = QLabel()
        # lbl.setText("网页链接")
        # layout.addWidget(lbl)
        top_layout = QHBoxLayout()
        self.btn_manage = btn_manage = QPushButton("下载管理")
        btn_manage.clicked.connect(self.event_download_manage)
        top_layout.addWidget(btn_manage)

        self.btn_setting = btn_setting = QPushButton("下载设置")
        btn_setting.clicked.connect(self.event_download_setting)
        top_layout.addWidget(btn_setting)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        header_layout = QHBoxLayout()
        self.txt = txt = QLineEdit()
        txt.setPlaceholderText("请输入需要下载视频的网页链接，如“https://www.bilibili.com/video/BV1HY4y1979a/?vd_source=4fc11458c5546fcf32498390ea8879f6”")
        self.txt_url = txt
        header_layout.addWidget(txt)

        self.btn_analysis = btn_analysis = QPushButton("解析")
        btn_analysis.clicked.connect(self.event_analysis_click)
        header_layout.addWidget(btn_analysis, 0, Qt.AlignRight)
        layout.addLayout(header_layout)

        # 合集列表表格布局
        table_layout = QHBoxLayout()
        # 创建表格
        self.table_widget = table_widget = QTableWidget(0, 2)  # (行，列)

        header_field = ['', '视频列表']
        self.header = header = CheckBoxHeader()  # 自定义了表头类
        table_widget.setHorizontalHeader(header)  # 在表头中添加控件（如复选框）
        table_widget.setHorizontalHeaderLabels(header_field)  # 设置行表头字段
        table_widget.setColumnWidth(0, 30)  # 设置第0列宽度
        table_widget.setColumnWidth(1, 1400)  # 设置第1列宽度
        header.select_all_clicked.connect(header.change_state)  # 行表头复选框单击信号与槽

        table_layout.addWidget(table_widget)
        layout.addLayout(table_layout)

        # 底部状态信息和按钮
        footer_layout = QHBoxLayout()
        self.label_status = label_status = QLabel("就绪", self)
        footer_layout.addWidget(label_status)

        self.btn_save = btn_save = QPushButton("下载")
        btn_save.clicked.connect(self.event_download_click)
        footer_layout.addWidget(btn_save, 0, Qt.AlignRight)

        layout.addLayout(footer_layout)

        self.setLayout(layout)

    def event_download_setting(self):
        pass

    def event_analysis_click(self):
        self.btn_analysis.setEnabled(False)
        self.btn_save.setEnabled(False)
        # 清空表格、复选框和视频列表
        self.table_widget.setRowCount(0)
        self.table_widget.clearContents()  # 清空QTableWidget中的数据
        all_header_combobox.clear()
        self.videos_url_list.clear()  #确保清空旧数据
        url = self.txt_url.text()
        if not url:
            self.init_task_info_callback("网页链接不能为空!")
            self.btn_analysis.setEnabled(True)
            self.btn_save.setEnabled(True)
            print(self.label_status)
            return
        print("正在解析链接url: ", url)
        from octopus.dialogs.utils.analysis_url_threads import AnalysisUrlThread
        self.thread = thread = AnalysisUrlThread(url, self)
        thread.process.connect(self.init_task_info_callback)
        thread.success.connect(self.init_table_callback)
        thread.start()

    def event_download_manage(self):
        if not GetVideosWindow.download_window:
            GetVideosWindow.download_window = DownloadVideosWindow(self.basedir)
        GetVideosWindow.download_window.show()

    def event_download_click(self):
        if not GetVideosWindow.download_window:
            GetVideosWindow.download_window = DownloadVideosWindow(self.basedir)

        #获取下载窗口的实例
        download_window = GetVideosWindow.download_window
        download_window.show()

        #确保已将需要下载的视频项添加到下载窗口的表格中，再触发下载
        def delayed_start():
            #初始化表格（从数据库加载未完成的任务）
            download_window.init_table()
            #再触发自动下载
            download_window.event_all_start(automatic=True)

        #使用定时器延迟执行，确保UI更新完成
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, delayed_start)  #延迟100毫秒确保UI加载完

        #选中的视频数量
        counter = 0
        #需要下载的视频列表
        download_videos_list = []
        #获取选中数据
        for i in range(self.table_widget.rowCount()):
            if self.table_widget.cellWidget(i, 0).isChecked():
                counter += 1
                try:
                    bvid = self.videos_url_list[i]['bvid']
                    video_url = self.videos_url_list[i]['video_url']  #新增获取 video_url
                    sql = "SELECT COUNT(*) FROM download_video_list WHERE video_url = ? LIMIT 1"
                    values = (video_url,)
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
                    if result is not None and result[0] == 0:
                        if counter == 1:
                            GetVideosWindow.download_window.show()

                        lock.acquire()
                        try:
                            video_url = self.videos_url_list[i]['video_url']
                            video_title = self.videos_url_list[i]['video_title']
                            finish_flag = 0
                            self.videos_url_list[i]['finish_flag'] = finish_flag
                            sql_insert = "INSERT INTO download_video_list( bvid,video_url, video_title, finish_flag, save_path) VALUES (?, ?, ?, ?, ?)"
                            values = ( bvid, video_url,video_title, finish_flag, "暂未设置")
                            cursor.execute(sql_insert, values)
                            conn.commit()

                            GetVideosWindow.download_window.add_table_item(self.videos_url_list[i])
                            download_videos_list.append(self.videos_url_list[i])
                        except Exception as e:
                            conn.rollback()
                            print(e)
                            QMessageBox.warning(self, "错误", "数据插入未成功")
                        finally:
                            lock.release()
                    else:
                        print("警告：第{}行数据已存在于下载列表".format(i + 1))
                except Exception as e:
                    print(e)
        if counter <= 0:
            QMessageBox.warning(self, "警告", "当前未选中任何数据")
        else:
            pass

    def init_table_callback(self, title, video_url, bvid):
        self.current_row_count = self.table_widget.rowCount()
        print(self.current_row_count)
        self.table_widget.insertRow(self.current_row_count)

        # 单元格添加复选框
        cell_checkbox = QCheckBox()
        cell_checkbox.setChecked(True)
        cell_checkbox.stateChanged.connect(self.check_all_checked)
        # 将所有的复选框都添加到 全局变量 all_header_combobox 中
        all_header_combobox.append(cell_checkbox)
        # 为每一行添加复选框
        self.table_widget.setCellWidget(self.current_row_count, 0, cell_checkbox)

        # 单元格添加标题
        cell_title = QTableWidgetItem(title)
        cell_title.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        cell_title.setTextAlignment(Qt.AlignLeft| Qt.AlignVCenter)
        self.table_widget.setItem(self.current_row_count, 1, cell_title)

        video_info = {}
        video_info['video_url'] = video_url
        video_info['video_title'] = title
        video_info['bvid'] = bvid
        # 将视频链接添加进列表
        self.videos_url_list.append(video_info)
        print(video_info)

    # 检查所有复选框是否被选中
    def check_all_checked(self):
        for i in all_header_combobox:
            #若有一个及以上未选中，则取消全选
            if not i.isChecked():
                self.header.set_isOn(False)
                return
        self.header.set_isOn(True)


    def init_task_info_callback(self, message):
        self.label_status.setText(message)
        self.label_status.repaint()
        print(message)
        if message == "解析完成":
            self.check_all_checked()
            self.btn_analysis.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.txt.setText("")
        if message == "解析异常":
            QMessageBox.warning(self, '警告', '您输入的网页链接解析异常，请重新输入')
            self.btn_analysis.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.txt.setText("")

    def closeEvent(self, event):
        if self.thread is not None:
            if self.thread.isRunning():
                A = QMessageBox.warning(self, '警告', '您有正在解析的进程，是否确认关闭窗口', QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No)
                if A == QMessageBox.Yes:
                    self.thread.stop = True
                    event.accept()
                else:
                    event.ignore()
                    return
        event.accept()

class CheckBoxHeader(QHeaderView):
    """自定义表头类"""
    # 自定义 复选框全选信号
    select_all_clicked = pyqtSignal(bool)
    # 这4个变量控制列头复选框的样式，位置以及大小
    _x_offset = 0
    _y_offset = 0
    _width = 16
    _height = 16

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(CheckBoxHeader, self).__init__(orientation, parent)
        self.isOn = False
    def paintSection(self, painter, rect, logicalIndex): #负责绘制表头部分
        # 仅对第0列（复选框列）调用父类绘制
        if logicalIndex != 1:
            painter.save()
            super(CheckBoxHeader, self).paintSection(painter, rect, logicalIndex)
            painter.restore()

        self._y_offset = int((rect.height() - self._width) / 2.)

        # 处理复选框列（索引0）
        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(rect.x() + self._x_offset, rect.y() + self._y_offset, self._width, self._height)
            option.state = QStyle.State_Enabled | QStyle.State_Active
            if self.isOn:
                option.state |= QStyle.State_On
            else:
                option.state |= QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)
        # 处理文本列（索引1）
        elif logicalIndex == 1:
            option = QStyleOptionHeader()
            self.initStyleOption(option)
            option.textAlignment = Qt.AlignLeft | Qt.AlignVCenter  # 强制左对齐
            option.text = self.model().headerData(logicalIndex, self.orientation(), Qt.DisplayRole)
            option.rect = rect.adjusted(5, 0, -5, 0)  # 左右边距调整
            painter.save()
            self.style().drawControl(QStyle.CE_Header, option, painter)
            painter.restore()

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if 0 == index:
            x = self.sectionPosition(index)
            if x + self._x_offset < event.pos().x() < x + self._x_offset + self._width and self._y_offset < event.pos().y() < self._y_offset + self._height:
                if self.isOn:
                    self.isOn = False
                else:
                    self.isOn = True
                    # 当用户点击了行表头复选框，发射 自定义信号 select_all_clicked()
                self.select_all_clicked.emit(self.isOn)

                self.updateSection(0)
        super(CheckBoxHeader, self).mousePressEvent(event)

    # 自定义信号 select_all_clicked 的槽方法
    def change_state(self, isOn):
        # 如果行表头复选框为勾选状态
        if isOn:
            # 将所有的复选框都设为勾选状态
            for i in all_header_combobox:
                i.setCheckState(Qt.Checked)
        else:
            for i in all_header_combobox:
                i.setCheckState(Qt.Unchecked)

    def set_isOn(self, status):
        self.isOn = status
        self.updateSection(0)
