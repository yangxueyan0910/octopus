import time

from PyQt5.QtCore import QThread, pyqtSignal


class StopThread(QThread):

    def __del__(self):
        print('del')

    update_signal = pyqtSignal(str)

    def __init__(self, total, scheduler,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = scheduler
        self.total = total

    def run(self):

        # 1 监测线程的数量(总的线程数)
        # total_count = len(self.scheduler.thread_list)
        # total_count = self.scheduler.total
        while True:
            # 当前运行的线程数
            running_count = len(self.scheduler.thread_list)
            # running_count = self.running_count
            self.update_signal.emit("正在终止({}/{})".format(self.total-running_count, self.total))
            # 更新到页面上
            if running_count == 0:
                break

            time.sleep(5)

        self.update_signal.emit("已终止")
