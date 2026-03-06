from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import Review

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
def get_stats(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()
    total_patients = db.query(User).filter(User.role == UserRole.patient).count()
    total_doctors = db.query(Doctor).count()
    total_appointments = db.query(Appointment).count()
    completed = db.query(Appointment).filter(Appointment.status == AppointmentStatus.completed).count()
    cancelled = db.query(Appointment).filter(Appointment.status == AppointmentStatus.cancelled).count()
    pending = db.query(Appointment).filter(Appointment.status == AppointmentStatus.pending).count()
    confirmed = db.query(Appointment).filter(Appointment.status == AppointmentStatus.confirmed).count()
    total_revenue = db.query(func.sum(Appointment.consultation_fee)).filter(
        Appointment.status == AppointmentStatus.completed,
        Appointment.payment_status == "paid",
    ).scalar() or 0.0

    return {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "appointments": {
            "total": total_appointments,
            "completed": completed,
            "cancelled": cancelled,
            "pending": pending,
            "confirmed": confirmed,
        },
        "total_revenue": round(total_revenue, 2),
    }


@router.get("/users")
def list_all_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/appointments/{appointment_id}/complete", status_code=200)
def mark_appointment_complete(
    appointment_id: int,
    current_user: User = Depends(require_role("admin", "doctor")),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = AppointmentStatus.completed
    db.commit()
    return {"message": "Appointment marked as completed"}
