# HỆ THỐNG SINH CÂU HỎI TRẮC NGHIỆM TỪ TÀI LIỆU THEO KIẾN TRÚC MICROSERVICES

## 1. Thông tin học phần

- **Sinh viên thực hiện:** Nguyễn Văn Sơn
- **MSSV:** `202416339`
- **Lớp:** `IT1-03-K69` (Hệ Cử nhân)
- **Giảng viên hướng dẫn:** Thầy Nguyễn Mạnh Tuấn
- **Bộ môn:** Project 1 – Trường CNTT&TT, Đại học Bách khoa Hà Nội
- **Đề tài:** Thiết kế và xây dựng hệ thống sinh câu hỏi trắc nghiệm từ tài liệu theo kiến trúc Microservices, hỗ trợ xử lý tác vụ AI bất đồng bộ và đánh giá khả năng chịu tải.
- **GitHub:** https://github.com/son107306/microservice_ai_project

---

## 2. Tổng quan dự án

Dự án hướng tới xây dựng một hệ thống tự động sinh câu hỏi trắc nghiệm từ tài liệu học tập bằng cách ứng dụng các mô hình ngôn ngữ lớn (LLM).

Hệ thống được phát triển theo kiến trúc Microservices, phân tách các thành phần tiếp nhận yêu cầu, quản lý dữ liệu và xử lý AI thành những dịch vụ độc lập.

Thay vì xử lý toàn bộ yêu cầu trong một HTTP request đồng bộ, hệ thống sử dụng RabbitMQ và Celery để đưa các tác vụ sinh câu hỏi vào hàng đợi, cho phép Worker xử lý bất đồng bộ.

Kết quả được lưu trữ trong PostgreSQL, hỗ trợ truy xuất trạng thái tác vụ và nội dung bộ câu hỏi đã sinh.

### Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.13 |
| API Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Database Migration | Alembic |
| Message Broker | RabbitMQ |
| Task Queue | Celery |
| AI Integration | Gemini, DeepSeek, OpenAI, Mock |
| Document Processing | PyMuPDF, python-docx, python-pptx |
| Containerization | Docker, Docker Compose |
| Validation | Pydantic |

---

## 3. Tiến độ phát triển dự án

### Tuần 2 (17/10/2026 – 23/10/2026): Xây dựng phiên bản Baseline

- Xây dựng ứng dụng FastAPI xử lý yêu cầu sinh câu hỏi từ tài liệu PDF.
- Tích hợp Google Gemini để sinh câu hỏi trắc nghiệm.
- Xây dựng cấu trúc dữ liệu đầu ra bằng Pydantic.
- Đo lường thời gian trích xuất văn bản, thời gian phản hồi LLM và tổng thời gian xử lý.
- Xác định vấn đề về độ trễ khi xử lý đồng bộ.

### Tuần 3 (24/10/2026 – 30/10/2026): Microservices và Docker Compose

- Phân tách hệ thống thành `job_service` và `core_service`.
- Xây dựng RESTful API để tiếp nhận yêu cầu và truy xuất kết quả.
- Container hóa các dịch vụ bằng Docker.
- Mở rộng khả năng tiền xử lý PDF, DOCX và PPTX.
- Xây dựng Multi-LLM Adapter hỗ trợ Gemini, DeepSeek, OpenAI và Mock.
- Xử lý tài liệu PDF dạng handout 4 slide/trang, Unicode và công thức toán học.

### Tuần 4 (31/10/2026 – 06/11/2026): Xử lý bất đồng bộ và quản lý dữ liệu tập trung

**Mục tiêu:** Chuyển đổi hệ thống từ kiến trúc Microservices mới dừng ở mức tiếp nhận và phản hồi trạng thái sang hệ thống có khả năng xử lý tác vụ AI bất đồng bộ thông qua Message Broker và Worker độc lập.

#### 3.1. Xây dựng cơ chế xử lý tác vụ bất đồng bộ

- Tích hợp RabbitMQ làm Message Broker để tiếp nhận và phân phối các tác vụ sinh câu hỏi.
- Tích hợp Celery để quản lý và thực thi các tác vụ nền.
- Xây dựng `worker` độc lập với các API Service.
- Job Service tiếp nhận yêu cầu, tạo `job_id` và gửi tác vụ vào hàng đợi.
- Worker tiếp nhận tác vụ, thực hiện pipeline xử lý tài liệu và sinh câu hỏi bằng LLM.
- Sau khi hoàn thành, kết quả được lưu trữ để Core Service cung cấp cho người dùng.

**Luồng xử lý tổng quát:**

```text
                  CLIENT
                     |
                     v
              +--------------+
              |  Job Service |
              |   Port 8002  |
              +--------------+
                     |
                     | Create Job
                     v
              +--------------+
              |   RabbitMQ   |
              | Message Queue|
              +--------------+
                     |
                     | Consume Task
                     v
              +--------------+
              | Celery Worker|
              +--------------+
                     |
          +----------+----------+
          |          |          |
          v          v          v
      Extract      LLM       Validate
      Document   Generation   Quiz Data
          |          |          |
          +----------+----------+
                     |
                     v
              +--------------+
              |  PostgreSQL  |
              | Persist Data |
              +--------------+
                     |
                     v
              +--------------+
              | Core Service |
              |   Port 8001  |
              +--------------+
                     |
                     v
                 CLIENT
```

