from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QLabel

# 连接数据库
import connect
cursor, conn, lock = connect.connect()

class SettingDialog(QDialog):
    success = pyqtSignal(str)
    def __init__(self, num):
        super().__init__()
        self.num = num
        self.setWindowTitle('自定义')
        self.setWindowIcon(QIcon(':/favicon.ico'))
        self.resize(300, 100)

        # 创建垂直布局
        layout = QVBoxLayout()

        # 创建输入框
        self.edit = QLineEdit(f"自定义{self.num}")
        layout.addWidget(self.edit)

        self.label = QLabel()
        self.label.setStyleSheet('color:red; font-size:smaller')
        layout.addWidget(self.label)

        btn_layout = QHBoxLayout()
        # 创建取消按钮
        cancel_button = QPushButton('取消')
        cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_button)

        # 创建确认按钮
        ok_button = QPushButton('确认')
        ok_button.clicked.connect(self.accept)
        btn_layout.addWidget(ok_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def accept(self):
        self.label.setText("")
        try:
            sql = "SELECT COUNT(*) FROM live_setting WHERE name = ? LIMIT 1"
            values = (self.edit.text(),)
            lock.acquire()
            cursor.execute(sql, values)
            count = cursor.fetchone()[0]
            if count == 0:
                self.success.emit(self.edit.text())
                self.close()
            else:
                self.label.setText("该名称已存在")
        except Exception as e:
            QMessageBox.warning(self, "错误", "未能获取到数据")
            lock.release()
        lock.release()
