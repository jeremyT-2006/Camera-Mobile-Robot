import jetson.inference
import jetson.utils
import sys

# 1. Khởi tạo Camera CSI trực tiếp vào GPU (Zero-Copy)
# sensor-id=0 nếu cắm khe 0, sensor-id=1 nếu cắm khe 1
camera = jetson.utils.videoSource("csi://0", argv=["--input-width=1280", "--input-height=720", "--input-rate=30"])

# 2. Khởi tạo Màn hình xuất hình ảnh trực tiếp từ GPU
display = jetson.utils.videoOutput("display://0")

# 3. Nạp Model AI SSD-MobileNet v2 tối ưu hóa phần cứng
print("Đang nạp mô hình TensorRT...")
net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)

print("\n" + "="*60)
print("🚀 HỆ THỐNG AI TỐC ĐỘ CAO (25 - 30 FPS) ĐANG CHẠY!")
print("Bấm phím 'q' hoặc đóng cửa sổ để thoát.")
print("="*60 + "\n")

while display.IsStreaming():
    # Thu nhận ảnh trực tiếp trong bộ nhớ GPU
    img = camera.Capture()
    if img is None:
        continue

    # Nhận diện vật cản và tự động vẽ Bounding Box lên GPU
    detections = net.Detect(img, overlay="box,labels,conf")

    robot_action = "FORWARD"
    width = img.width

    for det in detections:
        # Nếu chiều cao vật cản > 120px nghĩa là ở cự ly gần
        if det.Height > 120:
            cx = det.Center[0]
            if cx < (width / 3):
                robot_action = "TURN RIGHT"
            elif cx > (2 * width / 3):
                robot_action = "TURN LEFT"
            else:
                robot_action = "STOP / EVADE"
                break

    # In quyết định ra Terminal và hiển thị lên thanh tiêu đề
    fps = net.GetNetworkFPS()
    display.SetStatus(f"ACTION: {robot_action} | FPS: {fps:.1f}")

    # Xuất hình ảnh siêu tốc ra màn hình Dell
    display.Render(img)

print("Đã đóng chương trình.")
