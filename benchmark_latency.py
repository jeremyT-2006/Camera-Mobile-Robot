import cv2
import time
import json
import struct
import sys

def gstreamer_pipeline(sensor_id=0):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
        f"nvvidconv ! video/x-raw, width=640, height=480, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
    )

print("="*60)
print("   BÀI THỬ NGHIỆM: ĐÁNH GIÁ ẢNH HƯỞNG CỦA ĐỊNH DẠNG DỮ LIỆU")
print("="*60)

cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("❌ Lỗi camera, dùng chế độ giả lập frame...")
    frame = None
else:
    time.sleep(1)
    ret, frame = cap.read()
    print("✅ Đã kết nối camera thành công!")

objects = [
    {"id": 1, "class": "car", "conf": 0.93, "bbox": [150, 200, 220, 180]},
    {"id": 2, "class": "person", "conf": 0.88, "bbox": [400, 180, 80, 210]},
    {"id": 3, "class": "sign", "conf": 0.95, "bbox": [520, 100, 60, 60]}
]

trials = 2000

t0 = time.perf_counter()
for _ in range(trials):
    data_json = json.dumps(objects).encode('utf-8')
t_json = (time.perf_counter() - t0) / trials * 1000
size_json = len(data_json)

t0 = time.perf_counter()
for _ in range(trials):
    rows = [f"{o['id']},{o['bbox'][0]},{o['bbox'][1]},{o['bbox'][2]},{o['bbox'][3]},{o['conf']:.2f}" for o in objects]
    data_csv = (";".join(rows) + "\n").encode('utf-8')
t_csv = (time.perf_counter() - t0) / trials * 1000
size_csv = len(data_csv)

t0 = time.perf_counter()
for _ in range(trials):
    b_data = bytearray()
    for o in objects:
        b_data.extend(struct.pack("Bhhhhf", o['id'], o['bbox'][0], o['bbox'][1], o['bbox'][2], o['bbox'][3], o['conf']))
t_struct = (time.perf_counter() - t0) / trials * 1000
size_struct = len(b_data)

print("\n--- BẢNG KẾT QUẢ ĐO ĐẠC THỰC TẾ TRÊN JETSON NANO ---")
print(f"{'Định dạng (Format)':<22} | {'Kích thước gói tin':<20} | {'Độ trễ đóng gói (Latency)':<25}")
print("-" * 72)
print(f"{'1. JSON':<22} | {size_json:>10} Bytes       | {t_json:>14.4f} ms")
print(f"{'2. Plain Text (CSV)':<22} | {size_csv:>10} Bytes       | {t_csv:>14.4f} ms")
print(f"{'3. Raw Binary Struct':<22} | {size_struct:>10} Bytes       | {t_struct:>14.4f} ms")
print("-" * 72)

serial_speed = 11520
print("\nƯớc tính độ trễ truyền tải qua Serial (Baud 115200):")
print(f"- JSON               : {(size_json / serial_speed) * 1000:.2f} ms")
print(f"- Plain Text (CSV)   : {(size_csv / serial_speed) * 1000:.2f} ms")
print(f"- Raw Binary Struct  : {(size_struct / serial_speed) * 1000:.2f} ms  <-- TỐI ƯU NHẤT CHO ROBOT/XE")

if cap.isOpened():
    cap.release()
