import datetime
import os
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal


class StartRecordThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    success = pyqtSignal(int, str, str, str, str)
    error = pyqtSignal(str)

    def __init__(self, base_dir, rtmp_url, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rtmp_url = rtmp_url
        self.base_dir = base_dir
        # self.flag = False
        # 主播名称
        self.name = name
        self.record_base_path = os.path.join(base_dir, "live_videos", name)
        self.p = None

    def run(self):
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not os.path.exists(self.record_base_path):
            os.makedirs(self.record_base_path)
        record_path = os.path.join(self.record_base_path, self.name + "_" + now + ".mp4")
        print(now)
        # 屏幕录制指令
        # 改变码率-b:v 改变分辨率-s  改变帧率-r
        # test1 1.01 6mb 1.00 25.9mb
        command = "ffmpeg -i {} -c:v copy -c:a copy -bsf:a aac_adtstoasc {}".format(self.rtmp_url, record_path)
        # test4.1 设置帧率为20fps 1.01 24.2mb   待定1  1.00  33.5mb  1.01 30.7
        # command = "ffmpeg -i {} -r 20 -c:v copy -c:a copy -bsf:a aac_adtstoasc {}".format(self.rtmp_url, record_path)\
        print(command)
        # 执行指令
        self.p = p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)
        # 等待5秒钟（录制5秒钟的视频）
        # time.sleep(60)
        # self.stop_thread()

    def stop_thread(self):
        # 停止录制
        if self.p is not None:
            self.p.stdin.write('q'.encode("GBK"))
            self.p.communicate()
            self.p.kill()
            print('录制完成')
