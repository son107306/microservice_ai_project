# Hệ thống Sinh Câu hỏi Trắc nghiệm từ PDF theo Kiến trúc Microservices (Project 1)

## Thông tin học phần
- **Sinh viên thực hiện**: Nguyễn Văn Sơn – MSSV: `202416339` – Lớp: `IT1-03-K69`
- **Giảng viên hướng dẫn**: Thầy Nguyễn Mạnh Tuấn (Bộ môn Project 1 – Trường CNTT&TT, ĐHBK Hà Nội)
- **Mục tiêu dự án**: Thiết kế và xây dựng hệ thống Web sinh câu hỏi trắc nghiệm (Quiz) từ tài liệu PDF có lớp văn bản theo kiến trúc Microservices, giải quyết bài toán tác vụ AI kéo dài và xử lý đồng thời (40 yêu cầu cùng lúc) thông qua hàng đợi RabbitMQ và Celery Worker.

## Tiến độ hiện tại: Tuần 2 – Phiên bản cơ sở đồng bộ (Synchronous Baseline)

Trong Tuần 2, hệ thống đã hoàn thành và chạy thực nghiệm **phiên bản cơ sở đồng bộ (`baseline_app.py`)** nhằm:
1. Kiểm chứng quy trình cốt lõi: **Nhận tệp PDF có lớp văn bản -> Trích xuất văn bản (`PyMuPDF 2.0`) -> Gọi LLM qua tầng Adapter (`gemini-3.8-flash` / `gemini-3.5-flash-lite` hoặc `Mock LLM`) -> Kiểm tra cấu trúc đầu ra JSON (`Pydantic v2`)**.
2. Thu thập số đo thời gian thực tế (`extraction_time_ms`, `llm_latency_ms`, `total_time_ms`) để làm mốc tham chiếu (Baseline) trước khi tách thành `Core Service`, `Job Service`, `RabbitMQ` và `Celery Worker` ở Tuần 3 – Tuần 4.

## Ngăn xếp công nghệ (Tech Stack)
- **Ngôn ngữ & Backend API**: Python 3.13 (`win32 64-bit`), FastAPI `0.159.1`, Uvicorn `0.54.0`, Pydantic `2.14.1`
- **Trích xuất văn bản PDF**: PyMuPDF `2.0` (MuPDF `1.28.5`)
- **Tích hợp AI (LLM Adapter)**: Google Gemini API (`gemini-3.8-flash`, `gemini-3.5-flash-lite` qua bộ SDK `google-genai 2.32.0`) và chế độ `Mock LLM` phục vụ kiểm thử độ trễ/lỗi
- **Hạ tầng bất đồng bộ (Tuần 3 – Tuần 8)**: RabbitMQ, Celery Worker, PostgreSQL, MinIO, Docker Compose, Locust

## Hướng dẫn cài đặt và chạy thử trên máy cá nhân (Python 3.13)

### Bước 1: Tạo và kích hoạt môi trường ảo Python 3.13
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\activate
```

### Bước 2: Cài đặt các thư viện cần thiết cho Tuần 2
```powershell
python -m pip install fastapi "uvicorn[standard]" python-multipart PyMuPDF google-genai pydantic python-dotenv
python -m pip freeze > requirements.txt
```

### Bước 3: Cấu hình API Key
Tạo file `.env` cùng cấp với `baseline_app.py` (lưu ý không đẩy file `.env` lên GitHub):
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

### Bước 4: Khởi chạy Server FastAPI và mở Swagger UI
```powershell
python -m uvicorn baseline_app:app --reload --port 8000
```
Mở trình duyệt truy cập địa chỉ Swagger UI sẵn có của FastAPI:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/health`

## Kết quả đo thời gian xử lý Baseline thực tế (Thực nghiệm ngày 22/10/2026)

Thử nghiệm thực tế được thực hiện trên tài liệu PDF bài giảng chuyên ngành (*Cơ học – Cân bằng của vật rắn*, sinh 5 câu hỏi trắc nghiệm tiếng Việt có trích dẫn mục lục và giải thích đáp án):

| Chỉ số đo (Metrics) | Giá trị thực nghiệm (Gemini API) | Tỷ trọng (%) | Nhận xét kỹ thuật |
| :--- | :---: | :---: | :--- |
| **`extraction_time_ms`** (Trích xuất PDF) | `66.54 ms` (~0.067 giây) | `0.06%` | `PyMuPDF 2.0` trích xuất lớp văn bản cực nhanh, không gây nghẽn cổ chai. |
| **`llm_latency_ms`** (Chờ LLM xử lý & sinh JSON) | `105049.54 ms` (~105.05 giây) | `99.94%` | Chiếm gần như toàn bộ thời gian phản hồi do mô hình phải đọc hiểu tài liệu và sinh cấu trúc JSON. |
| **`total_time_ms`** (Tổng thời gian HTTP đồng bộ) | `105116.23 ms` (~105.12 giây) | `100.00%` | Vượt ngưỡng HTTP timeout mặc định (60s) của các cổng API Gateway; giữ chặt kết nối gần 2 phút. |

**Kết luận từ thực nghiệm Baseline Tuần 2**: Thời gian phản hồi đồng bộ lên tới **105,12 giây/yêu cầu** chứng minh rằng nếu 40 người dùng cùng gửi yêu cầu tạo Quiz đồng thời, mô hình gọi trực tiếp trong HTTP request chắc chắn sẽ gây nghẽn kết nối và lỗi Timeout. Đây là cơ sở thực nghiệm trực tiếp để chuyển sang kiến trúc bất đồng bộ (`HTTP 202 Accepted` + `Job ID` + `RabbitMQ` + `Celery Worker`) từ Tuần 3 – Tuần 4.
