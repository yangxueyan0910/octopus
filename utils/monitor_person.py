import shutil
import subprocess
import time
import sys
import os

import threading
import os
from pathlib import Path
import torch
import torch.backends.cudnn as cudnn
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from yolo.models.common import DetectMultiBackend
from yolo.utils.datasets import LoadImages, LoadStreams
from yolo.utils.general import (LOGGER, check_img_size, check_imshow, non_max_suppression,  scale_coords)
from yolo.utils.plots import Annotator
from yolo.utils.torch_utils import select_device, time_sync

class MonitorPersonThread(QThread):

    person_status = pyqtSignal(str)

    def __init__(self, base_dir, rtmp_url, name, rid):
        # 初始化界面
        super().__init__()
        self.base_dir = base_dir
        self.rtmp_url = rtmp_url
        self.name = name
        # 图片读取进程
        self.output_size = 480
        self.img2predict = ""
        self.device = 'cpu'
        # # 初始化视频读取线程
        self.vid_source = '0'  # 初始设置为摄像头
        self.stopEvent = threading.Event()
        self.webcam = True
        self.stopEvent.clear()
        model_path = os.path.join(base_dir, "yolo", "runs", "train", "exp_yolov5s", "weights", "yolov5m.pt")
        self.model = self.model_load(weights=model_path,
                                     device=self.device)  # todo 指明模型加载的位置的设备
        self.reset_vid()
        self.record_thread = None
        self.terminate_flag = False
        self.p = None
        self.record_flag = False
        self.rid = rid
        self.previous_status = ""

    '''
    ***模型初始化***
    '''
    @torch.no_grad()
    def model_load(self, weights="",  # model.pt path(s)
                   device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
                   half=False,  # use FP16 half-precision inference
                   dnn=False,  # use OpenCV DNN for ONNX inference
                   ):
        current_dir = os.path.dirname(sys.executable)
        weights = os.path.join(current_dir, "yolov5m.pt")
        print(weights)
        try :
            device=select_device(device)
        except Exception as e:
            print("模型加载发生错误:", str(e))
        print(device)
        half &= device.type != 'cpu'  # half precision only supported on CUDA
        device = select_device(device)
        print(device)
        try:
            model = DetectMultiBackend(weights, device=device, dnn=dnn)
            print("模型加载完成!")
        except Exception as e:
            print("模型加载发生错误:", str(e))
        print(weights)
        stride, names, pt, jit, onnx = model.stride, model.names, model.pt, model.jit, model.onnx
        # Half
        half &= pt and device.type != 'cpu'  # half precision only supported by PyTorch on CUDA
        if pt:
            model.model.half() if half else model.model.float()
        print("模型加载完成!")
        return model

    def run(self):
        self.vid_source = self.rtmp_url
        self.webcam = False
        from windows.start_record_threads import StartRecordThread
        self.record_thread = StartRecordThread(self.base_dir, self.rtmp_url, self.name)
        photo_path = os.path.join(self.base_dir, "live_videos", "temp_frames{}".format(self.rid))
        if not os.path.exists(photo_path):
            os.makedirs(photo_path)
        # command = f"ffmpeg -i {} -vf fps=0.2 {}/frame_%04d.jpg".format(self.rtmp_url, photo_path)
        while True:
            if self.terminate_flag:
                print("正在停止监测")
                # 如果正在录制就停止录制
                if self.record_thread:
                    print("正在关闭录制线程")
                    self.stop_record()
                shutil.rmtree(photo_path)
                print("检测图片文件夹删除完成")
                if self.p is not None:
                    self.p.stdin.write('q'.encode("GBK"))
                    self.p.communicate()
                    self.p.kill()
                break
            timestamp = int(time.time())
            output_file = f"{photo_path}\{timestamp}.jpg"
            cmd = "ffmpeg -ss 5 -i {} -frames:v 1 {}".format(self.rtmp_url, output_file)
            print(111, cmd)
            self.p = p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
            time.sleep(10)
            self.img2predict = output_file
            if os.path.exists(self.img2predict):
                print(96)
                self.detect_img()
            time.sleep(1)
            print("下一次提取帧")

        print("即将关闭人物监测线程")
        self.close_vid()

    '''
    ***选取视频帧进行检测***
    '''

    def upload_img(self):
        photo_path = os.path.join(self.base_dir, "live_videos", "temp_frames")
        if not os.path.exists(photo_path):
            os.makedirs(photo_path)
        # command = f"ffmpeg -i {} -vf fps=0.2 {}/frame_%04d.jpg".format(self.rtmp_url, photo_path)
        while True:
            if self.terminate_flag:
                print("正在停止监测")
                if self.record_thread.isRunning():
                    print("正在关闭录制线程")
                    self.stop_record()
                break
            timestamp = int(time.time())
            output_file = f"{photo_path}\{timestamp}.jpg"
            cmd = "ffmpeg -ss 5 -i {} -frames:v 1 {}".format(self.rtmp_url, output_file)
            print(cmd)
            self.p = p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
            time.sleep(5)
            self.img2predict = output_file
            if os.path.exists(output_file):
                self.detect_img()
            time.sleep(1)
            print("下一次提取帧")

        print("即将关闭人物监测线程")
        self.close_vid()

    '''
    ***检测图片***
    '''
    def detect_img(self):
        model = self.model
        output_size = self.output_size
        source = self.img2predict  # file/dir/URL/glob, 0 for webcam
        imgsz = [640,640]  # inference size (pixels)
        conf_thres = 0.25  # confidence threshold
        iou_thres = 0.45  # NMS IOU threshold
        max_det = 1000  # maximum detections per image
        device = self.device  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img = False  # show results
        save_txt = False  # save results to *.txt
        save_conf = False  # save confidences in --save-txt labels
        save_crop = False  # save cropped prediction boxes
        nosave = False  # do not save images/videos
        classes = None  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms = False  # class-agnostic NMS
        augment = False  # ugmented inference
        visualize = False  # visualize features
        line_thickness = 3  # bounding box thickness (pixels)
        hide_labels = False  # hide labels
        hide_conf = False  # hide confidences
        half = False  # use FP16 half-precision inference
        dnn = False  # use OpenCV DNN for ONNX inference
        print(source)
        if source == "":
            QMessageBox.warning(self, "请上传", "请先上传图片再进行检测")
        else:
            source = str(source)
            device = select_device(self.device)
            webcam = False
            stride, names, pt, jit, onnx = model.stride, model.names, model.pt, model.jit, model.onnx
            imgsz = check_img_size(imgsz, s=stride)  # check image size
            save_img = not nosave and not source.endswith('.txt')  # save inference images
            # Dataloader
            if webcam:
                view_img = check_imshow()
                cudnn.benchmark = True  # set True to speed up constant image size inference
                dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt and not jit)
                bs = len(dataset)  # batch_size
            else:
                dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt and not jit)
                bs = 1  # batch_size
            vid_path, vid_writer = [None] * bs, [None] * bs
            # Run inference
            if pt and device.type != 'cpu':
                model(torch.zeros(1, 3, *imgsz).to(device).type_as(next(model.model.parameters())))  # warmup
            dt, seen = [0.0, 0.0, 0.0], 0
            for path, im, im0s, vid_cap, s in dataset:
                t1 = time_sync()
                im = torch.from_numpy(im).to(device)
                im = im.half() if half else im.float()  # uint8 to fp16/32
                im /= 255  # 0 - 255 to 0.0 - 1.0
                if len(im.shape) == 3:
                    im = im[None]  # expand for batch dim
                t2 = time_sync()
                dt[0] += t2 - t1
                # Inference
                # visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
                pred = model(im, augment=augment, visualize=visualize)
                t3 = time_sync()
                dt[1] += t3 - t2
                # NMS
                pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)
                dt[2] += time_sync() - t3
                # Second-stage classifier (optional)
                # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)
                # Process predictions
                for i, det in enumerate(pred):  # per image
                    seen += 1
                    if webcam:  # batch_size >= 1
                        p, im0, frame = path[i], im0s[i].copy(), dataset.count
                        s += f'{i}: '
                    else:
                        p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)
                    p = Path(p)  # to Path
                    s += '%gx%g ' % im.shape[2:]  # print string
                    gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                    imc = im0.copy() if save_crop else im0  # for save_crop
                    annotator = Annotator(im0, line_width=line_thickness, example=str(names))
                    if len(det):
                        # Rescale boxes from img_size to im0 size
                        det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

                        # Print results
                        print("开始输出结果")
                        for c in det[:, -1].unique():
                            n = (det[:, -1] == c).sum()  # detections per class
                            print("画面内有{}个人物".format(n.item()))
                            if n.item() == 0:          # 图片内没有人物
                                # 判断录制线程是否在进行
                                if self.record_flag:
                                    # 停止直播录制
                                    print("正在停止直播录制")
                                    self.stop_record()
                                    self.record_flag = False
                                    # 更新页面显示为"人物离开"
                                if self.previous_status != "人物离开":
                                    print("人物离开")
                                    self.person_status.emit("人物离开")
                                    self.previous_status = "人物离开"
                                pass
                            else:
                                # 判断录制线程是否在进行
                                if self.previous_status != "录制中":
                                    print("人物出现")
                                    self.person_status.emit("录制中")
                                    self.previous_status = "录制中"
                                if not self.record_flag:
                                    # 开始直播录制
                                    print("开始进行直播录制")
                                    self.record_flag = True
                                    self.record_thread.start()
                            s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string
                    else:
                        # 判断录制线程是否在进行
                        if self.record_flag:
                            # 停止直播录制
                            print("正在停止直播录制")
                            self.stop_record()
                            # 更新页面显示为"人物离开"
                        if self.previous_status != "人物离开":
                            self.person_status.emit("人物离开")
                            self.previous_status = "人物离开"

                    LOGGER.info(f'{s}Done. ({t3 - t2:.3f}s)')


    def stop_record(self):
        self.record_thread.stop_thread()
        self.record_thread.quit()
        self.record_thread.wait()

    '''
    ### 界面重置事件 ### 
    '''

    def reset_vid(self):
        self.vid_source = '0'
        self.webcam = True

    '''
    ### 视频重置事件 ### 
    '''

    def close_vid(self):
        # 停止录制
        self.p.stdin.write('q'.encode("GBK"))
        self.p.communicate()
        self.p.kill()
        if self.record_flag:
            self.stop_record()
        self.stopEvent.set()
        self.reset_vid()

