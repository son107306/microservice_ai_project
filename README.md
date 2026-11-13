# HỆ THỐNG SINH CÂU HỎI TRẮC NGHIỆM TỪ TÀI LIỆU THEO KIẾN TRÚC MICROSERVICES

> **Project 1 — Đại học Bách khoa Hà Nội**\
> **Trạng thái tài liệu:** Cập nhật kết quả triển khai và kiểm chứng đến hết Tuần 5 (07/11–13/11/2026). Đây là trạng thái kỹ thuật đã ghi nhận, **chưa phải tuyên bố hoàn tất toàn bộ đồ án**.

## 1. Thông tin học phần

- **Sinh viên thực hiện:** Nguyễn Văn Sơn
- **MSSV:** `202416339`
- **Lớp:** `IT1-03-K69` (Hệ Cử nhân)
- **Giảng viên hướng dẫn:** Thầy Nguyễn Mạnh Tuấn
- **Đơn vị:** Trường Công nghệ Thông tin và Truyền thông, Đại học Bách khoa Hà Nội
- **Đề tài:** Thiết kế và xây dựng hệ thống sinh câu hỏi trắc nghiệm từ tài liệu theo kiến trúc Microservices, hỗ trợ xử lý tác vụ AI bất đồng bộ và đánh giá khả năng chịu tải.
- **Kho mã nguồn:** https://github.com/son107306/microservice_ai_project

## 2. Tổng quan dự án

Dự án xây dựng hệ thống tạo câu hỏi trắc nghiệm từ tài liệu học tập. Các tác vụ gọi LLM có thể kéo dài nên hệ thống **không chờ xử lý AI ngay trong HTTP request tạo Job**. Job Service tiếp nhận yêu cầu, trả mã Job; RabbitMQ phân phối tác vụ cho Celery Worker; kết quả được lưu trong PostgreSQL và truy xuất thông qua Core Service.

**Phạm vi MVP theo đề cương:** tài liệu PDF có lớp văn bản, không bao gồm OCR cho PDF scan. Bộ tiền xử lý đã có hỗ trợ DOCX và PPTX ở mức triển khai đã ghi nhận, nhưng kiểm thử E2E Tuần 5 dưới đây được thực hiện bằng **một PDF 7 trang**. Chưa có bằng chứng kiểm thử tải đồng thời 10/20/40 Job hoặc triển khai giao diện React hoàn chỉnh trong Tuần 5.

### Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ/API | Python, FastAPI |
| Xử lý bất đồng bộ | Celery, RabbitMQ |
| Cơ sở dữ liệu | PostgreSQL, SQLAlchemy ORM |
| Quản lý schema | Alembic |
| Trích xuất tài liệu | PyMuPDF (`fitz`), `python-docx`, `python-pptx` |
| Chia văn bản | Chunking có overlap |
| Tích hợp AI | LLM Adapter: Gemini, DeepSeek, OpenAI, Mock |
| Xác thực dữ liệu | Pydantic |
| Triển khai dịch vụ | Docker, Docker Compose |
| Định hướng giao diện/đo tải | React, Locust (không tuyên bố đã hoàn tất trong Tuần 5) |

## 3. Tiến độ phát triển dự án

### Tuần 2 (16/10/2026 – 23/10/2026): Đề cương và Baseline

- Hoàn thiện phạm vi MVP, lựa chọn tech stack và kiến trúc phân tách Core Service, Job Service, Worker.
- Thiết kế luồng đồng bộ PDF → trích xuất văn bản → LLM Adapter → xác thực JSON Quiz.
- Xác định schema câu hỏi và các chỉ số `extraction_time_ms`, `llm_latency_ms`, `total_time_ms`.
- Báo cáo Tuần 2 ghi nhận **đang hoàn thiện chạy thực nghiệm Baseline**; không suy diễn rằng toàn bộ phép đo đã hoàn tất ngay tại thời điểm nộp báo cáo đó.

### Tuần 3 (24/10/2026 – 30/10/2026): Microservices và Docker Compose

