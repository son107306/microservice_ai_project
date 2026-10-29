# Hệ thống Sinh Câu hỏi Trắc nghiệm từ Tài liệu theo Kiến trúc Microservices (Project 1)

## Thông tin học phần
- **Sinh viên thực hiện**: Nguyễn Văn Sơn – MSSV: `202416339` – Lớp: `IT1-03-K69` (Hệ Cử nhân)
- **Giảng viên hướng dẫn**: Thầy Nguyễn Mạnh Tuấn (Bộ môn Project 1 – Trường CNTT&TT, Đại học Bách khoa Hà Nội)
- **Đề tài**: Thiết kế và xây dựng hệ thống sinh câu hỏi trắc nghiệm từ tài liệu theo kiến trúc Microservices, hỗ trợ xử lý tác vụ AI bất đồng bộ và đánh giá khả năng chịu tải.
- **Kho mã nguồn**: `https://github.com/son107306/microservice_ai_project`

## Tiến độ hiện tại: Tuần 3 (24/10/2026 – 30/10/2026) – Kiến trúc Microservices, Đa định dạng & Docker Compose

Trong Tuần 3, hệ thống đã hoàn thành việc chuyển đổi từ phiên bản cơ sở đơn lẻ sang kiến trúc phân tán đa dịch vụ (Microservices), container hóa qua Docker Compose và mở rộng năng lực xử lý tài liệu đa định dạng theo góp ý chuyên môn của Giảng viên hướng dẫn:

1. **Phân tách ranh giới dịch vụ (Skeleton Services)**:
   - **`job_service`** (Cổng `8002`): Đóng vai trò API Gateway tiếp nhận yêu cầu, cấp phát mã định danh `job_id`, trả trạng thái ban đầu `queued` (HTTP 202) và cung cấp endpoint tra cứu trạng thái tác vụ qua HTTP Polling.
   - **`core_service`** (Cổng `8001`): Quản lý dữ liệu tài liệu, lưu trữ và cung cấp API truy xuất kết quả bộ câu hỏi trắc nghiệm (Quiz).
2. **Container hóa toàn diện bằng Docker Compose**:
   - Đóng gói từng service qua `Dockerfile` chuyên biệt.
   - Khởi chạy đồng bộ qua `docker-compose.yml`, kiểm thử thực tế đạt trạng thái `Up / Healthy` (Ports `8001` và `8002`).
3. **Mở rộng Pipeline tiền xử lý đa định dạng & xử lý các trường hợp đặc biệt**:
   - **Tài liệu Word (`.docx`)**: Trích xuất toàn diện đoạn văn bản (`paragraphs`) và cấu trúc bảng biểu (`tables`) bằng `python-docx`.
   - **Bài giảng PowerPoint (`.pptx`)**: Trích xuất tiêu đề slide, các điểm danh sách (`shapes`) và phần ghi chú bài giảng của giảng viên (`speaker notes`) bằng `python-pptx`.
   - **Trường hợp PDF in 4 slide/trang (Handout 2x2)**: Thuật toán phân vùng tọa độ Bounding Box chia trang A4 thành 4 góc phần tư độc lập (Trên-Trái $\rightarrow$ Trên-Phải $\rightarrow$ Dưới-Trái $\rightarrow$ Dưới-Phải) bằng `PyMuPDF 2.0`, loại bỏ hoàn toàn hiện tượng dính chữ ngang giữa các slide.
   - **Ký tự đặc biệt & Công thức toán học**: Chuẩn hóa Unicode tương thích **NFKC**, bảo toàn ký hiệu Hy Lạp ($\alpha, \beta, \Sigma, \Delta$), dấu so sánh và chỉ số toán học.
   - **Xử lý hình vẽ, sơ đồ**: Chiến lược *Text & Caption First* trích xuất chú thích hình vẽ để tối ưu chi phí và độ trễ.
4. **Tích hợp Tầng Adapter đa nhà cung cấp LLM (`MultiLLMAdapter`)**:
   - Hỗ trợ chuyển đổi linh hoạt qua biến môi trường giữa **Google Gemini** (`gemini-3.5-flash-lite`, `gemini-3.8-flash`), **DeepSeek** (`deepseek-chat` / V3 giá rẻ $0.28/1M token output), **OpenAI** (`gpt-4o-mini`) và chế độ **Mock LLM** phục vụ kiểm thử tải.

## Cấu trúc thư mục dự án

