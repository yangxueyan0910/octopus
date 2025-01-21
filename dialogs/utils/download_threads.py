import json
import math
import os
import random
import re
import time

import requests
import subprocess
import threading

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox

# 连接数据库
import connect
from asset import resources

cursor, conn, lock = connect.connect()

class DownloadInfoThread(QThread):
    # 信号，触发信号，通知用户
    success = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    tip_signal = pyqtSignal(str)
    progress_finish = pyqtSignal(bool)
    progress_finish_update = pyqtSignal(object)
    progress_pause = pyqtSignal(bool)
    # save_path_signal = pyqtSignal(str)

    def __init__(self, basedir, item_video_info, play_button, row_index, progress_bar, tip_item, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.basedir = basedir
        self.item_video_info = item_video_info
        self.play_button = play_button
        self.row_index = row_index
        self.progress_bar = progress_bar
        self.tip_item = tip_item
        self.download_flag = False
        self.finish_icon = QIcon(':/finish.ico')
        self.is_season_display = None
        self.current_value = 0
        self.current_value_lock = threading.Lock()

    def set_current_value(self, value):
        with self.current_value_lock:
            self.current_value = value

    def get_current_value(self):
        with self.current_value_lock:
            return self.current_value

    def run(self):
        try:
            video_url = self.item_video_info['video_url']
            title = self.item_video_info['video_title']
            title = re.sub('\W+', '',title).replace("_", '')
            print(self.item_video_info)
            self.tip_signal.emit("正在获取数据源")
            time.sleep(0.5)
            video_info, author_name = self.get_video_info(html_url=video_url)
            # 音频的二进制数据
            audio_content = self.get_response(video_info[0]).content
            # 视频的二进制数据
            video_content = self.get_response(video_info[1]).content
            save_folder = os.path.join(self.basedir, "_normal_videos", author_name)
            save_temp_folder = os.path.join(self.basedir, "_normal_videos", "temp_videos", author_name)

            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            if not os.path.exists(save_temp_folder):
                os.makedirs(save_temp_folder)

            with open(os.path.join(save_temp_folder, title + '.mp3'), mode='wb') as f:
                f.write(audio_content)
                self.success.emit(f"{title}.mp3 已开始下载...")
            with open(os.path.join(save_temp_folder, title + '.mp4'), mode='wb') as f:
                f.write(video_content)
                self.success.emit(f"{title}.mp4 已开始下载...")
            print("mp3、mp4视频内容保存完成")
            self.progress_bar.setRange(0, 100)
            # 将视频和音频整合
            self.merge_data(video_name=title, temp_path=save_temp_folder, path=save_folder)
            # self.remove_data(video_name=title, path=save_folder)
            if self.download_flag:
                # 删除整合前的视频和音频
                self.remove_data(video_name=title, path=save_temp_folder, save_path=save_folder)
                from pathlib import Path
                parent_directory = Path(save_temp_folder).parent
                import shutil
                try:
                    shutil.rmtree(parent_directory)
                    print(f"Folder '{parent_directory}' deleted successfully.")
                except OSError as e:
                    print(f"Error: {parent_directory} - {e}")
            self.progress_finish_update.emit(self.item_video_info)
        finally:
            if self.download_flag: #仅在正常完成时发送信号
                self.progress_finish.emit(True) #新增完成信号
    def merge_data(self, video_name, temp_path, path):
        video_path = os.path.join(temp_path, video_name + '.mp4')
        audio_path = os.path.join(temp_path, video_name + '.mp3')
        random_int = random.randint(1, 100000)
        save_path = os.path.join(path, video_name + str(random_int) + '.mp4')
        # print('视频合成开始：', video_name)
        ffmpeg_path = os.path.join(self.basedir, "ffmpeg.exe")
        # video_name = video_name.replace(' ','')
        command = f"{ffmpeg_path} -i {video_path} -i {audio_path} -c:v copy -c:a aac -strict experimental -y {save_path}"
        print(command)
        # command = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac -strict experimental {save_path}"
        # command = f'ffmpeg -i F:\\myProject\\get_live\\_normal_videos\\{video_name}.mp4 -i F:\\myProject\\get_live\\_normal_videos\\{video_name}.mp3 -acodec copy -vcodec copy F:\\myProject\\get_live\\_normal_videos\\{video_name}-{random_int}.mp4'
        # subprocess.call(command, shell=True)
        # process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, text=True, shell=True, encoding="utf-8", errors='ignore')
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, bufsize=0, text=True, encoding="utf-8", errors='ignore')
        # process = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, text=True, shell=True, encoding="utf-8", errors='ignore')
        self.compute_progress_and_send_progress(process, save_path)
        # print(process.communicate()[0])
        # print('视频合成完成', video_name)
        self.success.emit(f"{video_name}{str(random_int)}.mp4 开始下载...")

    def get_seconds(self, time):
        h = int(time[0:2])
        m = int(time[3:5])
        s = int(time[6:8])
        ms = int(time[9:11])
        ts = (h * 60 * 60) + (m * 60) + s + (ms / 1000)
        return ts


    def compute_progress_and_send_progress(self, process, save_path):
        duration = None
        while process.poll() is None: #轮询进程状态
            if not self.download_flag:
                # 处理暂停逻辑
                try:
                    process.stdin.write('q')
                    process.communicate()
                    os.remove(save_path)
                    self.progress_pause.emit(True)
                    self.tip_signal.emit('')
                    # 保存当前进度值到数据库
                    current_value = self.get_current_value()
                    sql = "UPDATE download_video_list SET finish_flag = ? WHERE bvid = ?"
                    values = (current_value, self.item_video_info['bvid'])
                    lock.acquire()
                    cursor.execute(sql, values)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    QMessageBox.warning(self, "错误", f"'{self.item_video_info['video_title']}的下载进度保存未成功'")
                finally:
                    lock.release()
                break
            else:
                line = process.stdout.readline() #得到日志信息
                #print(line)
                # 提取视频总时长
                if not duration:
                    duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
                    if duration_res:
                        duration = duration_res.groupdict()['duration'].replace(',', '')
                        duration_seconds = self.get_seconds(duration)
                # 提取当前时间并计算进度
                time_res = re.search(r'\stime=(?P<time>\S+)', line)
                if time_res and duration:
                    elapsed_time = time_res.groupdict()['time']
                    elapsed_seconds = self.get_seconds(elapsed_time)
                    progress = (elapsed_seconds / duration_seconds) * 100
                    progress = min(round(progress, 1), 100)  # 确保不超过100%
                    self.set_current_value(math.ceil(progress))
                    self.progress_signal.emit(progress)
                    # 更新实时速度
                    bitrate_res = re.search(r'\sbitrate=\s*(?P<bitrate>\S+)', line)
                    if bitrate_res:
                        self.tip_signal.emit(bitrate_res.group('bitrate'))

        # 进程结束后强制设置进度为100%
        if self.download_flag:  # 仅在正常完成时更新
            self.progress_signal.emit(100)
            self.tip_signal.emit('')
            self.play_button.setIcon(self.finish_icon)
            self.play_button.setText("完成")
            self.play_button.setEnabled(False)
            # 更新数据库
            try:
                sql = "UPDATE download_video_list SET finish_flag = ? WHERE bvid = ?"
                values = (100, self.item_video_info['bvid'])
                lock.acquire()
                cursor.execute(sql, values)
                conn.commit()
                self.progress_finish_update.emit(self.item_video_info)
            except Exception as e:
                conn.rollback()
                QMessageBox.warning(self, "错误", f"进度保存失败: {str(e)}")
            finally:
                lock.release()

    def remove_data(self, video_name, path, save_path):
        video_path = os.path.join(path, video_name + '.mp4')
        audio_path = os.path.join(path, video_name + '.mp3')
        os.remove(video_path)
        os.remove(audio_path)
        self.success.emit(f"{video_name}.mp4 下载已完成")
        save_path = re.sub(r'(:)', r'\1\\', save_path)
        save_path = re.sub(r'(octopus)', r'\1\\', save_path)
        save_path = re.sub(r"(videos)", r"\1\\", save_path)
        try:
            sql = "UPDATE download_video_list SET save_path = ? WHERE video_url = ?"
            values = (save_path, self.item_video_info['bvid'])
            lock.acquire()
            cursor.execute(sql, values)
            conn.commit()
        except:
            conn.rollback()
            QMessageBox.warning(self, "错误", f"'{self.item_video_info['video_title']}的视频路径保存未成功'")
        lock.release()

    def get_video_info(self, html_url):
        response = self.get_response(html_url)
        # 获取作者的名字
        json_data_1 = json.loads(
            re.findall('<script>window.__INITIAL_STATE__=(.*?);\(function\(\){var s;', response.text)[0])
        author_name = json_data_1['videoData']['owner']['name']
        print("author: ", author_name)
        # self.success.emit("正在获取数据源...")
        # 正则匹配出来的数据是列表
        #print(response.text)
        html_data = re.findall('<script>window.__playinfo__=(.*?)</script>', response.text)[0]
        json_data = json.loads(html_data)
        # 数据解析 json数据取值， 键值对取值
        audio_url = json_data['data']['dash']['audio'][0]['baseUrl']
        video_url = json_data['data']['dash']['video'][0]['baseUrl']
        video_info = [audio_url, video_url]
        return video_info, author_name

    def get_response(self, html_url):
        headers = {
            'referer': 'https://www.bilibili.com/',
            'cookie': "buvid3=CD5F63EB-4942-00B5-09B3-B3A8367AF6EA40758infoc; b_nut=1730386940; _uuid=7148F10D10-128B-2FA1-3F5B-714A78B6F6A953155infoc; rpdid=|()k~m|RJ)Y0J'u~J|J)~JlR; buvid4=C97989C2-D5F5-E07A-BFCC-ED0898C377DD40758-024103115-uG3KEHERXsjv%2B7SHY9SX5g%3D%3D; header_theme_version=CLOSE; iflogin_when_web_push=1; enable_web_push=DISABLE; buvid_fp=f442b4341c4d6bfa57c13c877418398c; CURRENT_QUALITY=80; bp_t_offset_40648342=1016659883275059200; home_feed_column=4; DedeUserID=693862727; DedeUserID__ckMd5=97bc1d93000f822e; LIVE_BUVID=AUTO8617367642142762; PVID=16; bsource=search_bing; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Mzc0NDY3MDAsImlhdCI6MTczNzE4NzQ0MCwicGx0IjotMX0.gsHh1YJLXzFtwqwbj95mAC0STfNawlaVvgOVjeyr2rY; bili_ticket_expires=1737446640; SESSDATA=dc4b0060%2C1752739501%2C06e4f%2A11CjCDcPOkh-Gv4O7cP1dWxqzc393OF8CTW2FpuViB7na7vMk6BenQdWpHNgwyPYUkCOkSVnZCQ21jUFRRMlVxcTRvNGtyU2hWb2Y4bnZWZjVqaWNwZ1luemdBYXcxd1NBSGpSbW80SUFYWXo0MUh4cGtRN0haV1N1RDk0STBkajVJQmNDWG9qLUJnIIEC; bili_jct=d084778ee7db30b9e946629a5b73216c; sid=77s4rpf9; bp_t_offset_693862727=1024773308425437184; b_lsid=1013A9D1C_1948762E0AF; browser_resolution=1017-671; CURRENT_FNVAL=2000",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': '*/*',
        }
        time.sleep(random.randint(0, 1))
        response = requests.get(url=html_url, headers=headers, timeout=10)
        return response
