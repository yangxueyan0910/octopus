import hashlib
import re
import time

import requests

try:
    import quickjs
    use_quickjs = True
except ImportError:
    import execjs
    use_quickjs = False

from PyQt5.QtCore import QThread, pyqtSignal


class GetInfoThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    success = pyqtSignal(int, str, str, str, str)
    error = pyqtSignal(str)

    def __init__(self, row_index, rid, drop_box_text, *args, **kwargs):
        super(GetInfoThread, self).__init__(*args, **kwargs)
        self.row_index = row_index
        self.rid = rid
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        }

        self.drop_box_text = drop_box_text
        self.name = None

        self.did = '10000000000000000000000000001501'
        self.t10 = str(int(time.time()))
        self.t13 = str(int((time.time() * 1000)))

        self.s = requests.Session()
        self.res = self.s.get('https://m.douyu.com/' + str(rid), timeout=30).text
        result = re.search(r'rid":(\d{1,8}),"vipId', self.res)

        if result:
            self.rid = result.group(1)
        else:
            raise Exception('房间号错误')

    def run(self):
        try:
            print(50)
            # 获取主播名称
            api_url = 'https://www.douyu.com/yuba/wbapi/web/group/roomwhitelist/' + str(self.rid)
            with requests.Session() as s:
                res = s.get(api_url, headers=self.header).json()

            self.name = res['data']['owner_group']['name']
            print(self.name)

            error = self.get_pre()
            if error == 0:
                self.success.emit(self.row_index, self.drop_box_text, self.rid, self.name, "录制中")
            elif error == 102:
                raise Exception('主播间不存在')
            elif error == 104:  # 主播未开播
                self.success.emit(self.row_index, self.drop_box_text, self.rid, self.name, "监测中")
            else:
                self.success.emit(self.row_index, self.drop_box_text, self.rid, self.name, "录制中")
        except Exception as e:
            self.error.emit(str(e))

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

        return error
