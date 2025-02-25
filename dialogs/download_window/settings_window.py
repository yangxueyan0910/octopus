from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox,
                             QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt
import connect
cursor, conn, lock = connect.connect()

class DownloadSettingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("下载设置")
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.resize(650, 220)
        self.init_ui()
        self.load_settings()
        self.setStyleSheet("""
                   QWidget {
                       font-size: 14px;
                   }
                   QLabel {
                       min-width: 100px;
                   }
                   QSpinBox {
                       padding: 5px;
                   }
                   QPushButton {
                       padding: 8px;
                       min-width: 80px;
                   }
               """)
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20) #设置边距

        #路径设置组
        path_group=QGroupBox("")
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(10,15,10,15)
        path_layout.setSpacing(15)

        self.lbl_path = QLabel("保存路径:")
        self.txt_path = QLineEdit()
        self.txt_path.setPlaceholderText("请选择视频保存路径")
        self.btn_choose = QPushButton("浏览")
        self.btn_choose.clicked.connect(self.choose_path)

        path_layout.addWidget(self.lbl_path)
        path_layout.addWidget(self.txt_path,stretch=5)
        path_layout.addWidget(self.btn_choose,stretch=1)
        path_group.setLayout(path_layout)


        #并发设置组
        concurrent_group=QGroupBox("")
        concurrent_layout = QHBoxLayout()
        concurrent_layout.setContentsMargins(10,15,10,15)
        concurrent_layout.setSpacing(15)

        self.lbl_concurrent = QLabel("下载并发数:")
        self.spn_concurrent = QSpinBox()
        self.spn_concurrent.setFixedWidth(80)
        self.spn_concurrent.setRange(1, 5)
        concurrent_layout.addWidget(self.lbl_concurrent)
        concurrent_layout.addWidget(self.spn_concurrent)
        concurrent_layout.addStretch()
        concurrent_group.setLayout(concurrent_layout)

        #按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存设置")
        self.btn_save.setFixedWidth(100)
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)

        main_layout.addWidget(path_group)
        main_layout.addWidget(concurrent_group)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def choose_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.txt_path.setText(path)

    def load_settings(self):
        lock.acquire()
        try:
            cursor.execute("SELECT save_path, max_concurrent FROM download_settings WHERE id=1")
            result = cursor.fetchone()
            if result:
                self.txt_path.setText(result[0] or "")
                self.spn_concurrent.setValue(result[1] or 3)
        finally:
            lock.release()

    def save_settings(self):
        path = self.txt_path.text()
        concurrent = self.spn_concurrent.value()

        lock.acquire()
        try:
            cursor.execute(
                "UPDATE download_settings SET save_path=?, max_concurrent=? WHERE id=1",
                (path, concurrent)
            )
            conn.commit()
            QMessageBox.information(self, "提示", "设置保存成功")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
        finally:
            lock.release()