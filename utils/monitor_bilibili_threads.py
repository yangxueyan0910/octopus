import time
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

class MonitorInfoThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    live_status = pyqtSignal(int, str, str, str)

    def __init__(self, list_scheduler, row_index, rid, platform, live_status, *args, **kwargs):
        super(MonitorInfoThread, self).__init__(*args, **kwargs)
        self.row_index = row_index
        self.rid = rid
        self.platform = platform
        self.previous_live_status = live_status
        self.list_scheduler = list_scheduler
        self.s = requests.Session()
        self.proxies = [

    {"http":"http://169.254.253.133/16"}
    # ...
]

        self.header = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }

        # 真实房间号
        self.real_room_id = None
        self.name = None
        self.recent_live_satus = self.previous_live_status
        self.monitor_person_thread = None

    import time

    def run(self):
        # 加入开始人物监测的线程
        from utils.monitor_person import MonitorPersonThread

        try:
            # 先获取直播状态和真实房间号以及主播名称
            r_url = 'https://api.live.bilibili.com/room/v1/Room/room_init'
            param = {
                'id': self.rid
            }
            record_flag = True
            while True:
                print(40, self.rid)

                if self.list_scheduler.terminate:
                    try:
                        if self.monitor_person_thread is not None:
                            self.monitor_person_thread.quit()
                            self.monitor_person_thread.wait()
                    except Exception as e:
                        print("Error while terminating monitor_person_thread:", e)

                    print(f"房间号：{self.rid}, 已停止监测")
                    self.list_scheduler.destroy_thread(self)
                    super().quit()
                    break

                print("bilibili:", self.list_scheduler.item_terminate_flag[self.row_index])
                if self.list_scheduler.item_terminate_flag[self.row_index]:
                    try:
                        if self.monitor_person_thread is not None:
                            print(57)
                            self.monitor_person_thread.terminate_flag = True
                            self.monitor_person_thread.quit()
                            self.monitor_person_thread.wait()
                    except Exception as e:
                        print("Error while terminating monitor_person_thread:", e)

                    self.list_scheduler.destroy_thread(self)
                    try:
                        self.live_status.emit(self.row_index, self.platform, self.rid, "已停止")
                    except Exception as e:
                        print("Error while emitting live status:", e)

                    print(f"房间号：{self.rid}, 已停止监测")
                    break

                try:
                    import random
                    proxy = random.choice(self.proxies)
                    res = self.s.get(url=r_url, headers=self.header, params=param, proxies=proxy, timeout=100).json()

                    if res['msg'] == '直播间不存在':
                        raise Exception
                    live_status = res['data']['live_status']
                    print(56, live_status)
                    if live_status != 1:
                        self.recent_live_satus = "监测中"
                    else:
                        self.recent_live_satus = "录制中"
                        if self.previous_live_status == "录制中":
                            if record_flag:
                                record_flag = False
                                self.real_room_id = res['data']['room_id']
                                rtmp_urls, name = self.get_real_url()
                                rtmp_url = rtmp_urls['线路1'].split("?")[0]
                                print(rtmp_url)
                                print("开始进行人物目标监测")
                                self.monitor_person_thread = MonitorPersonThread(base_dir=self.list_scheduler.base_dir,
                                                                                 rtmp_url=rtmp_url, name=name,
                                                                                 rid=self.rid)
                                self.monitor_person_thread.person_status.connect(self.monitor_callback)
                                self.monitor_person_thread.start()
                except Exception as e:
                    print("Error:", e)

                try:
                    print(self.recent_live_satus, self.previous_live_status)
                    if self.recent_live_satus != self.previous_live_status:
                        if live_status != 1:
                            self.live_status.emit(self.row_index, self.platform, self.rid, "监测中")
                            self.previous_live_status = self.recent_live_satus
                            if self.monitor_person_thread is not None:
                                self.monitor_person_thread.terminate_flag = True
                        else:
                            self.live_status.emit(self.row_index, self.platform, self.rid, "录制中")
                            self.previous_live_status = self.recent_live_satus
                            record_flag = True
                except Exception as e:
                    print("Error:", e)

                time.sleep(5)
        except Exception as e:
            import cgitb
            cgitb.enable(format='text')
            # QMessageBox.warning(self.list_scheduler.window, '错误', f'房间号：{self.rid}的直播状态获取未成功')

    def monitor_callback(self, info):
        self.live_status.emit(self.row_index, self.platform, self.rid, info)

    def get_real_url(self, current_qn: int = 10000) -> dict:
        url = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo'
        param = {
            'room_id': self.real_room_id,
            'protocol': '0,1',
            'format': '0,1,2',
            'codec': '0,1',
            'qn': current_qn,
            'platform': 'h5',
            'ptype': 8,
        }
        import random
        proxy = random.choice(self.proxies)
        res = self.s.get(url, headers=self.header, proxies=proxy,params=param).json()
        stream_info = res['data']['playurl_info']['playurl']['stream']
        qn_max = 0

        for data in stream_info:
            accept_qn = data['format'][0]['codec'][0]['accept_qn']
            for qn in accept_qn:
                qn_max = qn if qn > qn_max else qn_max
        if qn_max != current_qn:
            param['qn'] = qn_max
            res = self.s.get(url, headers=self.header,proxies=proxy, params=param).json()
            stream_info = res['data']['playurl_info']['playurl']['stream']

        name_url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id=' + str(self.real_room_id)
        res2 = self.s.get(name_url, headers=self.header ,proxies=proxy).json()
        name = res2['data']['anchor_info']['base_info']['uname']

        stream_urls = {}
        # flv流无法播放，暂修改成获取hls格式的流，
        for data in stream_info:
            format_name = data['format'][0]['format_name']
            if format_name == 'ts':
                base_url = data['format'][-1]['codec'][0]['base_url']
                url_info = data['format'][-1]['codec'][0]['url_info']
                for i, info in enumerate(url_info):
                    host = info['host']
                    extra = info['extra']
                    stream_urls[f'线路{i + 1}'] = f'{host}{base_url}{extra}'
                break
        return stream_urls, name





