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

print("Đang khởi động Camera...")
cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("Khe 0 không phản hồi, đang chuyển sang khe 1...")
    cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("❌ Không mở được camera. Vui lòng kiểm tra lại cáp.")
    exit()

time.sleep(1)

print("✅ ĐÃ MỞ CAMERA THÀNH CÔNG! Bấm 'q' để thoát.")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue

    cv2.imshow("Camera Jetson Nano", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Đã đóng camera an toàn.")
