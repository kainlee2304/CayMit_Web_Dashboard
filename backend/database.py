from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# SQLite cho local dev (không cần cài PostgreSQL)
# Đổi DATABASE_URL trong .env khi deploy production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caymit.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Prediction(Base):
    """Lưu kết quả phát hiện bệnh"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, nullable=True)         # Đường dẫn ảnh đã lưu
    predicted_class = Column(String, nullable=False)   # Tên bệnh
    confidence = Column(Float, nullable=False)         # Độ tin cậy (0-1)
    model_used = Column(String, default="best_11")     # Model nào inference
    all_scores = Column(Text, nullable=True)           # JSON scores tất cả class
    device_id = Column(String, nullable=True)          # ID của Jetson Nano
    batch_id = Column(Integer, ForeignKey("trace_batches.id"), nullable=True, index=True)
    trace_code = Column(String(32), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SensorData(Base):
    """Lưu dữ liệu cảm biến nhiệt độ, độ ẩm"""
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)        # Nhiệt độ (°C)
    humidity = Column(Float, nullable=False)           # Độ ẩm (%)
    device_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceState(Base):
    """Lưu trạng thái thiết bị (đèn, relay...)"""
    __tablename__ = "device_states"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False)
    light_on = Column(Boolean, default=False)          # Trạng thái đèn
    is_online = Column(Boolean, default=False)         # Thiết bị online?
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TraceBatch(Base):
    """Lô nông sản được định danh bằng QR để truy xuất nguồn gốc."""
    __tablename__ = "trace_batches"

    id = Column(Integer, primary_key=True, index=True)
    trace_code = Column(String(32), unique=True, nullable=False, index=True)
    product_name = Column(String(120), nullable=False)
    variety = Column(String(120), nullable=True)
    farm_name = Column(String(180), nullable=False)
    origin = Column(String(240), nullable=False)
    harvest_date = Column(String(20), nullable=True)
    plot_code = Column(String(80), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)
    status = Column(String(40), nullable=False, default="created")
    owner_user_id = Column(Integer, ForeignKey("trace_users.id"), nullable=True, index=True)
    owner_organization = Column(String(180), nullable=True, index=True)
    locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TraceUser(Base):
    """Tài khoản vận hành chuỗi truy xuất với vai trò nghiệp vụ rõ ràng."""
    __tablename__ = "trace_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(240), nullable=False)
    display_name = Column(String(160), nullable=False)
    organization = Column(String(180), nullable=False)
    role = Column(String(30), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("trace_users.id"), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TraceEvent(Base):
    """Khối bất biến trong sổ cái: mỗi hash liên kết với khối đứng trước."""
    __tablename__ = "trace_events"
    __table_args__ = (UniqueConstraint("batch_id", "block_index", name="uq_trace_event_block"),)

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("trace_batches.id"), nullable=False, index=True)
    block_index = Column(Integer, nullable=False)
    stage = Column(String(40), nullable=False)
    title = Column(String(180), nullable=False)
    actor = Column(String(180), nullable=False)
    location = Column(String(240), nullable=True)
    details = Column(Text, nullable=True)
    event_time = Column(DateTime, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TraceBatchAccess(Base):
    """Đơn vị được chủ lô cấp quyền tham gia cập nhật hành trình."""
    __tablename__ = "trace_batch_access"
    __table_args__ = (UniqueConstraint("batch_id", "user_id", name="uq_trace_batch_user_access"),)

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("trace_batches.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("trace_users.id"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("trace_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    """Nhật ký bảo mật append-only cho các thao tác nhạy cảm."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("trace_users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False, index=True)
    resource_id = Column(String(120), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


def get_db():
    """Dependency injection - lấy DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Tạo tất cả bảng nếu chưa có"""
    Base.metadata.create_all(bind=engine)
    # create_all không thêm cột vào SQLite đã tồn tại. Migration nhỏ này giữ
    # dữ liệu MVP cũ và giúp ứng dụng nâng cấp tại chỗ.
    if DATABASE_URL.startswith("sqlite"):
        columns = {column["name"] for column in inspect(engine).get_columns("trace_batches")}
        additions = {
            "owner_user_id": "INTEGER",
            "owner_organization": "VARCHAR(180)",
            "locked": "BOOLEAN NOT NULL DEFAULT 0",
            "plot_code": "VARCHAR(80)",
            "quantity": "FLOAT",
            "unit": "VARCHAR(30)",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE trace_batches ADD COLUMN {name} {definition}"))
        user_columns = {column["name"] for column in inspect(engine).get_columns("trace_users")}
        user_additions = {
            "approved": "BOOLEAN NOT NULL DEFAULT 0",
            "approved_by": "INTEGER",
            "last_login_at": "DATETIME",
        }
        with engine.begin() as connection:
            for name, definition in user_additions.items():
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE trace_users ADD COLUMN {name} {definition}"))
            # Tài khoản tồn tại trước nâng cấp được giữ hoạt động.
            connection.execute(text("UPDATE trace_users SET approved = 1 WHERE active = 1 AND approved = 0 AND created_at IS NOT NULL"))
        prediction_columns = {column["name"] for column in inspect(engine).get_columns("predictions")}
        with engine.begin() as connection:
            if "batch_id" not in prediction_columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN batch_id INTEGER"))
            if "trace_code" not in prediction_columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN trace_code VARCHAR(32)"))