```text
microservice-project/
├── .venv/                         # Môi trường ảo Python 3.13
├── .env                           # Biến môi trường (API Key, cấu hình cổng)
├── .gitignore                     # Bỏ qua .venv, .env, __pycache__
├── docker-compose.yml             # Cấu hình khởi chạy các container đa dịch vụ
├── requirements.txt               # Danh mục thư viện phụ thuộc
├── README.md                      # Tài liệu hướng dẫn và báo cáo tiến độ
├── baseline_app.py                # Mã nguồn phiên bản cơ sở đồng bộ (Tuần 2)
├── core_service/                  # Dịch vụ quản lý tài liệu và bộ câu hỏi Quiz
│   ├── main.py                    # FastAPI server Core Service (Port 8001)
│   └── Dockerfile                 # Container hóa Core Service
├── job_service/                   # Dịch vụ tiếp nhận yêu cầu và điều phối Job
│   ├── main.py                    # FastAPI server Job Service (Port 8002)
│   └── Dockerfile                 # Container hóa Job Service
├── worker/                        # Pipeline tiền xử lý và Adapter AI
│   ├── preprocessor.py            # Trích xuất PDF (4-up slide), DOCX, PPTX, Unicode NFKC
│   └── llm_adapter.py             # Multi-LLM Adapter (Gemini, DeepSeek, OpenAI, Mock)
└── shared/                        # Chia sẻ dữ liệu và lược đồ cấu trúc
    └── schemas.py                 # Pydantic Schemas (QuizQuestion, QuizPayload, JobCreate)
```

## Hướng dẫn cài đặt và chạy thử nghiệm

### Cách 1: Khởi chạy nhanh bằng Docker Compose (Khuyên dùng)
Yêu cầu: Đã bật ứng dụng Docker Desktop.

```powershell
# 1. Khởi chạy toàn bộ hệ thống microservices
docker compose up -d

# 2. Kiểm tra trạng thái hoạt động của các container
docker compose ps
```

Khi chạy thành công, mở trình duyệt để truy cập tài liệu API tự động (Swagger UI):
- **Core Service API**: `http://localhost:8001/docs`
- **Job Service API**: `http://localhost:8002/docs`

### Cách 2: Chạy trực tiếp trên máy bằng môi trường ảo Python 3.13

```powershell
# 1. Kích hoạt môi trường ảo
.\.venv\Scripts\activate

# 2. Cài đặt các thư viện phụ thuộc
python -m pip install -r requirements.txt

# 3. Khởi chạy Core Service (Terminal 1)
python -m uvicorn core_service.main:app --reload --port 8001

# 4. Khởi chạy Job Service (Terminal 2)
python -m uvicorn job_service.main:app --reload --port 8002
```

## Đặc tả API cốt lõi của hệ thống (RESTful)

### 1. Job Service (Cổng tiếp nhận & Polling trạng thái)
- `POST /api/v1/jobs`: Tiếp nhận yêu cầu tạo Quiz (chứa `document_id`, `question_count`).
  - Phản hồi: `HTTP 202 Accepted` kèm `job_id`, trạng thái `"status": "queued"`.
- `GET /api/v1/jobs/{job_id}`: Tra cứu trạng thái xử lý của job (`queued` $\rightarrow$ `processing` $\rightarrow$ `completed` / `failed`).
- `GET /health`: Kiểm tra sức khỏe của dịch vụ tiếp nhận.

### 2. Core Service (Quản lý dữ liệu Quiz & Tài liệu)
- `GET /api/v1/quizzes/{quiz_id}`: Lấy nội dung chi tiết của bộ câu hỏi trắc nghiệm đã sinh.
- `GET /health`: Kiểm tra sức khỏe của dịch vụ Core.

## Kết quả đo lường mốc tham chiếu Baseline (Kế thừa từ thực nghiệm Tuần 2)

Thực nghiệm đo thời gian phản hồi đồng bộ trực tiếp trên tài liệu bài giảng chuyên ngành (*Cơ học – Cân bằng của vật rắn*, sinh 5 câu hỏi trắc nghiệm tiếng Việt):

| Chỉ số đo lường (Metrics) | Giá trị thực nghiệm | Tỷ trọng | Nhận xét kỹ thuật |
| :--- | :---: | :---: | :--- |
| **`extraction_time_ms`** (Trích xuất văn bản) | `66.54 ms` (~0.067s) | `0.06%` | Tốc độ trích xuất bằng thư viện C-binding cực nhanh, không gây nghẽn cổ chai. |
| **`llm_latency_ms`** (Chờ LLM sinh cấu trúc JSON) | `105049.54 ms` (~105.05s) | `99.94%` | Chiếm gần như toàn bộ độ trễ hệ thống do AI cần đọc hiểu và sinh dữ liệu cấu trúc. |
| **`total_time_ms`** (Tổng thời gian HTTP đồng bộ) | `105116.23 ms` (~105.12s) | `100.00%` | Vượt xa ngưỡng timeout 60 giây của các Gateway; khẳng định tính bắt buộc của kiến trúc Microservices và hàng đợi bất đồng bộ. |