- Phân tách Job Service (cổng `8002`) và Core Service (cổng `8001`); khởi chạy thử bằng Docker Compose.
- Thiết lập API tạo Job và truy vấn trạng thái qua HTTP Polling.
- Mở rộng tiền xử lý DOCX, PPTX; bổ sung xử lý PDF handout 4 slide/trang khi cấu hình thích hợp và chuẩn hóa Unicode.
- Xây dựng tầng Multi-LLM Adapter có các provider Gemini, DeepSeek, OpenAI, Mock.
- Ở mốc Tuần 3, việc lưu Job bền vững và ghép RabbitMQ/Celery **chưa hoàn thành**, được triển khai ở các tuần sau.

### Tuần 4 (31/10/2026 – 06/11/2026): Bất đồng bộ và dữ liệu tập trung

- Tích hợp RabbitMQ và Celery Worker; triển khai luồng tạo Job → hàng đợi → Worker → PostgreSQL → Core API.
- Tạo các model `Document`, `Job`, `Quiz`, `Question` với SQLAlchemy ORM; sử dụng Alembic quản lý schema.
- Bổ sung xử lý transaction rollback, ACK và các biện pháp hạn chế ghi trùng ở mức đã triển khai.
- **Cập nhật trạng thái mới nhất (Tuần 5):** Alembic `current` đã ghi nhận `98e0bbb3ce26 (head)`; bảng dữ liệu và các ràng buộc đã được kiểm tra. Không cần chạy lại migration chỉ để làm theo README.
- Báo cáo Tuần 4 từng nêu “retry tối đa 3 lần” cho Worker; cấu hình thực tế cập nhật ở Tuần 5 là **Celery `max_retries=0`**, còn retry HTTP Gemini được SDK đảm nhiệm (xem mục 8).

### Tuần 5 (07/11/2026 – 13/11/2026): PDF nhiều trang, Chunking và Gemini E2E

- Xử lý PDF nhiều trang bằng PyMuPDF, làm sạch Unicode, đánh dấu trang, kiểm tra nội dung rỗng.
- Hoàn thiện `chunking.py`: `chunk_size = 5000` ký tự và `overlap = 300` ký tự; PDF thử nghiệm được tách thành **2 chunks**.
- Chuẩn hóa `QuizQuestion`/`QuizPayload` để kiểm tra bốn đáp án A–D, `correct_answer` và `explanation`.
- Đồng bộ giao diện trả kết quả LLM Adapter dạng `dict` với Worker; build và chạy Worker thành công.
- Chạy E2E thành công với **Mock** và **Gemini thật (`gemini-3.5-flash`)**; lưu và truy xuất Quiz/Questions qua Core API.
- Quan sát Gemini gặp HTTP **504** ở một lần gọi, SDK retry rồi thành công; không nhầm thành lỗi HTTP 503 ở phép thử này.
- Đối chiếu 5 câu hỏi sinh ra với PDF gốc; xác minh lại Job và Quiz qua API sau khi container khởi động lại.

## 4. Kiến trúc và cấu trúc mã nguồn

### Luồng xử lý bất đồng bộ

```text
Người dùng / Client
    |  (upload tài liệu, tạo job, polling trạng thái)
    +--> Core Service :8001 -- lưu/truy xuất Document, Quiz
    |
    +--> Job Service :8002 -- tạo Job ID / trạng thái
                 |
                 v
              RabbitMQ
                 |
                 v
          Celery Worker
            | Extract + Clean PDF
            | Chunking (5000, overlap 300)
            | LLM Adapter (Mock/Gemini/...)
            | Validate + Aggregate Questions
                 |
                 v
             PostgreSQL
          documents / jobs / quizzes / questions
                 |
                 v
          Core Service :8001 -- GET Quiz
```

### Những thư mục/tệp trọng tâm đã được ghi nhận

```text
microservice-project/
├── core_service/         # API tài liệu và Quiz
├── job_service/          # Tạo Job, đọc trạng thái
├── worker/               # Celery task: worker.tasks.process_quiz_generation
├── shared/               # Models và kết nối PostgreSQL
├── alembic/              # Migration/schema
├── test_files/           # Tài liệu thử nghiệm nội bộ
├── preprocessor.py       # Trích xuất, chuẩn hóa tài liệu
├── chunking.py           # Chia đoạn có overlap
├── llm_adapter.py        # Gemini / DeepSeek / OpenAI / Mock
├── baseline_app.py       # Phiên bản Baseline (lịch sử)
├── docker-compose.yml
├── requirements.txt
└── README.md
```

