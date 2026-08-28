# CayMit Operations Platform

Nền tảng giám sát bệnh cây mít và truy xuất nguồn gốc theo vai trò. Frontend dùng Next.js static export; backend FastAPI phục vụ API, frontend, AI inference và sổ cái SHA-256.

## Chạy local

```bash
python -m pip install -r backend/requirements.txt
npm ci
npm run build
cd backend
python main.py
```

Mở `http://localhost:8000/register` để tạo quản trị viên đầu tiên. Các tài khoản đăng ký sau đó phải được admin phê duyệt tại `/admin`.

## Production

1. Sao chép `.env.example` thành `.env`.
2. Tạo secret ngẫu nhiên tối thiểu 32 byte cho `TRACEABILITY_TOKEN_SECRET`.
3. Đặt domain thật trong `CORS_ORIGINS`, `TRUSTED_HOSTS` và `PUBLIC_TRACE_URL`.
4. Đặt `POSTGRES_PASSWORD` mạnh và không commit `.env`.
5. Chạy sau reverse proxy TLS:

```bash
docker compose up -d --build
```

Sao lưu cả volume `postgres_data` và `uploads`. Health check tại `/health`; OpenAPI docs tự tắt khi `ENVIRONMENT=production`.

## Mô hình bảo mật

- Tài khoản đầu tiên là admin; đăng ký công khai luôn ở trạng thái chờ duyệt.
- API dự đoán, cảm biến, thiết bị và thống kê yêu cầu Bearer token.
- Lô chỉ hiển thị cho chủ sở hữu, admin hoặc đối tác được cấp quyền.
- Công đoạn bị giới hạn theo role và workflow; lô khóa không nhận thêm dữ liệu.
- Hành động nhạy cảm được lưu trong `audit_logs` cùng user, IP và thời gian.
- Sổ cái là chuỗi hash SHA-256 có khả năng phát hiện sửa đổi, không phải blockchain công khai.

## Kiểm tra

```bash
npm run lint
npm run build
cd backend && python -m pytest tests -q
```

## Việc cần làm theo hạ tầng triển khai

- TLS, WAF/rate limiting và quản lý secrets tại cloud provider.
- Backup tự động, restore drill, monitoring và cảnh báo.
- Object storage cho ảnh/chứng từ thay vì filesystem nếu chạy nhiều replica.
- Alembic migrations chính thức trước khi thay schema trên PostgreSQL production.
- Chữ ký số hoặc blockchain anchoring nếu cần chống quản trị viên database viết lại chuỗi hash.
