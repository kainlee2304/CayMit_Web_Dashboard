"""
Router: Sensors - Nhận và trả dữ liệu cảm biến
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SensorData, get_db
from routers.traceability import get_current_user

router = APIRouter(prefix="/api/sensors", tags=["Sensors"], dependencies=[Depends(get_current_user)])


class SensorIn(BaseModel):
    temperature: float
    humidity: float
    device_id: Optional[str] = None


class SensorOut(BaseModel):
    id: int
    temperature: float
    humidity: float
    device_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=SensorOut)
def create_sensor_data(data: SensorIn, db: Session = Depends(get_db)):
    """Jetson Nano gửi dữ liệu nhiệt độ, độ ẩm lên"""
    record = SensorData(
        temperature=data.temperature,
        humidity=data.humidity,
        device_id=data.device_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/latest", response_model=SensorOut)
def get_latest_sensor(device_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Lấy giá trị sensor mới nhất"""
    query = db.query(SensorData)
    if device_id:
        query = query.filter(SensorData.device_id == device_id)
    record = query.order_by(SensorData.created_at.desc()).first()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(404, "Chưa có dữ liệu cảm biến")
    return record


@router.get("/history", response_model=List[SensorOut])
def get_sensor_history(
    skip: int = 0,
    limit: int = 100,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lịch sử dữ liệu cảm biến"""
    query = db.query(SensorData)
    if device_id:
        query = query.filter(SensorData.device_id == device_id)
    return query.order_by(SensorData.created_at.desc()).offset(skip).limit(limit).all()
