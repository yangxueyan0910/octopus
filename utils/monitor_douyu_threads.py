import hashlib
import re
import time

import requests
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import quickjs
    use_quickjs = True
except ImportError:
    import execjs
    use_quickjs = False

class MonitorInfoThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    live_status = pyqtSignal(int, str, str, str)

    def __init__(self, list_scheduler, row_index, rid, platform, live_status, *args, **kwargs):
        super(MonitorInfoThread, self).__init__(*args, **kwargs)
        self.did = '10000000000000000000000000001501'
        self.t10 = str(int(time.time()))
        self.t13 = str(int((time.time() * 1000)))
        self.row_index = row_index
        self.rid = rid
        self.platform = platform
        self.previous_live_status = live_status
        self.list_scheduler = list_scheduler
        self.s = requests.Session()

        self.header = {
            'User-Agent': 'Mozilla/5.0 (iPod; CPU iPhone OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                          'like Gecko) CriOS/87.0.4280.163 Mobile/15E148 Safari/604.1',
        }

        # 真实房间号
        self.name = None
        self.recent_live_satus = self.previous_live_status

    def run(self):
        # 具体线程需要做的事
        # 斗鱼进行线程监测
        try:
            record_flag = True
            while True:
                print("douyu: ", self.list_scheduler.terminate)
                if self.list_scheduler.terminate:
                    self.list_scheduler.destroy_thread(self)
                    print(f"房间号：{self.rid}, 已停止检测")
                    return

                if self.list_scheduler.item_terminate_flag[self.row_index]:
                    self.list_scheduler.destroy_thread(self)
                    self.live_status.emit(self.row_index, self.platform, self.rid, "已停止")
                    print(f"房间号：{self.rid}, 已停止检测")
                    return

                live_status = self.get_pre()[0]
                if live_status == 0:
                    self.recent_live_satus = "录制中"
                    # 正在直播就开始录制，并且设置录制标志位false，即仅循环一次
                    if record_flag:
                        key = self.get_pre()[1]
                        record_flag = False
                        name = self.get_name()
                        rtmp_url = "http://hw-tct.douyucdn.cn/live/{}.flv?uuid=".format(key)
                        # 加入开始录制的线程
                        from windows.start_record_threads import StartRecordThread
                        record_thread = StartRecordThread(base_dir=self.list_scheduler.base_dir,
                                                          rtmp_url=rtmp_url, name=name)
                        record_thread.start()
                elif live_status == 102:
                    raise Exception
                elif live_status == 104:  # 主播未开播
                    self.recent_live_satus = "监测中"
                else:
                    self.recent_live_satus = "录制中"
                    # 正在直播就开始录制，并且设置录制标志位false，即仅循环一次
                    if record_flag:
                        key = self.get_js()
                        record_flag = False
                        name = self.get_name()
                        rtmp_url = "http://hw-tct.douyucdn.cn/live/{}.flv?uuid=".format(key)
                        # 加入开始录制的线程
                        from windows.start_record_threads import StartRecordThread
                        record_thread = StartRecordThread(base_dir=self.list_scheduler.base_dir,
                                                          rtmp_url=rtmp_url, name=name)
                        record_thread.start()

                # 如果当前的直播状态未发生改变，就不发送更新数据, 如果发生改变就发送更新数据
                if self.recent_live_satus != self.previous_live_status:
                    if live_status == 0:
                        # 正在直播就开始录制，并且设置录制标志位false，即仅循环一次
                        if record_flag:
                            key = self.get_pre()[1]
                            record_flag = False
                            name = self.get_name()
                            rtmp_url = key
                            # 加入开始录制的线程
                            from windows.start_record_threads import StartRecordThread
                            record_thread = StartRecordThread(base_dir=self.list_scheduler.base_dir,
                                                              rtmp_url=rtmp_url, name=name)
                            record_thread.start()
                        self.live_status.emit(self.row_index, self.platform, self.rid, "录制中")
                    elif live_status == 102:
                        raise Exception
                    elif live_status == 104:  # 主播未开播
                        self.live_status.emit(self.row_index, self.platform, self.rid, "监测中")
                    else:
                        # 正在直播就开始录制，并且设置录制标志位false，即仅循环一次
                        if record_flag:
                            key = self.get_js()
                            record_flag = False
                            name = self.get_name()
                            rtmp_url = key
                            # 加入开始录制的线程
                            from windows.start_record_threads import StartRecordThread
                            record_thread = StartRecordThread(base_dir=self.list_scheduler.base_dir,
                                                              rtmp_url=rtmp_url, name=name)
                            record_thread.start()
                        self.live_status.emit(self.row_index, self.platform, self.rid, "录制中")
                time.sleep(5)
        except Exception as e:
            import cgitb
            cgitb.enable(format='text')
            # QMessageBox.warning(self.list_scheduler.window, '错误', f'房间号：{self.rid}的直播状态获取未成功')

    @staticmethod
    def md5(data):
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_pre(self):
        url = 'https://playweb.douyucdn.cn/lapi/live/hlsH5Preview/' + self.rid
        data = {
            'rid': self.rid,
            'did': self.did
        }

        auth = self.md5(self.rid + self.t13)
        headers = {
            'rid': self.rid,
            'time': self.t13,
            'auth': auth
        }
        res = self.s.post(url, headers=headers, data=data, timeout=30).json()
        error = res['error']
        data = res['data']
        key = ''
        if data:
            rtmp_live = data['rtmp_live']
            key = re.search(r'(\d{1,8}[0-9a-zA-Z]+)_?\d{0,4}p?(.m3u8|/playlist)', rtmp_live).group(1)
        return error, key

    def get_js(self):
        res1 = self.s.get('https://m.douyu.com/' + str(self.rid), timeout=30).text
        result = re.search(r'(function ub98484234.*)\s(var.*)', res1).group()
        func_ub9 = re.sub(r'eval.*;}', 'strc;}', result)
        if use_quickjs:
            js_func = quickjs.Function('ub98484234', func_ub9)
            res = js_func()
        else:
            js = execjs.compile(func_ub9)
            res = js.call('ub98484234')

        v = re.search(r'v=(\d+)', res).group(1)
        rb = self.md5(self.rid + self.did + self.t10 + v)

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')

        if use_quickjs:
            js_func = quickjs.Function('sign', func_sign)
            params = js_func(self.rid, self.did, self.t10)
        else:
            js = execjs.compile(func_sign)
            params = js.call('sign', self.rid, self.did, self.t10)

        params += '&ver=219032101&rid={}&rate=-1'.format(self.rid)

        url = 'https://m.douyu.com/api/room/ratestream'
        res = self.s.post(url, params=params, timeout=30).json()['data']
        key = re.search(r'(\d{1,8}[0-9a-zA-Z]+)_?\d{0,4}p?(.m3u8|/playlist)', res['url']).group(1)
        print("key: ", key)

        return key

    def get_name(self):
        # 获取主播名称
        api_url = 'https://www.douyu.com/yuba/wbapi/web/group/roomwhitelist/' + str(self.rid)
        with requests.Session() as s:
            res = s.get(api_url, headers=self.header).json()

        name = res['data']['owner_group']['name']

        return name

