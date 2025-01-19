# 获取哔哩哔哩直播的真实流媒体地址，默认获取直播间提供的最高画质 qn=150高清 qn=250超清 qn=400蓝光 qn=10000原画

import requests
from PyQt5.QtCore import QThread, pyqtSignal


class GetInfoThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    success = pyqtSignal(int, str, str, str, str)
    error = pyqtSignal(str)

    def __init__(self, row_index, rid, drop_box_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_index = row_index
        self.rid = rid
        self.header = {
            'User-Agent': "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36",
        }
        self.drop_box_text = drop_box_text

        # 真实房间号
        self.real_room_id = None
        self.name = None
        self.proxies = [
            {"http": "http://10.10.1.10:3128"},
            {"http": "http://10.10.1.11:3128"},
            # ...
        ]

    def run(self):
        # 具体线程需要做的事
        try:
            # 先获取直播状态和真实房间号以及主播名称
            r_url = 'https://api.live.bilibili.com/room/v1/Room/room_init'

            param = {
                'id': self.rid
            }
            with requests.Session() as self.s:
                import random
                proxy = random.choice(self.proxies)
                res = self.s.get(r_url, headers=self.header,proxies=proxy,  params=param).json()
            if res['msg'] == '直播间不存在':
                # self.room_exit_flag = False
                raise Exception(f'bilibili {self.rid} {res["msg"]}')

            self.real_room_id = res['data']['room_id']  # 真实直播间ID
            name_url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id=' + str(self.real_room_id)
            proxy = random.choice(self.proxies)
            proxy = random.choice(self.proxies)
            res2 = self.s.get(name_url, headers=self.header,proxies=proxy).json()
            self.name = res2['data']['anchor_info']['base_info']['uname']
            live_status = res['data']['live_status']
            # self.room_exit_flag = True
            if live_status != 1:
                self.success.emit(self.row_index, self.drop_box_text, self.rid, self.name, "监测中")
            else:
                # 获取到房间号，主播名称和直播状态，将这个信息填写到表格和写入文件中(self, row_index, platform, room_id, name, live_status)
                self.success.emit(self.row_index, self.drop_box_text, self.rid, self.name, "录制中")
        except Exception as e:
            # if self.room_exit_flag:
            #     self.not_live.emit(self.row_index, self.drop_box_text, self.rid, self.name, "尚未开播")
            self.error.emit(str(e))
