import torch
from torchvision import transforms
from PIL import Image
import numpy as np
import cv2

# 加载YOLOv5模型
model_path = 'yolo/runs/train/exp_yolov5s/weights/yolov5m.pt'
model = torch.load(model_path, map_location=torch.device('cpu'))['model'].float()
model.eval()

# 读取要测试的图片
image_path = "live_videos/temp_frames30549904/1701676259.jpg"
image = Image.open(image_path)

# 进行图像变换和预处理
transform = transforms.Compose([
    transforms.Resize((1920, 1080)),  # 调整图片大小
    transforms.ToTensor(),
])

img_tensor = transform(image).unsqueeze(0)  # 添加 batch 维度

# 运行模型推理
with torch.no_grad():
    results = model(img_tensor)

# 获取检测结果
pred = results.xyxy[0]  # 获取第一张图片的预测结果

# 获取置信度大于阈值的检测框
conf_threshold = 0.5
filtered_boxes = pred[pred[:, 4] > conf_threshold]

# 输出检测到的人脸数量
num_faces = len(filtered_boxes)
print(f"Number of faces detected: {num_faces}")

# 在图像上绘制检测结果
drawn_image = image
