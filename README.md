 Jetson Nano Mobile Robot - Vision & AI Obstacle Avoidance

Dự án phát triển hệ thống thị giác máy tính và trí tuệ nhân tạo  cho Mobile Robot  sử dụng bo mạch NVIDIA Jetson Nano (4GB), camera CSI và mô hình suy luận thời gian thực SSD-MobileNet v2 (TensorRT)

Dự án bao gồm toàn bộ mã nguồn kiểm thử phần cứng, thuật toán phân vùng tránh vật cản , đánh giá độ trễ  các định dạng truyền thông.

*Tính Năng Nổi Bật
- Nhúng mô hình `SSD-MobileNet v2` thông qua `TensorRT` đạt 10-15 FPS.
- Thuật toán tránh vật cản 3 vùng :
  - Tự động chia khung hình thành 3 vùng: LEFT | CENTER | RIGHT.
  - Đánh giá khoảng cách vật thể dựa trên kích thước Bounding Box.
  - Tự động xuất quyết định điều khiển robot: FORWARD, STOP / EVADE, TURN LEFT, TURN RIGHT.
- Hỗ trợ phần cứng chuyên sâu:
  - Tối ưu hóa GStreamer pipeline cho Camera CSI (IMX219).
  - Cơ chế tăng tốc Zero-Copy phần cứng qua jetson.utils.videoSource.
- Bộ công cụ đo kiểm thực nghiệm (Benchmarking Suite):
  - Đo sụt áp khối nguồn 3S 18650 qua mạch hạ áp XL4016 theo các mốc thời gian (1h, 2h, 3h).

*Cấu Trúc Phần Cứng (Hardware Setup)
- Bộ xử lý trung tâm: NVIDIA Jetson Nano Developer Kit (4GB RAM, 128-core Maxwell GPU).
- Cảm biến hình ảnh: Camera CSI 8MP (Sony IMX219).
- Khối nguồn:
  - Nguồn sơ cấp: 3 cell pin Li-ion 18650 mắc nối tiếp (3S: $11.1\text{V} - 12.6\text{V}$).
  - Mạch hạ áp: DC-DC Buck Converter XL4016 (200W, 8A) hạ áp xuống 5.20V cấp vào cổng DC 5.5mm (Jumper J48 đóng).
- Hiển thị & Giám sát:Màn hình Dell E1715S qua cổng DisplayPort / USB Wi-Fi adapter.

* Hướng Dẫn sử Dụng
1. Yêu cầu hệ thống
- Hệ điều hành: Ubuntu 18.04 LTS (JetPack 4.5 / 4.6)
- Thư viện NVIDIA: jetson-inference, jetson-utils, OpenCV (có GStreamer & CUDA).
  
2. Cài đặt môi trường
- Cập nhật hệ thống
sudo apt update
sudo apt install -y python3-pip
- Cài đặt công cụ theo dõi phần cứng
sudo -H pip3 install -U jetson-stats

3. Mở khóa xung nhịp tối đa (Khuyên dùng)
Để đạt tốc độ xử lý 25 - 30 FPS và tránh bị bóp xung:
sudo nvpmodel -m 0
sudo jetson_clocks
4. Chạy các chương trình
A. Kiểm tra Camera CSI:
python3 test_cam.py
B. Chạy hệ thống AI Tránh vật cản (Obstacle Avoidance):
python3 ai_obstacle_avoidance.py
C. Chạy bản tăng tốc phần cứng Zero-Copy:
python3 ai_fast_robot.py
D. Chạy đánh giá độ trễ định dạng dữ liệu:
python3 benchmark_latency.py



