import json
import re
import time
import random
import urllib.parse
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox


class AnalysisUrlThread(QThread):
    # 信号，触发信号，通知用户
    success = pyqtSignal(str, str, str)
    process = pyqtSignal(str)

    def __init__(self, url, *args, **kwargs):
        super(AnalysisUrlThread, self).__init__(*args, **kwargs)
        self.url = url
        self.is_season_display = None
        self.stop = False

    def run(self):
        video_info_list, is_season_display, author_name, counter = self.get_video_info(html_url=self.url)
        if is_season_display:
            # 有合集
            for i, item in enumerate(video_info_list):
                if self.stop:
                    break
                # item_video_info = [item_title, item_audio_url, item_video_url]
                item_title = item[0]
                item_url = item[1]
                item_bvid = item[2]
                time.sleep(0.5)
                self.success.emit(item_title, item_url, item_bvid)
                self.process.emit("正在获取({}/{})".format(i+1, counter))
                if i == counter-1:
                    time.sleep(1)
                    self.process.emit("解析完成")

        else:
            # 没有合集
            if self.stop:
                pass
            else:
                print(video_info_list)
                if(len(video_info_list)==1):
                    title = video_info_list[0][0]
                    url = video_info_list[0][1]
                    bvid = video_info_list[0][2]
                else:
                    title = video_info_list[0]
                    url = video_info_list[1]
                    bvid = video_info_list[2]
                self.success.emit(title, url, bvid)
                time.sleep(1)
                self.process.emit("解析完成")

    def get_video_info(self, html_url):
        video_url_pattern1 = r'https://www\.bilibili\.com/video/[\w/]+'
        pattern2 = r"https://search\.bilibili\.com/all\?keyword=.*"
        pattern3 = r'https://search\.bilibili\.com/all\?.*?keyword=([^&]+)'
        pattern4 = r'https://search\.bilibili\.com/video\?keyword=([^&]+)'
        if re.match(video_url_pattern1, html_url):
            response = self.get_response(html_url)
            '''print(response.text)'''
            # 获取是否有合集的信号
            json_data_1 = json.loads(
                re.findall('<script>window.__INITIAL_STATE__=(.*?);\(function\(\){var s;', response.text)[0])
            print(56, json_data_1)

            is_season_display = json_data_1['videoData']['is_season_display']
            self.is_season_display = is_season_display
            print(is_season_display)
            # 获取作者的名字
            author_name = json_data_1['videoData']['owner']['name']
            print("author: ", author_name)
            self.process.emit("正在解析数据源...")
             #video_info列表
            video_info_list = []

            if is_season_display:
                print(json_data_1['videoData'])
                total = len(json_data_1['videoData']['ugc_season']['sections'][0]['episodes'])
                print(total)
                for i, item in enumerate(json_data_1['videoData']['ugc_season']['sections'][0]['episodes']):
                    if self.stop:
                        break
                    # bvid_list[i] = item['bvid']
                    print(item['bvid'])
                    bvid = item['bvid']
                    item_url = "https://www.bilibili.com/video/" + str(item['bvid'])
                    print(item_url)
                    item_res = self.get_response(item_url).text
                    # 每个视频的标题
                    item_title = re.findall('<h1 title="(.*?)" class="video-title tit">', item_res)[0]
                    print(79, item_title)
                    # item_title = re.sub(r'[^\u4e00-\u9fa5]+', '', item_title)  # 去除双引号
                    # item_title = re.sub(r'[\/:*?"<>|]', '', item_title)  # 去除双引号
                    re.sub(r'[\/:*?"<>|\s]', '', item_title)

                    item_video_info = [item_title, item_url, bvid]
                    video_info_list.append([])
                    video_info_list[i] = item_video_info
                    print(video_info_list[i])
                    self.process.emit("正在解析数据源... {}%".format(round((i + 1) / total, 2) * 100))
                    # 设置保存个数
                    # if i == 1:
                    #     return video_info_list, is_season_display, author_name, counter
                return video_info_list, is_season_display, author_name, total
            else:
                # 获取视频标题

                bvid1 = json_data_1['videoData']['bvid']
                total=len(json_data_1['videoData']['pages'])
                print(total)
                video_info_list=[]
                if total==1:
                    element = (json_data_1['videoData']['pages'][0]['part'])
                    re.sub(r'[\/:*?"<>|\s]', '', element)
                    html_url = ('https://www.bilibili.com/video/' + str(bvid1))
                    item_video_info=[element, html_url, bvid1]
                    video_info_list.append(item_video_info)
                    print(video_info_list[0])
                    time.sleep(0.2)
                else:
                    for i in range(0,total):
                      element=(json_data_1['videoData']['pages'][i]['part'])
                      re.sub(r'[\/:*?"<>|\s]', '', element)
                      html_url=('https://www.bilibili.com/video/'+str(bvid1)+'/?p='+str(i+1))
                      item_video_info=[element,html_url,bvid1]
                      video_info_list.append(item_video_info)
                      print(video_info_list[i])
                      time.sleep(0.2)
                      self.process.emit("正在解析数据源... {}%".format(round((i + 1) / total, 2) * 100))

                if total>1:
                  is_season_display= True
                return video_info_list, is_season_display, author_name, total
        elif re.match(pattern2, html_url)or re.match(pattern3, html_url) or re.match(pattern4,html_url):

            #keyword_match = re.search(r'keyword=([^&]+)', html_url)
            #keyword=keyword_match.group(1)
            page_match = re.search(r'page=(\d+)', html_url)
            if page_match:
                page = int(page_match.group(1))
            else:
                page = 1
            parsed_url = urllib.parse.urlparse(html_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'keyword' in query_params:
                # 解码关键词
                decoded_keyword = urllib.parse.unquote(query_params['keyword'][0])

            else:
                print("No 'keyword' parameter found in the URL.")
            print(decoded_keyword,page)
            info_url = "https://api.bilibili.com/x/web-interface/wbi/search/type?category_id=&search_type=video&ad_resource=5654&page={}&keyword={}".format(page,decoded_keyword)
            print(info_url)
            response = self.get_response1(info_url)
            json_data = json.loads(response.text)
            if 'code' in json_data:
                if json_data['code'] == -403:
                    self.process.emit("解析异常")
                    self.quit()
                    return
            print(119, json_data['code'])
            video_info_list = []
            total = len(json_data['data']['result'])
            author_name = json_data['data']['result'][0]['author']
            for i, item in enumerate(json_data['data']['result']):
                if self.stop:
                    break
                bvid = item['bvid']
                item_title1 = item['title']
                item_title1 = re.sub(r'[\/:*?"<>|\s]', '', item_title1)  # 去除双引号
                # item_title = re.sub(r'[^\u4e00-\u9fa5]+', '', item_title)  # 去除双引号
                item_title = re.sub(r'emclass=keyword.*?em', f'{decoded_keyword}', item_title1)
                item_url = "https://www.bilibili.com/video/" + str(bvid)
                item_video_info = [item_title, item_url, bvid]

                video_info_list.append([])
                video_info_list[i] = item_video_info
                print(video_info_list[i])
                time.sleep(0.2)
                self.process.emit("正在解析数据源... {}%".format(round((i + 1) / total, 2) * 100))
                # 设置保存个数
                # if i == 1:
                #     return video_info_list, is_season_display, author_name, counter
            return video_info_list, True, author_name, total

        else:
            flag1 = re.findall('com/(.*?)/', html_url)
            if flag1:
             flag = re.findall('com/(.*?)/', html_url)[0]
            else: flag = None
            if flag == None:
                mid = re.findall('bilibili\.com/(\d+)',html_url)[0]
                info_url = "https://api.bilibili.com/x/space/wbi/arc/search?mid={}".format(mid)
                print(info_url)
                response = self.get_response(info_url)
                json_data = json.loads(response.text)
                if 'code' in json_data:
                    if json_data['code'] == -403:
                        self.process.emit("解析异常")
                        self.quit()
                        return
                print(119, json_data['code'])

                # video_info列表
                video_info_list = []
                total = len(json_data['data']['list']['vlist'])
                author_name = json_data['data']['list']['vlist'][0]['author']

                for i, item in enumerate(json_data['data']['list']['vlist']):
                    if self.stop:
                        break
                    bvid = item['bvid']
                    item_title = item['title']
                    item_title = re.sub(r'[\/:*?"<>|\s]', '', item_title)  # 去除双引号
                    # item_title = re.sub(r'[^\u4e00-\u9fa5]+', '', item_title)  # 去除双引号
                    item_url = "https://www.bilibili.com/video/" + str(bvid)
                    item_video_info = [item_title, item_url, bvid]
                    video_info_list.append([])
                    video_info_list[i] = item_video_info
                    print(video_info_list[i])
                    time.sleep(0.2)
                    self.process.emit("正在解析数据源... {}%".format(round((i + 1) / total, 2) * 100))
                    # 设置保存个数
                    # if i == 1:
                    #     return video_info_list, is_season_display, author_name, counter
                return video_info_list, True, author_name, total

            else:
                # 获取到up主主页ID
                mid = flag
                print(104, mid)

                # 获取当前页面的页数
                if "page" in html_url:
                    pn = re.findall('page=(.*?)&', html_url)[0]
                    info_url = "https://api.bilibili.com/x/space/wbi/arc/search?mid={}&pn={}".format(mid, pn)
                    print(info_url)
                elif "pn" in html_url:
                    pn = re.findall('pn=(.*?)&', html_url)[0]
                    info_url = "https://api.bilibili.com/x/space/wbi/arc/search?mid={}&pn={}".format(mid, pn)
                    print(info_url)
                else:
                    info_url = "https://api.bilibili.com/x/space/wbi/arc/search?mid={}".format(mid)
                    print(info_url)

                response = self.get_response(info_url)
                json_data = json.loads(response.text)
                print(json_data)
                if 'code' in json_data:
                    if json_data['code'] == -403:
                        self.process.emit("解析异常")
                        self.quit()
                        return
                print(119, json_data['code'])

                # video_info列表
                video_info_list = []
                print(json_data['data'])
                total = len(json_data['data']['list']['vlist'])
                author_name = json_data['data']['list']['vlist'][0]['author']

                for i, item in enumerate(json_data['data']['list']['vlist']):
                    if self.stop:
                        break
                    bvid = item['bvid']
                    item_title = item['title']
                    item_title = re.sub(r'[\/:*?"<>|\s]', '', item_title)  # 去除双引号
                    # item_title = re.sub(r'[^\u4e00-\u9fa5]+', '', item_title)  # 去除双引号
                    item_url = "https://www.bilibili.com/video/" + str(bvid)
                    item_video_info = [item_title, item_url, bvid]

                    video_info_list.append([])
                    video_info_list[i] = item_video_info
                    print(video_info_list[i])
                    time.sleep(0.2)
                    self.process.emit("正在解析数据源... {}%".format(round((i + 1) / total, 2) * 100))
                    # 设置保存个数
                    # if i == 1:
                    #     return video_info_list, is_season_display, author_name, counter
                return video_info_list, True, author_name, total


    def get_response(self, html_url):
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 SLBrowser/9.0.0.10191 SLBChan/105",

            # Referer: 防盗链。用于告诉服务器我是从哪个链接跳转来的。
            'Referer': 'https://www.bilibili.com/',

        }
        # time.sleep(random.randint(1, 5))
        with requests.Session() as s:
            response = s.get(url=html_url, headers=headers, timeout=5)
        return response
    def get_response1(self,html_url):
        headers = {
            'accept': 'application/json,text/plain,*/*',
            'accept-encoding': 'gzip,deflate,br',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'cookie': "buvid4=9049BB59-1F85-A9BD-0DA2-9192AE167A5D36258-022072714-FtODpuifXpkq25XCF6uzpg%3D%3D; CURRENT_FNVAL=4048; CURRENT_QUALITY=16; rpdid=|(J~lkkYRuR~0J'uY~~|~uulk; _uuid=A751C7A5-9E1B-E9D10-EEDB-C969EE9FD35D32373infoc; b_nut=1694182632; buvid3=FBA1AF8F-4C58-6B14-167E-93872E3E9B3E33168infoc; header_theme_version=CLOSE; home_feed_column=4; browser_resolution=1280-647; DedeUserID=503413226; DedeUserID__ckMd5=35968ed52e86c9f4; LIVE_BUVID=AUTO1016952932183001; buvid_fp_plain=undefined; buvid_fp=590f6a10b94100f60ad0045a787f6933; enable_web_push=DISABLE; fingerprint=6cde34c5e5743a15dd719569af6fd0d3; PVID=3; bp_video_offset_503413226=859170776947884037; innersign=0; b_lsid=54F76EC6_18B93D20FF9; bsource=search_baidu; SESSDATA=13bde86e%2C1714544102%2C51c98%2Ab1CjAgTGB454yNo_tM7gcjVZJRkvBMCye2zKdSDkh6jTVvZ6UpDQve5sNsv2KMqs3qyIASVjh4Si1jc2ZJQV9EX2pHZGpQTFExb2ptclgya3AxZHY2UGdtWm8zNzhNWENMeEh4ZEZxWDBWZVpXQkVfZHBNb2pWaVEtb2M5MFVLZVdOendoaXJCMGVRIIEC; bili_jct=e02876481ffa068b23e02a1d5e0e5011; sid=5rpazcm3",
            'referer': 'https://www.bilibili.com/',
            'origin': 'https://search.bilibili.com',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="8"',
            # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 SLBrowser/8.0.1.4031 SLBChan/105'
        }
        params = {
            'search_type': 'video',
            '__refresh__': 'true',
            'ad_resource': '5654',
            '_extra': '',
            'context': '',
            'page_size': '42',
            'from_source': '',
            'from_spmid': '333.337',
            'platform': 'pc',
            'highlight': '1',
            'single_column': '0',
            'qv_id': 'Yx1wQ928UHWUTbvfP7E13tvczsX3ce80',
            'category_id': '',
            'preload': 'true',
            'com2co': 'true',
        }
        with requests.Session() as s:
            response = s.get(url=html_url, headers=headers,params=params, timeout=5)
        return response
