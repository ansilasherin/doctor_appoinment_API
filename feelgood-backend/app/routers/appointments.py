import random
import string
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import Notification, NotificationType
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate, AppointmentCancel
from app.services.email_service import send_appointment_confirmation, send_appointment_cancellation

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _generate_booking_ref() -> str:
    return "FG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _create_notification(db: Session, user_id: int, ntype: NotificationType,
                          title: str, message: str, appointment_id: Optional[int] = None):
    notif = Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        message=message,
        related_appointment_id=appointment_id,
    )
    db.add(notif)


def _appointment_to_out(appt: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        appointment_date=appt.appointment_date,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        appointment_type=appt.appointment_type,
        symptoms=appt.symptoms,
        notes=appt.notes,
        consultation_fee=appt.consultation_fee,
        payment_status=appt.payment_status,
        booking_ref=appt.booking_ref,
        created_at=appt.created_at,
        doctor_name=appt.doctor.user.name if appt.doctor and appt.doctor.user else None,
        doctor_specialty=appt.doctor.specialty.value if appt.doctor else None,
        patient_name=appt.patient.name if appt.patient else None,
    )


@router.post("", response_model=AppointmentOut, status_code=201)
async def book_appointment(
    payload: AppointmentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.doctor:
        raise HTTPException(status_code=403, detail="Doctors cannot book appointments as patients")

    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.schedules), joinedload(Doctor.user))
        .filter(Doctor.id == payload.doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not doctor.is_available:
        raise HTTPException(status_code=400, detail="Doctor is not available for booking")

    # Check schedule exists for this day
    day_of_week = payload.appointment_date.weekday()
    schedule = next(
        (s for s in doctor.schedules if s.day_of_week == day_of_week and s.is_active), None
    )
    if not schedule:
        raise HTTPException(status_code=400, detail="Doctor has no schedule on this day")

    # Validate slot time falls within schedule
    if payload.start_time < schedule.start_time or payload.start_time >= schedule.end_time:
        raise HTTPException(status_code=400, detail="Requested time is outside doctor's schedule")

    # Check slot not already booked
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == payload.doctor_id,
        Appointment.appointment_date == payload.appointment_date,
        Appointment.start_time == payload.start_time,
        Appointment.status.in_([AppointmentStatus.pending, AppointmentStatus.confirmed]),
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    end_time = (
        datetime.combine(payload.appointment_date, payload.start_time)
        + timedelta(minutes=doctor.avg_consultation_minutes)
    ).time()

    # Unique booking ref
    ref = _generate_booking_ref()
    while db.query(Appointment).filter(Appointment.booking_ref == ref).first():
        ref = _generate_booking_ref()

    appt = Appointment(
        patient_id=current_user.id,
        doctor_id=doctor.id,
        appointment_date=payload.appointment_date,
        start_time=payload.start_time,
        end_time=end_time,
        appointment_type=payload.appointment_type,
        symptoms=payload.symptoms,
        consultation_fee=doctor.consultation_fee,
        booking_ref=ref,
        status=AppointmentStatus.confirmed,
    )
    db.add(appt)

    _create_notification(
        db, current_user.id,
        NotificationType.appointment_confirmed,
        "Appointment Confirmed",
        f"Your appointment with Dr. {doctor.user.name} on {payload.appointment_date} at {payload.start_time.strftime('%H:%M')} is confirmed. Ref: {ref}",
        None,
    )

    db.commit()
    db.refresh(appt)

    # Update notification with correct appointment_id
    notif = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.related_appointment_id == None,
        Notification.type == NotificationType.appointment_confirmed
    ).order_by(Notification.id.desc()).first()
    if notif:
        notif.related_appointment_id = appt.id
        db.commit()

    # Send email in background
    if current_user.email:
        background_tasks.add_task(
            send_appointment_confirmation,
            current_user.email,
            current_user.name,
            ref,
            doctor.user.name,
            str(payload.appointment_date),
            payload.start_time.strftime("%H:%M"),
            doctor.consultation_fee,
        )

    return _appointment_to_out(appt)


@router.get("", response_model=List[AppointmentOut])
def list_appointments(
    status: Optional[AppointmentStatus] = None,
    upcoming_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient),
    )

    if current_user.role == UserRole.patient:
        q = q.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == UserRole.doctor:
        if not current_user.doctor_profile:
            return []
        q = q.filter(Appointment.doctor_id == current_user.doctor_profile.id)
    # admin sees all

    if status:
        q = q.filter(Appointment.status == status)
    if upcoming_only:
        q = q.filter(Appointment.appointment_date >= date.today())

    appointments = q.order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc()).offset(skip).limit(limit).all()
    return [_appointment_to_out(a) for a in appointments]


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient),
    ).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Access control
    if current_user.role == UserRole.patient and appt.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == UserRole.doctor:
        if not current_user.doctor_profile or appt.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    return _appointment_to_out(appt)


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Only doctor or admin can update notes/status
    if current_user.role == UserRole.patient:
        raise HTTPException(status_code=403, detail="Patients cannot update appointment details directly")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(appt, field, value)
    db.commit()
    db.refresh(appt)
    return _appointment_to_out(appt)


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient),
    ).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Access control
    if current_user.role == UserRole.patient and appt.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == UserRole.doctor:
        if not current_user.doctor_profile or appt.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    if appt.status in (AppointmentStatus.cancelled, AppointmentStatus.completed):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {appt.status.value} appointment")

    appt.status = AppointmentStatus.cancelled
    if payload.reason:
        appt.notes = (appt.notes or "") + f"\nCancellation reason: {payload.reason}"

    _create_notification(
        db, appt.patient_id,
        NotificationType.appointment_cancelled,
        "Appointment Cancelled",
        f"Your appointment (Ref: {appt.booking_ref}) has been cancelled.",
        appt.id,
    )

    db.commit()
    db.refresh(appt)

    if appt.patient.email:
        background_tasks.add_task(
            send_appointment_cancellation,
            appt.patient.email,
            appt.patient.name,
            appt.booking_ref,
            appt.doctor.user.name if appt.doctor and appt.doctor.user else "Doctor",
            str(appt.appointment_date),
        )

    return _appointment_to_out(appt)
