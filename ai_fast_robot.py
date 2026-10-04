import jetson.inference
import jetson.utils
import sys

camera = jetson.utils.videoSource("csi://0", argv=["--input-width=1280", "--input-height=720", "--input-rate=30"])

display = jetson.utils.videoOutput("display://0")

print("Đang nạp mô hình TensorRT...")
net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)

print("\n" + "="*60)
print("HỆ THỐNG AI TỐC ĐỘ CAO (25 - 30 FPS) ĐANG CHẠY!")
print("Bấm phím 'q' hoặc đóng cửa sổ để thoát.")
print("="*60 + "\n")

while display.IsStreaming():
    img = camera.Capture()
    if img is None:
        continue

    detections = net.Detect(img, overlay="box,labels,conf")

    robot_action = "FORWARD"
    width = img.width

    for det in detections:
        if det.Height > 120:
            cx = det.Center[0]
            if cx < (width / 3):
                robot_action = "TURN RIGHT"
            elif cx > (2 * width / 3):
                robot_action = "TURN LEFT"
            else:
                robot_action = "STOP / EVADE"
                break

    fps = net.GetNetworkFPS()
    display.SetStatus(f"ACTION: {robot_action} | FPS: {fps:.1f}")

    display.Render(img)

print("Đã đóng chương trình.")
