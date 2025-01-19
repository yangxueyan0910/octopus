import time

import connect
from asset import resources

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QMessageBox, QHBoxLayout, \
    QTableWidgetItem, QTableWidget, QWidget, \
    QMenu

# 连接数据库
cursor, conn, lock = connect.connect()

class LiveManageWindow(QWidget):

    move_success = pyqtSignal(str, str)

    def __init__(self, basedir, *args, **kwargs):
        super(LiveManageWindow, self).__init__(*args, **kwargs)
        self.basedir = basedir
        self.if_check = False
        self.table_widget = None
        self.init_ui()

    def init_ui(self):
        # 窗体logo
        self.setWindowIcon(QIcon(':/favicon.ico'))
        self.setWindowTitle("主播管理")
        self.resize(500, 400)

        layout = QVBoxLayout()

        # 合集列表表格布局
        table_layout = QHBoxLayout()
        # 创建表格
        self.table_widget = table_widget = QTableWidget(0, 3)  # (行，列)

        table_header = [
            {"field": "platform", "text": "直播平台", 'width': 100},
            {"field": "room_id", "text": "房间号", 'width': 120},
            {"field": "name", "text": "主播名称", 'width': 220}
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
        layout.addLayout(table_layout)

        self.setLayout(layout)

    def table_right_menu(self, pos):
        # 只有选中行时，才支持右键
        selected_item_list = self.table_widget.selectedItems()
        if len(selected_item_list) == 0:
            return

        # 创建菜单
        menu = QMenu()
        item_move = menu.addAction("移入监测")
        item_delete = menu.addAction("删除主播")

        # action表示选中了哪个
        action = menu.exec_(self.table_widget.mapToGlobal(pos))

        if action == item_move:
            # 移回主播
            selected_item_list.reverse()
            A = QMessageBox.warning(self, '警告', '是否确定要移回监测', QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
            if A == QMessageBox.Yes:
                for item in selected_item_list:
                    row_index = item.row()
                    platform = self.table_widget.item(row_index, 0).text().strip()
                    room_id = self.table_widget.item(row_index, 1).text().strip()
                    try:
                        sql = "UPDATE live_list_info SET flag = ? WHERE platform = ? and room_id = ?"
                        values = (0, platform, room_id)
                        lock.acquire()
                        cursor.execute(sql, values)
                        conn.commit()

                        self.table_widget.removeRow(row_index)
                        self.move_success.emit(platform, room_id)
                    except:
                        conn.rollback()
                        QMessageBox.warning(self, "错误", "删除主播未成功")
                    lock.release()
            else:
                return

        if action == item_delete:
            # 删除主播
            selected_item_list.reverse()
            A = QMessageBox.warning(self, '警告', '是否确定要删除视频', QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
            if A == QMessageBox.Yes:
                for item in selected_item_list:
                    row_index = item.row()
                    platform = self.table_widget.item(row_index, 0).text().strip()
                    room_id = self.table_widget.item(row_index, 1).text().strip()
                    try:
                        sql = "DELETE FROM live_list_info WHERE platform=? and room_id=?"
                        values = (platform, room_id)
                        lock.acquire()
                        cursor.execute(sql, values)
                        conn.commit()

                        self.table_widget.removeRow(row_index)
                    except:
                        conn.rollback()
                        QMessageBox.warning(self, "错误", "删除主播未成功")
                    lock.release()
            else:
                return

    def init_all_info(self):
        try:
            sql = "SELECT * FROM live_list_info WHERE flag = 1"
            lock.acquire()
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
                    if i > 3:
                        continue
                    self.table_widget.setItem(current_row_count, i, cell)
                current_row_count += 1

        except Exception as e:
            QMessageBox.warning(self, "错误", "未能获取到数据")
        lock.release()