# BÁO CÁO KỸ THUẬT CHUYÊN SÂU: THIẾT KẾ VÀ ĐÁNH GIÁ THỰC NGHIỆM HỆ THỐNG THỊ GIÁC MÁY TÍNH & ĐIỀU HƯỚNG TRÁNH VẬT CẢN THỜI GIAN THỰC CHO MOBILE ROBOT

- **Kỹ sư thực hiện:** JeremyT (Trần Thái Trung)
- **Nền tảng phần cứng:** NVIDIA Jetson Nano Developer Kit (4GB, 128-core Maxwell GPU), Sony IMX219 CSI-2
- **Mã nguồn dự án (GitHub):** [https://github.com/jeremyT-2006/Camera-Mobile-Robot](https://github.com/jeremyT-2006/Camera-Mobile-Robot)
- **Thời gian hoàn thiện:** Tháng 10/2026

---

## I. TỔNG QUAN HỆ THỐNG & CƠ CẤU PHẦN CỨNG (SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo cấu trúc điều khiển phân tầng phân tán (Hierarchical Control Architecture) dành riêng cho xe tự hành (Autonomous Mobile Robot - AMR):

```text
               +-------------------------------------------------------------+
               |     TẦNG ĐIỀU KHIỂN CẤP CAO (HIGH-LEVEL PERCEPTION & NAV)   |
               |                     NVIDIA Jetson Nano 4GB                  |
               |  - Sony IMX219 (MIPI CSI-2 2-Lane @ 30 FPS)                |
               |  - TensorRT Accelerated Engine (SSD-MobileNet v2 FP16)      |
               |  - Pinhole Camera Model & Proportional Steering Controller  |
               +------------------------------+------------------------------+
                                              |
                                              | UART / Serial (Baud 115200)
                                              | Binary Packet (Header + Twist + CRC)
                                              v
               +-------------------------------------------------------------+
               |   TẦNG ĐIỀU KHIỂN CƠ CẤU CHẤP HÀNH (LOW-LEVEL CONTROLLER)   |
               |                  STM32F4 / Arduino Mega 2560                |
               |  - Differential Drive Kinematics Solver                     |
               |  - Closed-loop PID Motor Speed Controller                   |
               |  - Dual H-Bridge Driver (TB6612FNG / BTS7960)               |
               +------------------------------+------------------------------+
                                              | PWM & Direction
                                              v
                              [ĐỘNG CƠ DC + QUADRATURE ENCODER]
```

### 1. Phân tích thiết kế Khối Nguồn (Power Subsystem Analysis):
* **Nguồn sơ cấp:** Bộ pin Lithium-Ion 3S1P (3 cell 18650 mắc nối tiếp).
  * Điện áp sạc đầy ($V_{max}$): $12.60\text{ V}$ ($4.20\text{ V/cell}$).
  * Điện áp danh định ($V_{nom}$): $11.10\text{ V}$ ($3.70\text{ V/cell}$).
  * Điện áp cắt xả bảo vệ ($V_{cutoff}$): $9.00\text{ V}$ ($3.00\text{ V/cell}$).
* **Mạch biến đổi DC-DC (Buck Converter XL4016):**
  * Tần số đóng cắt cố định: $180\text{ kHz}$.
  * Hiệu suất chuyển đổi thực nghiệm: 
    $$\eta = \frac{P_{out}}{P_{in}} = \frac{V_{out} \cdot I_{out}}{V_{in} \cdot I_{in}} = \frac{5.20\text{ V} \times 2.10\text{ A}}{11.50\text{ V} \times 1.07\text{ A}} \approx 88.7\%$$
  * Công suất tiêu tán nhiệt: $P_{loss} = P_{in} - P_{out} \approx 1.39\text{ W}$ (được giải nhiệt qua cánh nhôm).
  * **Thiết lập điện áp bù sụt tải (Voltage Compensation):** Tinh chỉnh biến trở hồi tiếp $V_{FB}$ đưa điện áp không tải lên **$5.20\text{ V}$**. Khi GPU ăn tải đỉnh ($2.5\text{ A}$), sụt áp nội trở dây dẫn $\Delta V_{wire} = I \cdot R_{wire} \approx 0.25\text{ V}$, điện áp tại chân chip Tegra vẫn duy trì an toàn ở mức **$4.95\text{ V} \ge 4.75\text{ V}$**, triệt tiêu hoàn toàn lỗi ngắt hiển thị DisplayPort.

---

## II. THUẬT TOÁN ĐIỀU HƯỚNG & MÔ HÌNH TOÁN HỌC TRÁNH VẬT CẢN

Thay vì áp dụng điều khiển logic rời rạc (Bang-Bang Control) gây giật cơ khí, hệ thống áp dụng **Mô hình Camera Pinhole** kết hợp **Bộ điều khiển góc lái tỷ lệ (Proportional Steering)**:

```text
                                  Trục quang học Z
                                         ^
                                         |
                       Vật cản (X, Z)    *
                                        /|
                                       / |
                                      /  |
                                     /   |
                                    /    |
                      Góc lệch θ   /     |
                                  /_)____|
                                 Camera (0, 0)
```

### 1. Chuyển đổi tọa độ Pixel sang Góc lệch góc lái ($\theta_{error}$):
Với khung hình phân giải $W \times H = 640 \times 480$, tiêu cự tương đương $f_x \approx 500\text{ px}$, điểm gốc quang học $c_x = 320\text{ px}$.
Khi vật thể được phát hiện với tâm Bounding Box tại $u_c$:
$$\Delta u = u_c - c_x$$
Góc lệch phương vị (Azimuth Angle Error):
$$\theta_{error} = \arctan\left(\frac{u_c - c_x}{f_x}\right) \approx \frac{u_c - 320}{500} \text{ (rad)}$$

### 2. Ước lượng cự ly vật cản dựa trên Bounding Box (Monocular Distance Estimation):
Biết chiều cao vật lý trung bình của vật cản chuẩn $H_{real}$ (ví dụ người ngồi/thùng hàng $\approx 0.5\text{ m}$), cự ly ước tính $Z_{est}$:
$$Z_{est} = \frac{f_y \cdot H_{real}}{h_{bbox}}$$
Khi $h_{bbox} \ge 120\text{ px}$, khoảng cách $Z_{est} \le 0.8\text{ m}$ (ngưỡng nguy hiểm).

### 3. Phương trình điều khiển vận tốc Mobile Robot (Differential Drive):
Quy chuẩn vận tốc theo chuẩn ROS `geometry_msgs/Twist`:
* Vận tốc góc $\omega$ (rad/s):
  $$\omega = -K_p \cdot \theta_{error}$$
* Vận tốc dài $v$ (m/s):
  $$v = \begin{cases} 
  0 & \text{khi } Z_{est} \le Z_{safe} \text{ (Phanh khẩn cấp / Tránh né)} \\
  v_{max} \cdot \left(1 - \frac{|\theta_{error}|}{\theta_{max}}\right) & \text{khi đường thông thoáng (Giảm tốc khi vào cua)}
  \end{cases}$$
* Vận tốc góc 2 bánh xe ($v_L, v_R$) với khoảng cách 2 bánh $L$:
  $$v_R = v + \frac{\omega \cdot L}{2}, \quad v_L = v - \frac{\omega \cdot L}{2}$$

---

## III. TỐI ƯU HÓA SUY LUẬN AI BẰNG NVIDIA TENSORRT

### 1. Phân tích nút thắt cổ chai Pipeline:
* **OpenCV CPU Pipeline:** Tốc độ chỉ đạt **3 – 5 FPS**. Nguyên nhân: Tốn chu kỳ CPU chuyển đổi định dạng BGRx sang BGR (`videoconvert`), thực hiện copy bộ nhớ 3 lần giữa không gian người dùng (User Space), RAM hệ thống và bộ nhớ VRAM của GPU.
* **NVIDIA Zero-Copy Hardware Acceleration (`ai_fast_robot.py`):**
  * Dữ liệu từ cảm biến IMX219 đi qua bộ phần cứng ISP (Image Signal Processor) vào vùng đệm **NVMM (NVIDIA Memory Management)**.
  * Bộ nhớ ánh xạ trực tiếp (Unified Memory) cho phép nhân TensorRT truy xuất trực tiếp con trỏ CUDA không qua CPU.
  * Tốc độ suy luận đạt **28.4 FPS** liên tục.

### 2. Tối ưu hóa TensorRT Engine:
* **FP16 Half-Precision Quantization:** Lượng tử hóa trọng số từ Float32 sang Float16. Giảm 50% dung lượng chiếm dụng VRAM (chỉ còn $280\text{ MB}$), tăng gấp 2 lần thông lượng ALU trên kiến trúc GPU Maxwell.
* **Layer Fusion:** TensorRT tự động gộp các cụm toán tử liên hoàn `Conv + BatchNorm + ReLU` thành một CUDA Kernel thực thi duy nhất, loại bỏ hoàn toàn độ trễ đọc/ghi bộ nhớ trung gian.

---

## IV. BẢNG SỐ LIỆU ĐO KIỂM THỰC NGHIỆM ĐỊNH LƯỢNG (BENCHMARK RESULTS)

### 1. So sánh chi tiết các Định dạng dữ liệu truyền thông (Communication Format Benchmark):
Thực nghiệm đóng gói dữ liệu kết quả suy luận (Metadata gồm Object ID, 4 tọa độ Bounding Box, Class ID, Confidence Score):

| Định dạng truyền thông | Kích thước Payload | Thời gian đóng gói ($T_{ser}$) | Thời gian giải mã ($T_{deser}$) | Độ trễ truyền Serial 115.2 kbps | Tổng độ trễ End-to-End | Băng thông chiếm dụng (30 FPS) | Đánh giá kiến trúc |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Raw Binary Struct (C-packed)** | **39 Bytes** | **0.012 ms** | **0.008 ms** | **3.38 ms** | **~ 3.40 ms** | **9.36 kbps** | ⭐ **Tối ưu tuyệt đối cho vi điều khiển (STM32/Arduino)** |
| **Plain Text / CSV** | 78 Bytes | 0.035 ms | 0.042 ms | 6.77 ms | ~ 6.85 ms | 18.72 kbps | Dễ debug Serial Monitor, hiệu năng trung bình |
| **JSON** | 215 Bytes | 0.082 ms | 0.115 ms | 18.66 ms | ~ 18.86 ms | 51.60 kbps | Quá nặng, gây tràn hàng đợi UART buffer |

*Kết luận:* Định dạng **Binary Struct** nhanh hơn **5.5 lần** so với JSON và tiết kiệm **81.8%** băng thông truyền thông có dây.

### 2. Kết quả đo kiểm sụt áp nguồn Pin 3S 18650 qua các mốc thời gian:

| Kịch bản thử nghiệm | Áp ban đầu ($V_0$) | Sau 1 giờ ($V_1$) | Sau 2 giờ ($V_2$) | Sau 3 giờ ($V_3$) | Mức sụt áp tổng ($\Delta V$) | Công suất trung bình | Nhiệt độ SoC ($T_{max}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Kịch bản 1: Camera Streaming Only** | 12.60 V | 12.12 V | 11.64 V | 11.15 V | **1.45 V** | 3.65 W | 44.5 °C |
| **Kịch bản 2: Camera + TensorRT Inference** | 12.60 V | 11.72 V | 10.78 V | 9.85 V | **2.75 V** | 7.42 W | 58.2 °C |
| **Kịch bản 3: Cam + AI + Wireless Streaming** | 12.60 V | 11.45 V | 10.25 V | *Ngắt bảo vệ (2h40p)* | **3.60 V** | 8.85 W | 62.8 °C |
| **Kịch bản 4: Cam + AI + Serial Packet Output**| 12.60 V | 11.68 V | 10.70 V | 9.75 V | **2.85 V** | 7.55 W | 58.9 °C |

*Nhận xét:*
* Kịch bản AI ăn tải làm tốc độ xả pin tăng **89.6%** so với kịch bản chạy camera thuần.
* Khối truyền không dây (USB Wi-Fi) tiêu thụ năng lượng phụ trợ lớn (tăng ~ $1.4\text{ W}$), gây sụt áp nhanh ở vùng cuối dung lượng pin.

---

## V. TỔNG KẾT NGUYÊN NHÂN LỖI HỆ THỐNG & BIỆN PHÁP KHẮC PHỤC KỸ THUẬT

| STT | Hiện tượng lỗi | Phân tích nguyên nhân sâu xa | Giải pháp kỹ thuật khắc phục triệt để |
| :---: | :--- | :--- | :--- |
| **1** | Màn hình tắt báo `Entering Power Save Mode` khi chạy AI | Khi GPU ăn tải $2.5\text{ A}$, sụt áp trên dây dẫn làm $V_{in}$ Jetson $< 4.75\text{ V}$. PMIC tự ngắt khối điều khiển DisplayPort/HDMI để chống brownout. | Tinh chỉnh mạch Buck XL4016 lên **$5.20\text{ V} - 5.25\text{ V}$** tạo biên độ bù áp (headroom compensation) $0.25\text{ V}$. |
| **2** | Điện áp pin tụt xuống $6.75\text{ V}$ | Cell pin Li-ion bị xả vượt quá ngưỡng gãy (Knee Voltage $< 3.0\text{ V/cell}$). Mạch XL4016 mất ổn áp do $V_{in} - V_{out} < V_{dropout}$. | Ngắt tải khẩn cấp, thiết lập quy trình kiểm tra điện áp bằng VOM trước mỗi ca chạy, kích hoạt BMS 3S ngắt ở $9.0\text{ V}$. |
| **3** | Cảnh báo `! MAXN` / System Throttled | Chip cảm biến dòng INA3221 kích hoạt cờ cảnh báo quá dòng xung đỉnh khi xung nhịp chưa bị khóa cố định. | Thực thi `sudo nvpmodel -m 0` (10W Mode) và `sudo jetson_clocks` để khóa cứng tần số CPU @ 1.47 GHz, GPU @ 921 MHz. |
| **4** | Lỗi CSI `No cameras available` / Daemon Crash | Tháo cáp nóng gây xung đột I2C bus làm crash tiến trình `nvargus-daemon`; cắm ngược mặt tiếp điểm kim loại. | Chuẩn hóa quy trình: Mặt chân kim loại quay hướng vào tản nhiệt; khởi động lại daemon qua `sudo systemctl restart nvargus-daemon`. |
| **5** | Tốc độ xử lý thấp (3 – 5 FPS) | Tắc nghẽn băng thông do sao chép bộ nhớ trung gian qua các tầng phần mềm OpenCV CPU. | Chuyển đổi toàn diện sang thư viện tăng tốc phần cứng `jetson.utils.videoSource` và `videoOutput` (Zero-Copy Architecture). |

---

## VI. THIẾT KẾ GIAO THỨC TRUYỀN THÔNG ĐIỀU KHIỂN ROBOT (PROPOSED PACKET PROTOCOL)

Để sẵn sàng tích hợp với mạch điều khiển động cơ tầng dưới (STM32/Arduino), giao thức truyền thông nhị phân định dạng Frame chuẩn công nghiệp được xây dựng:

```text
+------+------+-----+---------+---------+----------+----------+
| SOF1 | SOF2 | CMD | V_LIN   | W_ANG   | DISTANCE | CHECKSUM |
| 0xAA | 0x55 | 1B  | 2B(int) | 2B(int) | 2B(uint) | 1B (XOR) |
+------+------+-----+---------+---------+----------+----------+
```
* **SOF (Start of Frame):** `0xAA, 0x55` đồng bộ hóa khung truyền.
* **CMD (Command Byte):** `0x01` (Chạy tự động tránh vật cản), `0x00` (Dừng khẩn cấp).
* **V_LIN:** Vận tốc dài đặt ($mm/s$, bù 2 số nguyên).
* **W_ANG:** Vận tốc góc đặt ($mrad/s$).
* **DISTANCE:** Khoảng cách tới vật thể gần nhất ($mm$).
* **CHECKSUM:** Thuật toán XOR tổng kiểm soát toàn bộ byte dữ liệu chống sai số trên đường truyền động cơ nhiễu cao.

---

## VII. KẾ HOẠCH HÀNH ĐỘNG TUẦN TIẾP THEO (NEXT STEPS)

1. **Tuần 1:** Nối dây UART (Chân Pin 8 TXD, Pin 10 RXD trên Header 40-pin Jetson) sang cổng Serial STM32/Arduino với tốc độ Baudrate $115200\text{ bps}$.
2. **Tuần 2:** Lập trình giải mã Frame nhị phân trên STM32, viết thuật toán điều khiển PID vận tốc động cơ đóng kín qua Encoder bánh xe.
3. **Tuần 3:** Gắn cụm Jetson Nano + Pin 3S + Camera lên khung gầm xe thật, tiến hành thử nghiệm chạy sa bàn thực tế và tinh chỉnh hệ số lái $K_p$.
