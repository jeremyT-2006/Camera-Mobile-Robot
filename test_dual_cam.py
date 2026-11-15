import cv2
import numpy as np
import time
import sys

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=640,
    display_height=360,
    framerate=30,
    flip_method=0,
):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink drop=1"
    )

print("=" * 60)
print("  KIỂM TRA ĐỒNG THỜI 2 CAMERA CSI (CAM0 & CAM1) TRÊN JETSON NANO")
print("=" * 60)

print("\n[1/3] Đang kết nối Camera 0 (sensor-id=0)...")
cap0 = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
if not cap0.isOpened():
    print(" [LỖI] Không thể mở Camera 0 (sensor-id=0).")
else:
    print(" [OK] Camera 0 đã sẵn sàng!")

print("\n[2/3] Đang kết nối Camera 1 (sensor-id=1)...")
cap1 = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)
if not cap1.isOpened():
    print(" [LỖI] Không thể mở Camera 1 (sensor-id=1).")
else:
    print(" [OK] Camera 1 đã sẵn sàng!")

if not cap0.isOpened() and not cap1.isOpened():
    print("\n[THẤT BẠI] Cả 2 camera đều không mở được. Kiểm tra cáp và 'ls /dev/video*'.")
    sys.exit(1)

print("\n[3/3] Đang truyền hình ảnh lên màn hình... Bấm 'q' để thoát.")
prev_time = time.time()

while True:
    frame0 = None
    frame1 = None

    if cap0.isOpened():
        ret0, frame0 = cap0.read()
        if not ret0:
            frame0 = None

    if cap1.isOpened():
        ret1, frame1 = cap1.read()
        if not ret1:
            frame1 = None

    # Tạo khung hình hiển thị ghép đôi
    h, w = 360, 640
    black_canvas = np.zeros((h, w, 3), dtype=np.uint8)

    if frame0 is None:
        frame0 = black_canvas.copy()
        cv2.putText(frame0, "CAM 0: DISCONNECTED", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(frame0, "CAM 0 (LEFT / FRONT)", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    if frame1 is None:
        frame1 = black_canvas.copy()
        cv2.putText(frame1, "CAM 1: DISCONNECTED", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(frame1, "CAM 1 (RIGHT / WIDE)", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Ghép 2 ảnh cạnh nhau (Side-by-Side: 1280x360)
    combined = np.hstack((frame0, frame1))

    now = time.time()
    fps = 1.0 / (now - prev_time) if (now - prev_time) > 0 else 0
    prev_time = now

    cv2.putText(combined, f"FPS: {fps:.1f}", (1280 - 140, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow("DUAL CSI CAMERA TEST - JETSON NANO", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if cap0.isOpened():
    cap0.release()
if cap1.isOpened():
    cap1.release()
cv2.destroyAllWindows()
print("\n[DONE] Đã đóng camera an toàn.")
