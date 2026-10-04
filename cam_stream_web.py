import cv2
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading

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

print("Đang kết nối camera...")
cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=0), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("Khe 0 không phản hồi, thử khe 1...")
    cap = cv2.VideoCapture(gstreamer_pipeline(sensor_id=1), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Không thấy camera CSI, thử tìm USB Camera...")
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Lỗi: Không thể mở được camera nào. Vui lòng kiểm tra lại cáp kết nối!")
    exit(1)

print("✅ Đã kết nối Camera thành công!")

output_frame = None
lock = threading.Lock()

def capture_frames():
    global output_frame, lock
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        with lock:
            output_frame = frame.copy()

class CamStreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <html>
            <head>
                <title>Jetson Nano - Camera Live Stream</title>
                <style>
                    body { font-family: Arial, sans-serif; background:
                    h2 { color:
                    img { border: 3px solid
                </style>
            </head>
            <body>
                <h2>🎥 Jetson Nano - Camera Live Stream</h2>
                <p>Đang xem trực tiếp từ camera của Jetson Nano qua Wi-Fi</p>
                <img src="/stream.mjpg" />
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with lock:
                        if output_frame is None:
                            continue
                        ret, jpeg = cv2.imencode('.jpg', output_frame)
                        if not ret:
                            continue
                        data = jpeg.tobytes()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(data))
                    self.end_headers()
                    self.wfile.write(data)
                    self.wfile.write(b'\r\n')
                    time.sleep(0.03)
            except Exception:
                pass
        else:
            self.send_error(404)
            self.end_headers()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

t = threading.Thread(target=capture_frames, daemon=True)
t.start()

PORT = 5000
server = ThreadedHTTPServer(('0.0.0.0', PORT), CamStreamHandler)
print(f"\n=======================================================")
print(f"🚀 CAMERA ĐANG PHÁT TRỰC TIẾP!")
print(f"👉 Mở trình duyệt trên máy tính và truy cập:")
print(f"   http://192.168.0.101:{PORT}")
print(f"=======================================================")
print("Nhấn Ctrl + C để dừng.\n")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nĐang tắt camera...")
    cap.release()
    server.server_close()
    print("Đã tắt an toàn.")
