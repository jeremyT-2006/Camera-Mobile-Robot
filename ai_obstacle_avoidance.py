import cv2
import time
import sys

# Kiểm tra thư viện AI của NVIDIA Jetson
USE_JETSON_INFERENCE = False
try:
    import jetson.inference
    import jetson.utils
    USE_JETSON_INFERENCE = True
    print("✅ Đã phát hiện thư viện NVIDIA TensorRT (jetson.inference)!")
except ImportError:
    print("⚠️ Chưa có jetson.inference, chương trình sẽ chạy chế độ camera thuần.")

def gstreamer_pipeline(sensor_id=0, capture_width=1280, capture_height=720, display_width=640, display_height=480, framerate=30, flip_method=0):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink drop=1"
    )

print("Đang khởi động Camera cho Mobile Robot...")
cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("❌ Lỗi: Không thể mở camera CSI. Vui lòng kiểm tra lại cáp.")
    sys.exit()

time.sleep(1)

# Tải mô hình AI SSD-MobileNet v2 nếu có jetson.inference
net = None
if USE_JETSON_INFERENCE:
    print("Đang nạp mô hình AI SSD-MobileNet-v2 (TensorRT)...")
    net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.45)
    print("✅ Nạp Model AI thành công!")

WIDTH = 640
HEIGHT = 480
# Chia khung hình thành 3 vùng: Trái (0 - 213), Giữa (213 - 426), Phải (426 - 640)
ZONE_LEFT_LIMIT = WIDTH // 3
ZONE_RIGHT_LIMIT = 2 * (WIDTH // 3)

prev_time = time.time()
print("\n" + "="*60)
print("🚀 HỆ THỐNG TRÁNH VẬT CẢN (OBSTACLE AVOIDANCE) ĐANG CHẠY!")
print("Bấm phím 'q' trên màn hình Dell để THOÁT.")
print("="*60 + "\n")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue

    current_time = time.time()
    fps = 1 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
    prev_time = current_time

    # Trạng thái điều khiển mặc định: Đường trống -> TIẾN THẲNG
    robot_action = "FORWARD"
    action_color = (0, 255, 0) # Xanh lá
    obstacle_detected = False

    # 1. XỬ LÝ NHẬN DIỆN VẬT CẢN BẰNG MODEL AI
    if USE_JETSON_INFERENCE and net is not None:
        # Chuyển đổi frame từ OpenCV sang định dạng CUDA của NVIDIA
        cuda_img = jetson.utils.cudaFromNumpy(frame)
        detections = net.Detect(cuda_img, overlay="none")
        
        for det in detections:
            # Tọa độ vật thể
            x1 = int(det.Left)
            y1 = int(det.Top)
            x2 = int(det.Right)
            y2 = int(det.Bottom)
            cx = int(det.Center[0])
            bh = int(det.Height)
            label = net.GetClassDesc(det.ClassID)
            conf = det.Confidence

            # Vẽ khung nhận diện Bounding Box lên màn hình
            box_color = (0, 255, 0)
            is_close = bh > 110  # Chiều cao > 110px nghĩa là ở cự ly gần

            if is_close:
                box_color = (0, 0, 255) # Đỏ cảnh báo vật cản gần
                obstacle_detected = True
                if ZONE_LEFT_LIMIT <= cx <= ZONE_RIGHT_LIMIT:
                    robot_action = "STOP / EVADE"
                    action_color = (0, 0, 255)
                elif cx < ZONE_LEFT_LIMIT and robot_action != "STOP / EVADE":
                    robot_action = "TURN RIGHT"
                    action_color = (0, 255, 255)
                elif cx > ZONE_RIGHT_LIMIT and robot_action != "STOP / EVADE":
                    robot_action = "TURN LEFT"
                    action_color = (0, 255, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

    # 2. VẼ GIAO DIỆN QUAN SÁT ROBOT (HUD)
    # Vẽ 2 vạch phân cách 3 vùng: Trái | Giữa | Phải
    cv2.line(frame, (ZONE_LEFT_LIMIT, 0), (ZONE_LEFT_LIMIT, HEIGHT), (200, 200, 200), 1)
    cv2.line(frame, (ZONE_RIGHT_LIMIT, 0), (ZONE_RIGHT_LIMIT, HEIGHT), (200, 200, 200), 1)

    cv2.putText(frame, "LEFT", (ZONE_LEFT_LIMIT // 2 - 25, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "CENTER", (WIDTH // 2 - 35, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "RIGHT", (ZONE_RIGHT_LIMIT + (WIDTH - ZONE_RIGHT_LIMIT)//2 - 30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # Hiển thị Quyết định của Robot (Action Banner)
    cv2.rectangle(frame, (0, HEIGHT - 65), (WIDTH, HEIGHT), (0, 0, 0), -1)
    cv2.putText(frame, f"ACTION: {robot_action}", (20, HEIGHT - 22), cv2.FONT_HERSHEY_SIMPLEX, 1.0, action_color, 3)
    cv2.putText(frame, f"FPS: {fps:.1f}", (WIDTH - 140, HEIGHT - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("MOBILE ROBOT - OBSTACLE AVOIDANCE AI", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Đã tắt hệ thống Robot an toàn.")
