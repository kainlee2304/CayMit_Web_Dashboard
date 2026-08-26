"""QR traceability backed by an append-only, hash-linked internal ledger."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import secrets
import base64
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import qrcode
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import TraceBatch, TraceEvent, TraceUser, get_db

router = APIRouter(prefix="/api/traceability", tags=["Traceability"])
ZERO_HASH = "0" * 64
STAGES = {
    "created", "cultivation", "harvest", "processing", "packing",
    "cold_storage", "logistics", "export", "market",
}
ROLES = {"admin", "producer", "processor", "logistics"}
ROLE_STAGES = {
    "admin": STAGES - {"created"},
    "producer": {"cultivation", "harvest"},
    "processor": {"processing", "packing", "cold_storage"},
    "logistics": {"logistics", "export", "market"},
}


class BatchCreate(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    variety: Optional[str] = Field(default=None, max_length=120)
    farm_name: str = Field(min_length=2, max_length=180)
    origin: str = Field(min_length=2, max_length=240)
    harvest_date: Optional[str] = Field(default=None, max_length=20)


class EventCreate(BaseModel):
    stage: str
    title: str = Field(min_length=2, max_length=180)
    location: Optional[str] = Field(default=None, max_length=240)
    details: Optional[str] = Field(default=None, max_length=2000)
    event_time: Optional[datetime] = None


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserCreate(LoginInput):
    display_name: str = Field(min_length=2, max_length=160)
    organization: str = Field(min_length=2, max_length=180)
    role: str


class BootstrapAdmin(UserCreate):
    role: str = "admin"


def _password_hash(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_text, digest_text = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_secret() -> bytes:
    return os.getenv("TRACEABILITY_TOKEN_SECRET", "local-development-change-me").encode("utf-8")


def _issue_token(user: TraceUser) -> str:
    payload = {"sub": user.id, "role": user.role, "exp": int(time.time()) + 8 * 3600}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(hmac.new(_token_secret(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{body}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(_token_secret(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn")


def _user_dict(user: TraceUser) -> dict:
    return {"id": user.id, "username": user.username, "display_name": user.display_name,
            "organization": user.organization, "role": user.role, "active": user.active}


def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> TraceUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện thao tác này")
    payload = _decode_token(authorization.split(" ", 1)[1].strip())
    user = db.query(TraceUser).filter(TraceUser.id == payload["sub"], TraceUser.active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản không còn hoạt động")
    return user


def require_roles(*roles: str):
    def check(user: TraceUser = Depends(get_current_user)) -> TraceUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Vai trò của bạn không có quyền thực hiện thao tác này")
        return user
    return check


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def calculate_block_hash(*, trace_code: str, block_index: int, stage: str,
                         title: str, actor: str, location: Optional[str],
                         details: Optional[str], event_time: datetime,
                         previous_hash: str) -> str:
    payload = {
        "actor": actor,
        "block_index": block_index,
        "details": details or "",
        "event_time": _utc_iso(event_time),
        "location": location or "",
        "previous_hash": previous_hash,
        "stage": stage,
        "title": title,
        "trace_code": trace_code,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_dict(event: TraceEvent) -> dict:
    return {
        "id": event.id,
        "block_index": event.block_index,
        "stage": event.stage,
        "title": event.title,
        "actor": event.actor,
        "location": event.location,
        "details": event.details,
        "event_time": _utc_iso(event.event_time),
        "previous_hash": event.previous_hash,
        "block_hash": event.block_hash,
    }


def _verify(batch: TraceBatch, events: list[TraceEvent]) -> tuple[bool, Optional[int]]:
    previous = ZERO_HASH
    for expected_index, event in enumerate(events):
        expected = calculate_block_hash(
            trace_code=batch.trace_code, block_index=expected_index, stage=event.stage,
            title=event.title, actor=event.actor, location=event.location,
            details=event.details, event_time=event.event_time, previous_hash=previous,
        )
        if event.block_index != expected_index or event.previous_hash != previous or event.block_hash != expected:
            return False, expected_index
        previous = event.block_hash
    return bool(events), None if events else 0


def _trace_url(request: Request, code: str) -> str:
    configured = os.getenv("PUBLIC_TRACE_URL", "").strip().rstrip("/")
    base = configured or f"{str(request.base_url).rstrip('/')}/trace"
    return f"{base}/?code={quote(code)}"


def _batch_response(batch: TraceBatch, events: list[TraceEvent], request: Request) -> dict:
    verified, broken_at = _verify(batch, events)
    return {
        "trace_code": batch.trace_code, "product_name": batch.product_name,
        "variety": batch.variety, "farm_name": batch.farm_name, "origin": batch.origin,
        "harvest_date": batch.harvest_date, "status": batch.status,
        "created_at": _utc_iso(batch.created_at), "ledger_type": "permissioned_hash_chain",
        "verified": verified, "broken_at_block": broken_at,
        "latest_hash": events[-1].block_hash if events else None,
        "trace_url": _trace_url(request, batch.trace_code),
        "qr_url": str(request.url_for("traceability_qr", code=batch.trace_code)),
        "events": [_event_dict(event) for event in events],
    }


def _load_batch(code: str, db: Session) -> TraceBatch:
    batch = db.query(TraceBatch).filter(TraceBatch.trace_code == code.upper()).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Không tìm thấy lô nông sản")
    return batch


def _events(batch_id: int, db: Session) -> list[TraceEvent]:
    return db.query(TraceEvent).filter(TraceEvent.batch_id == batch_id).order_by(TraceEvent.block_index).all()


@router.get("/auth/status")
def auth_status(db: Session = Depends(get_db)):
    return {"initialized": db.query(TraceUser.id).first() is not None}


@router.post("/auth/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdmin, db: Session = Depends(get_db)):
    if db.query(TraceUser.id).first() is not None:
        raise HTTPException(status_code=409, detail="Hệ thống đã có tài khoản quản trị")
    user = TraceUser(username=payload.username.strip().lower(), password_hash=_password_hash(payload.password),
                     display_name=payload.display_name.strip(), organization=payload.organization.strip(),
                     role="admin", active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": _issue_token(user), "token_type": "bearer", "user": _user_dict(user)}


@router.post("/auth/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(TraceUser).filter(TraceUser.username == payload.username.strip().lower()).first()
    if not user or not user.active or not _password_matches(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
    return {"access_token": _issue_token(user), "token_type": "bearer", "user": _user_dict(user)}


@router.get("/auth/me")
def current_profile(user: TraceUser = Depends(get_current_user)):
    return _user_dict(user)


@router.get("/users")
def list_users(_: TraceUser = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return [_user_dict(user) for user in db.query(TraceUser).order_by(TraceUser.created_at).all()]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _: TraceUser = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    role = payload.role.strip().lower()
    if role not in ROLES or role == "admin":
        raise HTTPException(status_code=422, detail="Vai trò phải là producer, processor hoặc logistics")
    username = payload.username.strip().lower()
    if db.query(TraceUser.id).filter(TraceUser.username == username).first():
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại")
    user = TraceUser(username=username, password_hash=_password_hash(payload.password),
                     display_name=payload.display_name.strip(), organization=payload.organization.strip(),
                     role=role, active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_dict(user)


@router.post("/batches", status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchCreate, request: Request,
                 user: TraceUser = Depends(require_roles("admin", "producer")),
                 db: Session = Depends(get_db)):
    code = f"TM-{datetime.now(timezone.utc):%y%m%d}-{secrets.token_hex(3).upper()}"
    batch = TraceBatch(trace_code=code, product_name=payload.product_name.strip(),
                       variety=payload.variety.strip() if payload.variety else None,
                       farm_name=payload.farm_name.strip(), origin=payload.origin.strip(),
                       harvest_date=payload.harvest_date, status="created")
    db.add(batch)
    db.flush()
    now = datetime.utcnow().replace(microsecond=0)
    title = "Khởi tạo hồ sơ lô nông sản"
    actor = f"{user.display_name} · {user.organization}"
    details = f"{batch.product_name} được đăng ký tại {batch.farm_name}"
    block_hash = calculate_block_hash(trace_code=code, block_index=0, stage="created",
                                      title=title, actor=actor, location=batch.origin,
                                      details=details, event_time=now, previous_hash=ZERO_HASH)
    db.add(TraceEvent(batch_id=batch.id, block_index=0, stage="created", title=title,
                      actor=actor, location=batch.origin, details=details,
                      event_time=now, previous_hash=ZERO_HASH, block_hash=block_hash))
    db.commit()
    db.refresh(batch)
    return _batch_response(batch, _events(batch.id, db), request)


@router.get("/batches")
def list_batches(request: Request, limit: int = 30, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    batches = db.query(TraceBatch).order_by(TraceBatch.created_at.desc()).limit(limit).all()
    return [_batch_response(batch, _events(batch.id, db), request) for batch in batches]


@router.get("/{code}/qr", name="traceability_qr")
def traceability_qr(code: str, request: Request, db: Session = Depends(get_db)):
    batch = _load_batch(code, db)
    image = qrcode.make(_trace_url(request, batch.trace_code))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@router.post("/{code}/events", status_code=status.HTTP_201_CREATED)
def append_event(code: str, payload: EventCreate, request: Request,
                 user: TraceUser = Depends(get_current_user), db: Session = Depends(get_db)):
    stage = payload.stage.strip().lower()
    if stage not in STAGES or stage == "created":
        allowed = ", ".join(sorted(STAGES - {"created"}))
        raise HTTPException(status_code=422, detail=f"Công đoạn không hợp lệ. Chọn một trong: {allowed}")
    if stage not in ROLE_STAGES.get(user.role, set()):
        raise HTTPException(status_code=403, detail="Vai trò của bạn không được ghi công đoạn này")
    batch = _load_batch(code, db)
    events = _events(batch.id, db)
    verified, broken_at = _verify(batch, events)
    if not verified:
        raise HTTPException(status_code=409, detail=f"Chuỗi dữ liệu đã mất toàn vẹn tại khối {broken_at}")
    previous = events[-1].block_hash
    event_time = (payload.event_time or datetime.now(timezone.utc)).replace(microsecond=0, tzinfo=None)
    block_index = len(events)
    location = payload.location.strip() if payload.location else None
    details = payload.details.strip() if payload.details else None
    actor = f"{user.display_name} · {user.organization}"
    block_hash = calculate_block_hash(trace_code=batch.trace_code, block_index=block_index,
                                      stage=stage, title=payload.title.strip(), actor=actor,
                                      location=location, details=details, event_time=event_time,
                                      previous_hash=previous)
    db.add(TraceEvent(batch_id=batch.id, block_index=block_index, stage=stage,
                      title=payload.title.strip(), actor=actor, location=location,
                      details=details, event_time=event_time, previous_hash=previous,
                      block_hash=block_hash))
    batch.status = stage
    db.commit()
    return _batch_response(batch, _events(batch.id, db), request)


@router.get("/{code}")
def get_traceability(code: str, request: Request, db: Session = Depends(get_db)):
    batch = _load_batch(code, db)
    return _batch_response(batch, _events(batch.id, db), request)
