import base64
import hashlib
import html
import json
import re
import time
import urllib

import requests
from PyQt5.QtCore import QThread, pyqtSignal


class GetInfoThread(QThread):
    # 信号，触发信号，更新窗体中的数据
    success = pyqtSignal(int, str, str, str, str)
    error = pyqtSignal(str)

    def __init__(self, row_index, rid, drop_box_text, *args, **kwargs):
        super(GetInfoThread, self).__init__(*args, **kwargs)
        self.room_id = rid
        self.user_id = 1463993859134
        self.live_url_infos = {}
        self.name = None

    def run(self):
        try:
            room_url = 'https://www.huya.com/' + str(self.room_id)
            header = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
            }
            response = requests.get(url=room_url, headers=header, timeout=30)
            if response.status_code == 200:
                self.clear_live_url_infos()
                liveData = None
                streamInfo = re.findall(r'stream: ([\s\S]*?)\n', response.text)
                if (len(streamInfo) > 0):
                    liveData = json.loads(streamInfo[0])
                else:
                    streamInfo = re.findall(r'"stream": "([\s\S]*?)"', response.text)
                    if (len(streamInfo) > 0):
                        liveDataBase64 = streamInfo[0]
                        liveData = json.loads(str(base64.b64decode(liveDataBase64), 'utf-8'))
                if liveData is not None:
                    streamInfoList = liveData['data'][0]['gameStreamInfoList']
                    self.name = liveData['data'][0]['gameLiveInfo']['nick']
                    for streamInfo in streamInfoList:
                        live_url_info = {}
                        sCdnType = streamInfo['sCdnType']
                        live_url_info['stream_name'] = streamInfo['sStreamName']
                        live_url_info['base_url'] = streamInfo['sHlsUrl']
                        live_url_info['hls_url'] = streamInfo['sHlsUrl'] + '/' + streamInfo['sStreamName'] + '.' + \
                                                   streamInfo['sHlsUrlSuffix']
                        sHlsAntiCode = streamInfo['sHlsAntiCode']
                        live_url_info.update(self.decode_live_url_info(sHlsAntiCode))
                        self.live_url_infos[sCdnType] = live_url_info
            else:
                raise Exception("直播间不存在")
        except Exception as e:
            self.error.emit(str(e))

    def decode_live_url_info(self, srcAntiCode):
        srcAntiCode = html.unescape(srcAntiCode)
        c = srcAntiCode.split('&')
        c = [i for i in c if i != '']
        n = {i.split('=')[0]: i.split('=')[1] for i in c}
        fm = urllib.parse.unquote(n['fm'])
        u = base64.b64decode(fm).decode('utf-8')
        live_url_info = {}
        live_url_info['hash_prefix'] = u.split('_')[0]
        live_url_info['uuid'] = n.get('uuid', '')
        live_url_info['ctype'] = n.get('ctype', '')
        live_url_info['txyp'] = n.get('txyp', '')
        live_url_info['fs'] = n.get('fs', '')
        live_url_info['t'] = n.get('t', '')
        return live_url_info

    def clear_live_url_infos(self):
        self.live_url_infos = {}

    def get_real_url(self, ratio = None):
        urls = []
        seqid = str(int(time.time() * 1e3 + self.user_id))
        wsTime = hex(int(time.time()) + 3600).replace('0x', '')
        for live_url_info in self.live_url_infos.values():
            hash0 = hashlib.md5((seqid + '|' + live_url_info['ctype'] + '|' + live_url_info['t']).encode('utf-8')).hexdigest()
            hash1 = hashlib.md5('_'.join([live_url_info['hash_prefix'], str(self.user_id), live_url_info['stream_name'], hash0, wsTime]).encode('utf-8')).hexdigest()
            if ratio is None:
                ratio = ''
            if 'mobile' in live_url_info['ctype']:
                url = "{}?wsSecret={}&wsTime={}&uuid={}&uid={}&seqid={}&ratio={}&txyp={}&fs={}&ctype={}&ver=1&t={}".format(
                    live_url_info['hls_url'], hash1, wsTime, live_url_info['uuid'], self.user_id, seqid, ratio, live_url_info['txyp'],
                    live_url_info['fs'], live_url_info['ctype'], live_url_info['t'])
            else:
                url = "{}?wsSecret={}&wsTime={}&seqid={}&ctype={}&ver=1&txyp={}&fs={}&ratio={}&u={}&t={}&sv=2107230339".format(
                    live_url_info['hls_url'], hash1, wsTime, seqid, live_url_info['ctype'], live_url_info['txyp'], live_url_info['fs'], ratio, self.user_id, live_url_info['t'])
            urls.append(url)
        return urls