import cv2
import time

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=640,
    display_height=480,
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

print("Đang khởi động Camera cho Kịch bản 1 (Chạy Cam riêng)...")
cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
active_sensor = 0

if not cap.isOpened():
    print("Thử tiếp khe CAM1...")
    cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)
    active_sensor = 1

if not cap.isOpened():
    print("❌ Lỗi: Không thể mở camera.")
    exit()

time.sleep(1)

start_time = time.time()
prev_time = time.time()

print("="*55)
print(f"✅ ĐANG CHẠY KỊCH BẢN 1 (CAMERA HIỂN THỊ LIÊN TỤC)")
print("👉 Bạn hãy dùng Đồng hồ vạn năng để tự đo sụt áp của Pin.")
print("👉 Bấm phím 'q' trên màn hình Dell khi muốn dừng thí nghiệm.")
print("="*55)

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue

    current_time = time.time()
    elapsed_seconds = int(current_time - start_time)
    
    # Tính thời gian chạy (Giờ : Phút : Giây)
    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60
    timer_str = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"

    # Tính FPS
    fps = 1 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
    prev_time = current_time

    # Vẽ đồng hồ đếm giờ và FPS lên màn hình camera
    cv2.putText(frame, f"KICH BAN 1: CAM ONLY", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(frame, timer_str, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("THI NGHIEM KICH BAN 1 - JETSON NANO", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"Đã dừng kịch bản 1 sau: {timer_str}")
