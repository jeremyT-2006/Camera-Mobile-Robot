# 🤖 Jetson Nano Mobile Robot - Vision & AI Obstacle Avoidance

Dự án phát triển hệ thống thị giác máy tính và trí tuệ nhân tạo (AI/Computer Vision) cho **Mobile Robot (Xe tự hành)** sử dụng bo mạch **NVIDIA Jetson Nano (4GB)**, camera CSI và mô hình suy luận thời gian thực **SSD-MobileNet v2 (TensorRT)**.

Dự án bao gồm toàn bộ mã nguồn kiểm thử phần cứng, thuật toán phân vùng tránh vật cản (Obstacle Avoidance), công cụ đo kiểm sụt áp pin và đánh giá độ trễ (Latency Benchmark) các định dạng truyền thông.

---

## 📌 Tính Năng Nổi Bật

- **AI Nhận diện thời gian thực:** Nhúng mô hình `SSD-MobileNet v2` thông qua `TensorRT` đạt **25 - 30 FPS**.
- **Thuật toán tránh vật cản 3 vùng (3-Zone Navigation):**
  - Tự động chia khung hình thành 3 vùng: **LEFT | CENTER | RIGHT**.
  - Đánh giá khoảng cách vật thể dựa trên kích thước Bounding Box.
  - Tự động xuất quyết định điều khiển robot: `FORWARD`, `STOP / EVADE`, `TURN LEFT`, `TURN RIGHT`.
- **Hỗ trợ phần cứng chuyên sâu:**
  - Tối ưu hóa GStreamer pipeline cho Camera CSI (IMX219).
  - Cơ chế tăng tốc Zero-Copy phần cứng qua `jetson.utils.videoSource`.
- **Bộ công cụ đo kiểm thực nghiệm (Benchmarking Suite):**
  - Đo sụt áp khối nguồn 3S 18650 qua mạch hạ áp XL4016 theo các mốc thời gian (1h, 2h, 3h).
  - So sánh chi tiết độ trễ và kích thước gói tin giữa **JSON**, **CSV (Plain Text)** và **Raw Binary Struct**.

---

## 🛠️ Cấu Trúc Phần Cứng (Hardware Setup)

- **Bộ xử lý trung tâm:** NVIDIA Jetson Nano Developer Kit (4GB RAM, 128-core Maxwell GPU).
- **Cảm biến hình ảnh:** Camera CSI 8MP (Sony IMX219).
- **Khối nguồn:**
  - Nguồn sơ cấp: 3 cell pin Li-ion 18650 mắc nối tiếp (3S: $11.1\text{V} - 12.6\text{V}$).
  - Mạch hạ áp: DC-DC Buck Converter XL4016 (200W, 8A) hạ áp xuống **$5.20\text{V}$** cấp vào cổng DC 5.5mm (Jumper J48 đóng).
- **Hiển thị & Giám sát:** Màn hình Dell E1715S qua cổng DisplayPort / USB Wi-Fi adapter.

---

## 📁 Cấu Trúc Thư Mục & Tệp Mã Nguồn

```text
jetson-nano-mobile-robot/
├── README.md                  # Tài liệu hướng dẫn dự án
├── requirements.txt           # Danh sách thư viện Python cần thiết
├── .gitignore                 # Các tệp loại trừ không commit lên Git
│
├── test_cam.py                # Script kiểm tra kết nối Camera CSI/USB với GStreamer
├── ai_obstacle_avoidance.py   # Hệ thống AI tránh vật cản hoàn chỉnh (HUD + 3 Zones)
├── ai_fast_robot.py           # Bản tối ưu Zero-Copy phần cứng đạt 25 - 30+ FPS
├── run_workload1.py           # Bài test Kịch bản 1 (Camera only) kèm đồng hồ đếm giờ Uptime
├── benchmark_latency.py       # Công cụ đo độ trễ và dung lượng: JSON vs CSV vs Binary
└── cam_stream_web.py          # Luồng streaming camera qua giao diện Web/Mạng không dây
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Yêu cầu hệ thống
- Hệ điều hành: **Ubuntu 18.04 LTS (JetPack 4.5 / 4.6)**
- Thư viện NVIDIA: `jetson-inference`, `jetson-utils`, `OpenCV` (có GStreamer & CUDA).

### 2. Cài đặt môi trường
```bash
# Cập nhật hệ thống
sudo apt update
sudo apt install -y python3-pip

# Cài đặt công cụ theo dõi phần cứng
sudo -H pip3 install -U jetson-stats
```

### 3. Mở khóa xung nhịp tối đa (Khuyên dùng)
Để đạt tốc độ xử lý 25 - 30 FPS và tránh bị bóp xung:
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### 4. Chạy các chương trình

#### A. Kiểm tra Camera CSI:
```bash
python3 test_cam.py
```

#### B. Chạy hệ thống AI Tránh vật cản (Obstacle Avoidance):
```bash
python3 ai_obstacle_avoidance.py
```
*(Nếu chạy qua SSH từ Laptop, thêm `DISPLAY=:0 python3 ai_obstacle_avoidance.py`)*.

#### C. Chạy bản tăng tốc phần cứng Zero-Copy:
```bash
python3 ai_fast_robot.py
```

#### D. Chạy bài đo sụt áp nguồn (Kịch bản 1 có đồng hồ Uptime):
```bash
python3 run_workload1.py
```

#### E. Chạy đánh giá độ trễ định dạng dữ liệu:
```bash
python3 benchmark_latency.py
```

---

## 📊 Kết Quả Thực Nghiệm & Báo Cáo

### 1. So sánh định dạng dữ liệu (Data Format Latency Benchmark)

| Định dạng (Format) | Dung lượng gói tin | Độ trễ đóng gói ($T_{serialize}$) | Đánh giá ứng dụng trên Robot |
| :--- | :---: | :---: | :--- |
| **Raw Binary Struct** | **39 Bytes** | **0.012 ms** | ⭐ **Tối ưu nhất cho điều khiển thời gian thực qua Serial/UART** |
| **Plain Text (CSV)** | 78 Bytes | 0.035 ms | Đơn giản, dễ debug trực quan |
| **JSON** | 215 Bytes | 0.082 ms | Nặng, chỉ nên dùng cho Web Dashboard / REST API |

### 2. Đánh giá sụt áp nguồn pin 3S 18650 qua mạch hạ áp XL4016 ($5.2\text{V}$)

| Kịch bản thử nghiệm | Điện áp ban đầu ($V_0$) | Sau 1h ($\Delta V_1$) | Sau 2h ($\Delta V_2$) | Sau 3h ($\Delta V_3$) |
| :--- | :---: | :---: | :---: | :---: |
| **Kịch bản 1: Camera Only** | 12.60 V | 12.10 V (0.50 V) | 11.60 V (1.00 V) | 11.10 V (1.50 V) |
| **Kịch bản 2: Camera + AI (SSD-MobileNet)** | 12.60 V | 11.65 V (0.95 V) | 10.70 V (1.90 V) | 9.85 V (2.75 V) |

---

## 👥 Tác Giả & Bản Quyền
- Dự án được phát triển phục vụ học phần Kỹ thuật Lập trình / Nghiên cứu Mobile Robot.
- Giấy phép: MIT License.
