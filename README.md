# TaskHub

TaskHub là REST API quản lý công việc (Task Management API), được xây dựng bằng FastAPI và PostgreSQL.

## 1. Công nghệ sử dụng

- Python
- FastAPI
- SQLAlchemy (Async)
- PostgreSQL
- Alembic
- Pydantic
- Pytest
- Docker Compose

## 2. Cấu trúc dự án

```text
TaskHub/
├── alembic/       # Quản lý database migration
├── app/
│   ├── api/       # API endpoints
│   ├── core/      # Cấu hình và xử lý lỗi
│   ├── db/        # Kết nối database
│   ├── models/    # Database models
│   ├── repositories/ # Truy vấn database
│   ├── schemas/   # Request và response schemas
│   └── services/  # Xử lý nghiệp vụ
├── tests/         # Các bài kiểm thử
├── .env.example   # Mẫu cấu hình môi trường
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

## 3. Cài đặt và chạy dự án

### Bước 1: Tạo môi trường ảo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt thư viện

```powershell
python -m pip install -r requirements-dev.txt
```

### Bước 3: Cấu hình môi trường

Tạo file `.env` từ file mẫu:

```powershell
Copy-Item .env.example .env
```

Cập nhật thông tin database trong `.env`:

```env
POSTGRES_USER=taskhub
POSTGRES_PASSWORD=your-password
POSTGRES_DB=taskhub
POSTGRES_TEST_DB=taskhub_test
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
DB_ECHO=false
```

Lưu ý: `POSTGRES_DB` và `POSTGRES_TEST_DB` phải là hai database khác nhau.

### Bước 4: Khởi động PostgreSQL

Đảm bảo Docker Desktop đang chạy, sau đó thực hiện:

```powershell
docker compose up -d db
```

Kiểm tra trạng thái container:

```powershell
docker compose ps
```

### Bước 5: Chạy database migration

```powershell
python -m alembic upgrade head
```

### Bước 6: Khởi động API

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Sau khi khởi động, truy cập:

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

## 4. Các chức năng API

| Method | Endpoint | Chức năng |
|---|---|---|
| POST | `/api/v1/tasks` | Tạo task |
| GET | `/api/v1/tasks` | Lấy danh sách task |
| GET | `/api/v1/tasks/{task_id}` | Lấy thông tin task |
| PATCH | `/api/v1/tasks/{task_id}` | Cập nhật task |
| DELETE | `/api/v1/tasks/{task_id}` | Xóa task |

Chi tiết request và response được mô tả trong Swagger UI.

## 5. Chạy kiểm thử

Chạy toàn bộ test:

```powershell
python -m pytest .\tests -v
```

Test sẽ tự tạo test database nếu database chưa tồn tại và chạy migration trước khi thực hiện kiểm thử.

Tài khoản PostgreSQL cần có quyền tạo database. Không sử dụng database phát triển để chạy test.

## 6. Kiểm tra chất lượng code

Kiểm tra lỗi:

```powershell
python -m ruff check .
```

Kiểm tra định dạng:

```powershell
python -m ruff format --check .
```

Tự động định dạng code:

```powershell
python -m ruff format .
```

## 7. Một số lệnh Alembic

Tạo migration mới:

```powershell
python -m alembic revision --autogenerate -m "migration message"
```

Áp dụng migration:

```powershell
python -m alembic upgrade head
```

Kiểm tra migration hiện tại:

```powershell
python -m alembic current
```