#### 3.2. Tích hợp PostgreSQL và SQLAlchemy ORM

Xây dựng tầng quản lý dữ liệu tập trung bằng PostgreSQL và SQLAlchemy.

Thiết kế các thực thể dữ liệu chính:

| Model | Chức năng |
|---|---|
| `Document` | Lưu thông tin tài liệu được tải lên |
| `Job` | Quản lý trạng thái và thông tin tác vụ sinh Quiz |
| `Quiz` | Lưu thông tin bộ câu hỏi được sinh ra |
| `Question` | Lưu từng câu hỏi, các phương án và đáp án đúng |

Các quan hệ dữ liệu:

- Một `Document` có thể được sử dụng trong nhiều `Job`.
- Một `Document` có thể gắn với nhiều `Quiz`.
- Một `Job` có thể liên kết với một `Quiz` sau khi hoàn thành.
- Một `Quiz` chứa nhiều `Question`.
- Mỗi `Quiz` có mã định danh riêng và quan hệ liên kết với `Job`.

Sử dụng UUID làm khóa định danh cho các thực thể chính, hỗ trợ quản lý dữ liệu giữa các dịch vụ độc lập.

#### 3.3. Quản lý phiên bản cơ sở dữ liệu bằng Alembic

- Khởi tạo Alembic để quản lý schema PostgreSQL.
- Cấu hình `env.py` kết nối metadata từ SQLAlchemy Models.
- Tạo migration `create_initial_tables`.
- Xây dựng các bảng dữ liệu ban đầu gồm `documents`, `jobs`, `quizzes` và `questions`.
- Khai báo khóa chính, khóa ngoại, kiểu dữ liệu và các ràng buộc cần thiết.

Migration giúp quản lý thay đổi cấu trúc cơ sở dữ liệu có kiểm soát, thuận tiện cho việc nâng cấp và bảo trì hệ thống.

#### 3.4. Nâng cao độ tin cậy của Worker

Triển khai các cơ chế nhằm hạn chế lỗi khi xử lý tác vụ bất đồng bộ:

- **Retry:** Cho phép thử lại tối đa 3 lần khi tác vụ thất bại.
- **Exponential Backoff:** Tăng khoảng thời gian chờ giữa các lần thử lại.
- **Idempotency:** Hạn chế việc thực thi hoặc ghi nhận kết quả trùng lặp.
- **Safe ACK:** Kiểm soát việc xác nhận thông điệp sau quá trình xử lý.
- **Transaction Rollback:** Hoàn tác các thay đổi dữ liệu khi xảy ra lỗi.
- **Upload Cleanup:** Quản lý và dọn dẹp tệp tải lên sau khi xử lý theo vòng đời tác vụ.
- **Character Count:** Lưu thông tin số lượng ký tự trích xuất từ tài liệu.

#### 3.5. Hoàn thiện luồng API

- Job Service tiếp nhận yêu cầu tạo Quiz và trả về `job_id`.
- API tra cứu trạng thái Job hỗ trợ các trạng thái `queued`, `processing`, `completed` và `failed`.
- Khi xử lý thành công, Job trả về `quiz_id`.
- Core Service cung cấp API truy xuất nội dung bộ câu hỏi từ cơ sở dữ liệu.

---

## 4. Kiến trúc và cấu trúc thư mục dự án

```text
microservice-project/
│
├── .venv/
├── .env
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── README.md
│
├── alembic/
│   ├── versions/
│   │   └── create_initial_tables.py
│   ├── env.py
│   ├── README
│   └── script.py.mako
│
├── alembic.ini
│
├── core_service/
│   ├── __init__.py
│   ├── main.py
│   └── Dockerfile
│
├── job_service/
│   ├── __init__.py
│   ├── main.py
│   └── Dockerfile
│
├── shared/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   └── database_connection.py
│
├── worker/
│   ├── Dockerfile
│   └── tasks.py
│
├── test_files/
├── test_outputs/
│
├── baseline_app.py
├── preprocessor.py
└── llm_adapter.py
```

**Vai trò các thành phần:**

- `core_service/`: Quản lý tài liệu, Quiz và API truy xuất kết quả.
- `job_service/`: Tiếp nhận yêu cầu, tạo Job và cung cấp API theo dõi trạng thái.
- `worker/`: Thực thi các tác vụ nền bằng Celery.
- `shared/`: Chia sẻ cấu hình database và SQLAlchemy Models.
- `alembic/`: Quản lý lịch sử migration của cơ sở dữ liệu.
- `docker-compose.yml`: Điều phối các thành phần trong môi trường Docker.
- `baseline_app.py`: Lưu phiên bản Baseline đồng bộ từ Tuần 2.

---

