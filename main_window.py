import os
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTabWidget, QDesktopWidget, QApplication

BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
# 连接数据库
# cursor, conn = connect.connect()

class MainShowWindow(QTabWidget):
    def __init__(self, *args, **kwargs):
        super(MainShowWindow, self).__init__(*args, **kwargs)
        self.init_ui()

    def init_ui(self):
        # 窗体标题和尺寸
        self.setWindowTitle('学习行为视频采集系统')
        # 窗体logo
        self.setWindowIcon(QIcon(':/favicon.ico'))
        # 窗体的尺寸
        self.resize(1500, 1000)
        # 窗体的位置
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        # 创建2个选项卡小控件窗口
        from main import MainWindow
        self.live_scraw_widget = MainWindow()

        from dialogs.dialog import GetVideosWindow
        self.videos_download_widget = GetVideosWindow(BASE_DIR)

        # 将2个选项卡添加到顶层窗口中
        self.addTab(self.live_scraw_widget, "直播录制")
        self.addTab(self.videos_download_widget, "视频下载")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainShowWindow()
    window.show()

    sys.exit(app.exec_())
