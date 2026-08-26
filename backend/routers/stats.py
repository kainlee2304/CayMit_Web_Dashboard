"""
Router: Stats - Thống kê và dữ liệu biểu đồ
"""
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Prediction, SensorData, get_db

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Tổng hợp: tổng số lần phát hiện, phân loại theo bệnh"""
    total = db.query(func.count(Prediction.id)).scalar()

    # Đếm theo từng class
    class_counts = (
        db.query(Prediction.predicted_class, func.count(Prediction.id).label("count"))
        .group_by(Prediction.predicted_class)
        .all()
    )

    # Sensor mới nhất
    latest_sensor = db.query(SensorData).order_by(SensorData.created_at.desc()).first()

    return {
        "total_predictions": total,
        "class_breakdown": {row.predicted_class: row.count for row in class_counts},
        "latest_sensor": {
            "temperature": latest_sensor.temperature if latest_sensor else None,
            "humidity": latest_sensor.humidity if latest_sensor else None,
            "recorded_at": latest_sensor.created_at if latest_sensor else None,
        }
    }


@router.get("/chart/disease")
def get_disease_chart(days: int = 7, db: Session = Depends(get_db)):
    """Dữ liệu biểu đồ số lần phát hiện bệnh trong N ngày"""
    since = datetime.utcnow() - timedelta(days=days)

    results = (
        db.query(
            func.date(Prediction.created_at).label("date"),
            Prediction.predicted_class,
            func.count(Prediction.id).label("count"),
        )
        .filter(Prediction.created_at >= since)
        .group_by(func.date(Prediction.created_at), Prediction.predicted_class)
        .order_by(func.date(Prediction.created_at))
        .all()
    )

    # Chuyển thành format cho chart
    chart_data = {}
    for row in results:
        date_str = str(row.date)
        if date_str not in chart_data:
            chart_data[date_str] = {}
        chart_data[date_str][row.predicted_class] = row.count

    return {"days": days, "data": chart_data}


@router.get("/chart/sensor")
def get_sensor_chart(hours: int = 24, db: Session = Depends(get_db)):
    """Dữ liệu biểu đồ nhiệt độ, độ ẩm trong N giờ"""
    since = datetime.utcnow() - timedelta(hours=hours)

    results = (
        db.query(SensorData)
        .filter(SensorData.created_at >= since)
        .order_by(SensorData.created_at.asc())
        .all()
    )

    return {
        "hours": hours,
        "data": [
            {
                "time": row.created_at.isoformat(),
                "temperature": row.temperature,
                "humidity": row.humidity,
            }
            for row in results
        ]
    }
