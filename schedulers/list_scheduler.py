from PyQt5.QtWidgets import QMessageBox

class ListScheduler(object):
    def __init__(self):
        self.base_dir = None
        self.total = 0
        self.thread_list = []
        self.item_terminate_flag = {}
        self.window = None
        self.terminate = False  # 用户是否点击了停止

    def start(self, base_dir, window, fn_update_status):
        self.window = window
        self.terminate = False
        self.base_dir = base_dir

        # 1 获取表格中的所有数据，每一行创建一个线程去执行监控
        for row_index in range(window.table_widget.rowCount()):
            platform = window.table_widget.item(row_index, 0).text()
            room_id = window.table_widget.item(row_index, 1).text()
            live_status = window.table_widget.item(row_index, 3).text()
            item_terminate_flag = False
            self.item_terminate_flag[row_index] = item_terminate_flag

            # 只有是自动录制的时候，才能创建线程
            if live_status == "已停止":
                continue
            print(platform, room_id, live_status, self.item_terminate_flag[row_index])
            print(room_id, self.terminate)
            try:
                if platform == '哔哩哔哩':
                    # 2 每个线程 录制状态实时的显示在表格中  会用到房间号和平台
                    from utils.monitor_bilibili_threads import MonitorInfoThread
                    # from test_project.monitor_bilibili_threads_copy import MonitorInfoThread
                    t = MonitorInfoThread(list_scheduler=self, row_index=row_index, rid=room_id, platform=platform,
                                          live_status=live_status)
                    t.live_status.connect(fn_update_status)
                    t.start()
                    print("直播间号{}已加入线程".format(room_id))
                if platform == '斗鱼直播':
                    # 2 每个线程 录制状态实时的显示在表格中  会用到房间号和平台
                    from utils.monitor_douyu_threads import MonitorInfoThread
                    t = MonitorInfoThread(list_scheduler=self, row_index=row_index, rid=room_id, platform=platform,
                                          live_status=live_status)
                    t.live_status.connect(fn_update_status)
                    t.start()

                self.thread_list.append(t)
                self.total += 1
            except:
                import cgitb
                cgitb.enable(format='text')
                QMessageBox.warning(window, '错误', f'房间号：{self.rid}的直播状态获取未成功')
        print(self.thread_list)

    def start_item_thread(self, row_index, fn_update_status):
        platform = self.window.table_widget.item(row_index, 0).text()
        room_id = self.window.table_widget.item(row_index, 1).text()
        live_status = self.window.table_widget.item(row_index, 3).text()
        self.item_terminate_flag[row_index] = False

        print(platform, room_id, live_status)

        if platform == '哔哩哔哩':
            # 2 每个线程 录制状态实时的显示在表格中  会用到房间号和平台
            # from utils.monitor_bilibili_threads import MonitorInfoThread
            # # from test_project.monitor_bilibili_threads_copy import MonitorInfoThread
            # t = MonitorInfoThread(list_scheduler=self, row_index=row_index, rid=room_id, platform=platform,
            #                       live_status=live_status)
            # t.live_status.connect(fn_update_status)
            # t.start()
            from utils.monitor_bilibili_threads import MonitorInfoThread
            # from test_project.monitor_bilibili_threads_copy import MonitorInfoThread
            t = MonitorInfoThread(list_scheduler=self, row_index=row_index, rid=room_id, platform=platform,
                                  live_status=live_status)
            t.live_status.connect(fn_update_status)
            t.start()
            print("直播间号{}已加入线程".format(room_id))
        if platform == '斗鱼直播':
            # 2 每个线程 录制状态实时的显示在表格中  会用到房间号和平台
            from utils.monitor_douyu_threads import MonitorInfoThread
            t = MonitorInfoThread(list_scheduler=self, row_index=row_index, rid=room_id, platform=platform,
                                  live_status=live_status)
            t.live_status.connect(fn_update_status)
            t.start()

        self.thread_list.append(t)
        self.total += 1

    def stop_item_thread(self, row_index):
        print("正在停止第{}行的监测".format(row_index+1))
        self.item_terminate_flag[row_index] = True

    def destroy_thread(self, thread):
        self.thread_list.remove(thread)

    def stop(self):
        self.terminate = True
        # 创建线程， 去监测 thread_list 中的数量 + 实时更新的窗体的label中
        # self.window.update_status_message("xxx")
        from utils.stop_threads import StopThread
        self.t = StopThread(self.total, self, self.window)
        self.t.update_signal.connect(self.window.update_status_message)
        self.t.start()

# 单例模式
LISTSCHEDULER = ListScheduler()