Sơ đồ trên tập trung vào các tệp được nhắc trong báo cáo/bàn giao, **không thay thế việc kiểm tra cây thư mục Git thực tế**. Tệp `.env`, `.venv`, dữ liệu kiểm thử và bản dump database không được đưa vào GitHub.

## 5. API đã sử dụng

| Service | Method | Endpoint | Chức năng |
|---|---|---|---|
| Core (`8001`) | POST | `/api/v1/documents/upload` | Tải tài liệu |
| Core (`8001`) | GET | `/api/v1/documents/{document_id}` | Truy xuất thông tin Document |
| Core (`8001`) | GET | `/api/v1/quizzes/{quiz_id}` | Truy xuất bộ câu hỏi |
| Job (`8002`) | POST | `/api/v1/jobs` | Tạo Job và nhận mã Job |
| Job (`8002`) | GET | `/api/v1/jobs/{job_id}` | Theo dõi `queued` / `processing` / `completed` / `failed` |

Swagger: `http://localhost:8001/docs` và `http://localhost:8002/docs`.

> **Lưu ý:** Một số endpoint `/health` có thể trả HTTP 404 trong trạng thái bàn giao Tuần 5. Không dùng kết quả 404 tại `/health` làm bằng chứng duy nhất kết luận container hoặc service ngừng hoạt động; nên đối chiếu với `docker compose ps -a`, `/docs` và endpoint thực tế.

## 6. Hướng dẫn chạy và kiểm tra (Windows PowerShell)

### Yêu cầu

- Windows, PowerShell, Docker Desktop có Docker Compose.
- Python virtual environment (`.venv`) nếu cần thực thi lệnh Python ngoài container.
- Cấu hình môi trường hiện có phải hợp lệ. **Không công khai API key, mật khẩu, `.env` hoặc chuỗi kết nối thực.**

### Chạy hệ thống đang có

```powershell
# Từ thư mục dự án thực tế của bạn
cd C:\Users\ADMIN\microservice-project

# Khởi động lại các service theo cấu hình hiện tại, không ép build lại
docker compose up -d

# Xem các container, bao gồm container đã dừng
docker compose ps -a

# Nếu cần xem log Worker (không chỉnh sửa dữ liệu)
docker compose logs --tail=50 worker-service
```

Không dùng `docker compose down -v` để khắc phục lỗi thông thường vì có thể xóa volume chứa dữ liệu. Không tự đổi số worker, migration hoặc các giá trị trong `.env` để chạy lại phép thử cũ.

### Kiểm tra lại Job/Quiz đã có — không phát sinh tác vụ AI mới

Các mã dưới đây là **ID của dữ liệu kiểm thử đã được xác nhận**, không phải ID cố định cho mọi lần triển khai.

```powershell
$jobId = "59856f10-1cc1-4c72-a6ac-d6595085c7dc"
$quizId = "8060c874-9543-4755-aba8-7afb238fa994"

Invoke-RestMethod "http://localhost:8002/api/v1/jobs/$jobId" | Format-List

$quiz = Invoke-RestMethod "http://localhost:8001/api/v1/quizzes/$quizId"
$quiz | Select-Object quiz_id, job_id, question_count, `
    @{Name="actual_questions";Expression={@($_.questions).Count}} | Format-List

