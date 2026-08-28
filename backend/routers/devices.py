"""
Router: Devices - Điều khiển đèn và trạng thái thiết bị
Jetson Nano poll lệnh từ endpoint này để biết cần bật/tắt đèn
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import DeviceState, get_db
from routers.traceability import get_current_user

router = APIRouter(prefix="/api/devices", tags=["Devices"], dependencies=[Depends(get_current_user)])

# Lưu lệnh pending trong memory (Jetson Nano sẽ poll)
_pending_commands: dict = {}  # device_id -> {"light": True/False}


class LightCommand(BaseModel):
    device_id: str
    light_on: bool


class DeviceStateOut(BaseModel):
    device_id: str
    light_on: bool
    is_online: bool
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/light")
def set_light(cmd: LightCommand, db: Session = Depends(get_db)):
    """Web/App gửi lệnh bật/tắt đèn"""
    # Lưu lệnh để Jetson Nano poll
    _pending_commands[cmd.device_id] = {"light_on": cmd.light_on}

    # Cập nhật DB
    state = db.query(DeviceState).filter(DeviceState.device_id == cmd.device_id).first()
    if not state:
        state = DeviceState(device_id=cmd.device_id, light_on=cmd.light_on)
        db.add(state)
    else:
        state.light_on = cmd.light_on
        state.updated_at = datetime.utcnow()
    db.commit()

    return {"message": f"Đã gửi lệnh {'bật' if cmd.light_on else 'tắt'} đèn", "device_id": cmd.device_id}


@router.get("/command/{device_id}")
def get_pending_command(device_id: str):
    """
    Jetson Nano poll endpoint này để lấy lệnh mới nhất
    Sau khi lấy xong thì lệnh bị xóa khỏi queue
    """
    cmd = _pending_commands.pop(device_id, None)
    if cmd:
        return {"has_command": True, **cmd}
    return {"has_command": False}


@router.post("/heartbeat")
def device_heartbeat(device_id: str, db: Session = Depends(get_db)):
    """Jetson Nano gửi heartbeat để báo còn online"""
    state = db.query(DeviceState).filter(DeviceState.device_id == device_id).first()
    if not state:
        state = DeviceState(device_id=device_id, is_online=True)
        db.add(state)
    else:
        state.is_online = True
        state.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "ok"}


@router.get("/status")
def get_all_devices(db: Session = Depends(get_db)):
    """Lấy trạng thái tất cả thiết bị"""
    devices = db.query(DeviceState).all()
    return devices
