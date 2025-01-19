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
        # self.success.emit("123")
        # self.progress_signal.emit(20)
        video_url = self.item_video_info['video_url']
        title = self.item_video_info['video_title']
        title = re.sub('\W+', '',title).replace("_", '')
        print(45)
        print(self.item_video_info)
        print(video_url)
        print(title)
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

    def merge_data(self, video_name, temp_path, path):
        video_path = os.path.join(temp_path, video_name + '.mp4')
        audio_path = os.path.join(temp_path, video_name + '.mp3')
        random_int = random.randint(1, 100000)
        save_path = os.path.join(path, video_name + str(random_int) + '.mp4')
        # print('视频合成开始：', video_name)
        ffmpeg_path = os.path.join(self.basedir, "ffmpeg.exe")
        # video_name = video_name.replace(' ','')
        command = f"{ffmpeg_path} -i {video_path} -i {audio_path} -c:v copy -c:a aac -strict experimental -y {save_path}"
        # command = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac -strict experimental {save_path}"
        # command = f'ffmpeg -i F:\\myProject\\get_live\\_normal_videos\\{video_name}.mp4 -i F:\\myProject\\get_live\\_normal_videos\\{video_name}.mp3 -acodec copy -vcodec copy F:\\myProject\\get_live\\_normal_videos\\{video_name}-{random_int}.mp4'
        print(command)
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
        # 1
        # while process.poll() is None:
        #     if self.download_flag:
        #         line = process.stdout.readline()
        #         print(line)
        #         duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
        #         if duration_res is not None:
        #             duration = duration_res.groupdict()['duration']
        #             duration = re.sub(r',', '', duration)
        #             print(duration, self.get_seconds(duration))
        #
        #         result = re.search(r'\stime=(?P<time>\S+)', line)
        #         if result is not None:
        #             elapsed_time = result.groupdict()['time']
        #             # 此处可能会出现进度超过100%，未对数值进行纠正
        #             progress = (self.get_seconds(elapsed_time) / self.get_seconds(duration)) * 100
        #             progress = round(progress, 1)
        #             if progress < 100:
        #                 self.progress_signal.emit(progress)
        #             else:
        #                 self.progress_signal.emit(100)
        #                 self.play_button.setIcon(self.finish_icon)
        #                 self.play_button.setText("完成")
        #                 self.play_button.setEnabled(False)
        #     else:
        #         process.communicate(b' ')  # send space to pause/resume the process

        # 2
        # while process.poll() is None:
        #     if self.download_flag:
        #         line = process.stdout.readline()
        #         print(line)
        #         duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
        #         if duration_res is not None:
        #             duration = duration_res.groupdict()['duration']
        #             duration = re.sub(r',', '', duration)
        #             print(duration, self.get_seconds(duration))
        #
        #         result = re.search(r'\stime=(?P<time>\S+)', line)
        #         if result is not None:
        #             elapsed_time = result.groupdict()['time']
        #             # 此处可能会出现进度超过100%，未对数值进行纠正
        #             progress = (self.get_seconds(elapsed_time) / self.get_seconds(duration)) * 100
        #             progress = round(progress, 1)
        #             if progress < 100:
        #                 self.progress_signal.emit(progress)
        #             else:
        #                 self.progress_signal.emit(100)
        #                 self.play_button.setIcon(self.finish_icon)
        #                 self.play_button.setText("完成")
        #                 self.play_button.setEnabled(False)
        #     else:
        #         process.terminate()

        # 3
        # while self.download_flag:
        #     process.poll()
        #     if process.returncode is not None:
        #         break
        #     line = process.stdout.readline()
        #     print(line)
        #     duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
        #     if duration_res is not None:
        #         duration = duration_res.groupdict()['duration']
        #         duration = re.sub(r',', '', duration)
        #         print(duration, self.get_seconds(duration))
        #
        #     result = re.search(r'\stime=(?P<time>\S+)', line)
        #     if result is not None:
        #         elapsed_time = result.groupdict()['time']
        #         # 此处可能会出现进度超过100%，未对数值进行纠正
        #         progress = (self.get_seconds(elapsed_time) / self.get_seconds(duration)) * 100
        #         progress = round(progress, 1)
        #         if progress < 100:
        #             self.progress_signal.emit(progress)
        #         else:
        #             self.progress_signal.emit(100)
        #             self.play_button.setIcon(self.finish_icon)
        #             self.play_button.setText("完成")
        #             self.play_button.setEnabled(False)
        # process.terminate()

        # 4
        while process.poll() is None:
            if not self.download_flag:
                try:
                    print(180, self.current_value)
                    process.stdin.write('q')
                    process.communicate()
                    os.remove(save_path)
                    self.current_value = math.ceil(progress)
                    self.progress_pause.emit(True)
                    self.tip_signal.emit('')
                    print(185, self.current_value)
                    sql = "UPDATE download_video_list SET finish_flag = ? WHERE bvid = ?"
                    values = (self.current_value, self.item_video_info['bvid'])
                    lock.acquire()
                    cursor.execute(sql, values)
                    conn.commit()
                except:
                    conn.rollback()
                    QMessageBox.warning(self, "错误", f"'{self.item_video_info['video_title']}的下载进度保存未成功'")
                finally:
                    lock.release()
                break
            else:
                time.sleep(0.1)
                line = process.stdout.readline()
                print(line)
                duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
                if duration_res is not None:
                    duration = duration_res.groupdict()['duration']
                    duration = re.sub(r',', '', duration)
                    print(duration, self.get_seconds(duration))

                result = re.search(r'\stime=(?P<time>\S+)', line)
                bitrate_res = re.search('\sbitrate=\s*(?P<bitrate>\S+)', line)
                if result is not None and bitrate_res is not None:
                    elapsed_time = result.groupdict()['time']
                    bitrate = bitrate_res.groupdict()['bitrate']
                    print(bitrate)
                    # 此处可能会出现进度超过100%，未对数值进行纠正
                    progress = (self.get_seconds(elapsed_time) / self.get_seconds(duration)) * 100
                    progress = round(progress, 1)
                    self.set_current_value(math.ceil(progress))
                    if progress >= self.current_value:
                        if progress <= 99:
                            self.progress_signal.emit(progress)
                            self.tip_signal.emit(bitrate)
                        else:
                            try:
                                sql = "UPDATE download_video_list SET finish_flag = ? WHERE bvid = ?"
                                values = (100, self.item_video_info['bvid'])
                                lock.acquire()
                                cursor.execute(sql, values)
                                conn.commit()
                                self.progress_signal.emit(100)
                                self.tip_signal.emit('')
                                self.progress_finish_update.emit(self.item_video_info)
                                self.play_button.setIcon(self.finish_icon)
                                self.play_button.setText("完成")
                                self.progress_pause.emit(True)
                                self.play_button.setEnabled(False)
                            except:
                                conn.rollback()
                                QMessageBox.warning(self, "错误", f"'{self.item_video_info['video_title']}的下载进度保存未成功'")
                            lock.release()
                    else:
                        self.tip_signal.emit("0.0kbits/s")
        # 5
        # while process.poll() is None:
        #     line = process.stdout.readline()
        #     print(line)
        #     duration_res = re.search(r'\sDuration: (?P<duration>\S+)', line)
        #     if duration_res is not None:
        #         duration = duration_res.groupdict()['duration']
        #         duration = re.sub(r',', '', duration)
        #         print(duration, self.get_seconds(duration))
        #
        #     result = re.search(r'\stime=(?P<time>\S+)', line)
        #     if result is not None:
        #         elapsed_time = result.groupdict()['time']
        #         # 此处可能会出现进度超过100%，未对数值进行纠正
        #         progress = (self.get_seconds(elapsed_time) / self.get_seconds(duration)) * 100
        #         progress = round(progress, 1)
        #         if progress < 100:
        #             self.progress_signal.emit(progress)
        #         else:
        #             self.progress_signal.emit(100)
        #             self.play_button.setIcon(self.finish_icon)
        #             self.play_button.setText("完成")
        #             self.play_button.setEnabled(False)
        #     while not self.download_flag:
        #         self.sleep(1)
        #         print(process.stdout.readline())
        #         if self.download_flag:
        #             print(230)
        #             break

    def remove_data(self, video_name, path, save_path):
        video_path = os.path.join(path, video_name + '.mp4')
        audio_path = os.path.join(path, video_name + '.mp3')
        os.remove(video_path)
        os.remove(audio_path)
        print("视频、音频已删除", video_name)
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
        # 403 状态码 没有权限
        # 增加一个防盗链，防盗链的作用：告诉服务器我们发送请求的url地址是从哪里跳转来的
        # pprint(json_data)
        # 数据解析 json数据取值， 键值对取值
        audio_url = json_data['data']['dash']['audio'][0]['baseUrl']
        video_url = json_data['data']['dash']['video'][0]['baseUrl']
        video_info = [audio_url, video_url]
        return video_info, author_name

    def get_response(self, html_url):
        headers = {
            'referer': 'https://www.bilibili.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        }
        time.sleep(random.randint(0, 2))
        response = requests.get(url=html_url, headers=headers, timeout=10)
        return response