# Lưu JSON để xem UTF-8 trong VS Code (tùy chọn)
curl.exe -sS "http://localhost:8001/api/v1/quizzes/$quizId" -o gemini_quiz.json
code gemini_quiz.json
```

Nếu PowerShell hiển thị dấu tiếng Việt sai nhưng JSON mở trong VS Code đúng UTF-8, cần phân biệt **lỗi hiển thị terminal** với **lỗi dữ liệu API**.

### Database/Alembic

Phiên bản đã ghi nhận: `98e0bbb3ce26 (head)`. Chỉ kiểm tra trạng thái khi cần, **không tự ý `alembic upgrade head` hoặc chỉnh sửa schema** nếu không có migration mới được chủ động duyệt.

## 7. Kết quả Baseline — tham chiếu từ README trước Tuần 5

README cũ ghi nhận số liệu thử nghiệm Baseline với tài liệu *Cơ học – Cân bằng của vật rắn* như sau:

| Chỉ số | Giá trị ghi trong README cũ |
|---|---:|
| Extraction Time | 66,54 ms |
| LLM Latency | 105.049,54 ms |
| Total Time | 105.116,23 ms |

Các số liệu này được **giữ để bảo toàn lịch sử README**. Báo cáo Tuần 2 tại thời điểm nộp vẫn mô tả công đoạn đo Baseline là đang hoàn thiện; khi sử dụng số liệu trên cho báo cáo cuối kỳ nên đối chiếu lại log/minh chứng Baseline tương ứng. Không coi Baseline này là phép thử song song trực tiếp với dữ liệu Tuần 5 (khác tài liệu đầu vào).

## 8. Kết quả kiểm thử End-to-End — Tuần 5

**Tài liệu:** `Giải_đề_cuối_kì_Đại_số_2023_1.pdf` (PDF có lớp văn bản, 7 trang, 268.906 byte).\
**Trích xuất:** 9.397 ký tự; phân bố theo trang `[1464, 1198, 1449, 1510, 1586, 1535, 655]`.\
**Chunking:** `chunk_size=5000`, `overlap=300`, tổng cộng **2 chunks**.

| Chỉ số | Mock | Gemini |
|---|---:|---:|
| Provider | `mock` | `gemini` |
| Model | Giả lập | `gemini-3.5-flash` |
| Trạng thái Job | `completed` | `completed` |
| Số câu hỏi | 5 | 5 |
| Số chunks | 2 | 2 |
| Tổng LLM latency | 1.001 ms | 104.890 ms |
| Tổng thời gian | 1.175,32 ms | 105.430,81 ms |
| `error_message` cuối cùng | `null` | `null` |

**Mã kiểm thử (tham chiếu khi cần):**

| Provider | Job ID | Quiz ID |
|---|---|---|
| Mock | `e23f9cef-c72b-4cbf-82df-fa8f9498c00f` | `a693d295-3b46-4ec5-9848-a297dd92bbba` |
| Gemini | `59856f10-1cc1-4c72-a6ac-d6595085c7dc` | `8060c874-9543-4755-aba8-7afb238fa994` |

### Retry và cơ chế tin cậy đang dùng

- Celery task: `worker.tasks.process_quiz_generation` với `max_retries=0` (không retry toàn bộ task bằng Celery).
- Gemini SDK có `HttpRetryOptions`: `attempts=2` (tính cả lần thử đầu), `initial_delay=1.0`, `max_delay=4.0`, `exp_base=2.0`, `jitter=1.0`; retry các mã HTTP `[408, 429, 500, 502, 503, 504]` theo cấu hình SDK.
- Trong Job Gemini đã ghi nhận **HTTP 504**, SDK thử lại, sau đó nhận HTTP 200 và Job hoàn thành.
- Worker đang dùng `concurrency=20` (prefork), late ACK, reject worker lost, prefetch multiplier bằng 1 và logic rollback/giảm trùng lặp ở mức đã triển khai.
- **Chưa có persistence tiến độ từng chunk để resume độc lập** khi Worker bị gián đoạn. Chưa có bằng chứng kiểm thử đầy đủ các kịch bản Worker chết, mất RabbitMQ hoặc lỗi DB trong Tuần 5.

### Xác minh dữ liệu sau khi các container khởi động lại

- Job Service trả Job Gemini `status=completed`, `total_time_ms=105430.81`, `error_message=null` và đúng `quiz_id`.
- Core Service tiếp tục trả đúng `quiz_id`, `job_id`, `question_count=5` và danh sách có thực tế **5 câu hỏi**.
- Việc này xác nhận truy xuất lại dữ liệu đã lưu; **không chứng minh** tính năng resume khi một Job đang thực thi bị gián đoạn.
- Số liệu E2E này là của các lần chạy riêng lẻ, **không phải benchmark throughput/concurrency**.

## 9. Đánh giá nội dung Quiz Gemini so với PDF nguồn

Đã đối chiếu JSON Quiz Gemini gồm 5 câu với PDF Đại số 2023.1 và lời giải trong cùng PDF:

| Câu Gemini | Chủ đề | Đáp án trong JSON | Kết quả đối chiếu |
|---|---|---|---|
| 1 | Quy ước `Arg(z)` và `arg(z)` | A | Phù hợp quy ước trong PDF |
| 2 | Điều kiện hệ phương trình có nghiệm | B: `m=-2` | Đúng với phép khử Gauss |
| 3 | Hạng ma trận nhỏ nhất | C: `m=5` | Đúng với phép khử Gauss |
| 4 | Trị riêng của `p(A)=(A+2I)^4` | A: `1, 16, 4096` | Đúng với định lý phổ |
| 5 | Hai không gian sinh bằng nhau trong `P2[x]` | B: `m=5` | Đúng theo hệ vector dùng ở lời giải PDF |

**Kiểm tra cấu trúc:** 5/5 câu có nội dung, bốn lựa chọn, `correct_answer` thuộc A–D và `explanation` không rỗng; không có cặp câu hỏi trùng nguyên văn trong bộ 5 câu. Tiếng Việt của JSON được xác nhận hiển thị đúng khi tải file và mở trong VS Code.

**Hạn chế chất lượng:**

1. Câu Gemini 2 và 3 dẫn chiếu “hệ phương trình/ma trận trong tài liệu” nhưng không chép đủ dữ kiện, nên không tự giải được nếu tách khỏi PDF.
2. Explanation câu Gemini 5 cần lập luận chặt hơn về không gian sinh và tính độc lập tuyến tính.
3. PDF nguồn có khác biệt: đề Câu 7 ở trang 1 ghi `-3x^3` cho một phần tử thuộc `P2[x]`, trong khi phần lời giải dùng `-3x^2`; câu Gemini 5 theo phần lời giải. Phần lời giải Câu 8 còn có một dòng ghi trị riêng `2` thay vì `6`, dù phép tính và kết luận đúng là `-1, 0, 6`.

Kết luận **5/5 đáp án đúng trong bộ mẫu đã kiểm chứng**, không suy ra độ chính xác 100% trên các tài liệu hoặc Job khác.

## 10. Giới hạn và công việc chưa thực hiện

- **Chưa OCR:** PDF scan không có lớp văn bản chưa được hỗ trợ trong MVP.
- **Chưa có kiểm thử tải đồng thời** 10/20/40 Job và so sánh 1/2/4 worker; đây không phải kết quả đã hoàn thành trong Tuần 5.
- **Chưa chứng minh toàn diện lỗi hạ tầng**: dừng Worker giữa Job, mất RabbitMQ/DB và khôi phục từng chunk.
- **Chất lượng câu hỏi** cần được cải tiến để tự chứa dữ kiện gốc, hạn chế trùng lặp ngữ nghĩa và tăng tính chặt chẽ của lời giải.
- **Thời gian LLM** phụ thuộc nhà cung cấp, hạn mức và độ dài ngữ cảnh; một lần đo 105 giây không đủ để kết luận hiệu năng tổng quát.
- **React, MinIO, Locust** thuộc thiết kế/lộ trình nhưng README này không khẳng định đã triển khai đầy đủ hay kiểm thử E2E trong Tuần 5.

## 11. Định hướng sau Tuần 5

Chỉ chuyển sang các bước tiếp theo khi Tuần 5 được xác nhận hoàn tất. Theo đề cương, các bước sau dự kiến tập trung vào kiểm thử tải Mock bằng Locust, phân tích khả năng chịu tải, đánh giá cấu hình Worker, bổ sung kịch bản lỗi và đo metric. **Các mục này là định hướng, chưa phải kết quả đã triển khai.**

## 12. Tài liệu tham khảo

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/
- RabbitMQ: https://www.rabbitmq.com/docs
- Celery: https://docs.celeryq.dev/
- Docker Compose: https://docs.docker.com/compose/
- Google Gemini API: https://ai.google.dev/gemini-api/docs

---

*Project 1 — Nguyễn Văn Sơn — IT1-03-K69 — Đại học Bách khoa Hà Nội*\
*Cập nhật tài liệu đến 13/11/2026; chỉ phản ánh các hạng mục có bằng chứng trong báo cáo, bàn giao và kết quả kiểm tra đã cung cấp.*