## 5. Đặc tả API

### 5.1. Job Service (Port 8002)

| Method | Endpoint | Chức năng |
|---|---|---|
| POST | `/api/v1/jobs` | Tạo yêu cầu sinh Quiz |
| GET | `/api/v1/jobs/{job_id}` | Tra cứu trạng thái Job |
| GET | `/health` | Kiểm tra tình trạng dịch vụ |

Quy trình trạng thái:

```text
queued → processing → completed
                   ↘ failed
```

Khi hoàn thành, kết quả xử lý được liên kết với `quiz_id`.

### 5.2. Core Service (Port 8001)

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | `/api/v1/quizzes/{quiz_id}` | Truy xuất bộ câu hỏi |
| GET | `/health` | Kiểm tra tình trạng dịch vụ |

---

## 6. Hướng dẫn cài đặt và chạy dự án

### 6.1. Yêu cầu môi trường

- Python 3.13
- Docker Desktop
- Docker Compose
- Git

### 6.2. Cấu hình môi trường

Tạo file `.env` tại thư mục gốc và khai báo các biến môi trường cần thiết:

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.8-flash

DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/quiz_db

CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
```

Lưu ý: Các giá trị username, password, database và tên service cần đồng bộ với cấu hình thực tế trong `docker-compose.yml`. Không đưa API Key hoặc mật khẩu thật lên GitHub.

### 6.3. Khởi chạy bằng Docker Compose

```powershell
# Khởi chạy toàn bộ hệ thống
docker compose up -d --build

# Kiểm tra trạng thái các container
docker compose ps

# Theo dõi log của Worker
docker compose logs -f worker-service

# Theo dõi log toàn hệ thống
docker compose logs -f
```

### 6.4. Chạy trực tiếp bằng Python

```powershell
# Kích hoạt môi trường ảo
.\.venv\Scripts\activate

# Cài đặt thư viện
python -m pip install -r requirements.txt

# Chạy Core Service
python -m uvicorn core_service.main:app --reload --port 8001

# Chạy Job Service
python -m uvicorn job_service.main:app --reload --port 8002
```

RabbitMQ và PostgreSQL cần được khởi chạy và cấu hình kết nối trước khi kiểm thử toàn bộ pipeline bất đồng bộ.

### 6.5. Quản lý Database bằng Alembic

```powershell
# Kiểm tra phiên bản migration hiện tại
alembic current

# Xem lịch sử migration
alembic history

# Áp dụng migration mới nhất
alembic upgrade head
```

Các lệnh migration cần được chạy trong môi trường đã cài đặt dependencies và cấu hình `DATABASE_URL` phù hợp.

---

## 7. Kết quả thực nghiệm Baseline – Tuần 2

Dữ liệu tham chiếu từ thực nghiệm sinh 5 câu hỏi trắc nghiệm tiếng Việt trên tài liệu bài giảng *Cơ học – Cân bằng của vật rắn*.

| Chỉ số | Giá trị |
|---|---:|
| Extraction Time | 66.54 ms |
| LLM Latency | 105049.54 ms |
| Total Time | 105116.23 ms |

Nhận xét:

- Thời gian trích xuất văn bản chiếm tỷ trọng rất nhỏ.
- Thời gian phản hồi LLM chiếm khoảng 99.94% tổng thời gian.
- Độ trễ xử lý đồng bộ vượt quá 100 giây, gây nguy cơ timeout khi triển khai qua các API Gateway.

Kết quả này là cơ sở kỹ thuật để chuyển sang kiến trúc xử lý bất đồng bộ sử dụng RabbitMQ và Celery ở Tuần 4.

---

## 8. Định hướng phát triển tiếp theo

Các công việc tiếp theo tập trung vào:

1. Hoàn thiện và kiểm thử migration trên PostgreSQL thực tế.
2. Kiểm thử tích hợp toàn bộ luồng Job Service → RabbitMQ → Celery Worker → PostgreSQL → Core Service.
3. Kiểm thử các trường hợp lỗi LLM, mất kết nối RabbitMQ và lỗi Database.
4. Kiểm thử tính đúng đắn của Retry, Idempotency và cơ chế ACK.
5. Bổ sung giới hạn dung lượng file tải lên và cơ chế chống gửi yêu cầu trùng lặp đồng thời.
6. Đo lường thời gian xử lý, throughput và khả năng chịu tải khi có nhiều Job đồng thời.
7. So sánh hiệu năng giữa Baseline đồng bộ và kiến trúc Microservices bất đồng bộ.

---

## 9. Tài liệu tham khảo

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/
- RabbitMQ: https://www.rabbitmq.com/docs
- Celery: https://docs.celeryq.dev/
- Docker Compose: https://docs.docker.com/compose/
- Google Gemini API: https://ai.google.dev/gemini-api/docs

---

**Project 1 – Hệ thống sinh câu hỏi trắc nghiệm từ tài liệu theo kiến trúc Microservices**

*Nguyễn Văn Sơn – IT1-03-K69 – Trường Đại học Bách khoa Hà Nội*