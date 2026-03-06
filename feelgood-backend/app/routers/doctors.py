from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional, List
from datetime import date, datetime, time, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.doctor import Doctor, DoctorSchedule, Specialty
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.doctor import (
    DoctorCreate, DoctorUpdate, DoctorOut, DoctorListItem,
    ScheduleBase, ScheduleOut, AvailableSlotsResponse, SlotOut
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


def _enrich_doctor(doctor: Doctor) -> dict:
    data = {
        "id": doctor.id,
        "user_id": doctor.user_id,
        "specialty": doctor.specialty,
        "experience_years": doctor.experience_years,
        "consultation_fee": doctor.consultation_fee,
        "avg_consultation_minutes": doctor.avg_consultation_minutes,
        "bio": doctor.bio,
        "clinic_name": doctor.clinic_name,
        "clinic_address": doctor.clinic_address,
        "clinic_city": doctor.clinic_city,
        "qualification": doctor.qualification,
        "rating": doctor.rating,
        "total_reviews": doctor.total_reviews,
        "is_available": doctor.is_available,
        "schedules": doctor.schedules,
        "name": doctor.user.name if doctor.user else None,
        "avatar_url": doctor.user.avatar_url if doctor.user else None,
    }
    return data


@router.get("", response_model=List[DoctorListItem])
def list_doctors(
    specialty: Optional[Specialty] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_fee: Optional[float] = None,
    available_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Doctor).options(joinedload(Doctor.user))

    if specialty:
        q = q.filter(Doctor.specialty == specialty)
    if city:
        q = q.filter(Doctor.clinic_city.ilike(f"%{city}%"))
    if min_rating:
        q = q.filter(Doctor.rating >= min_rating)
    if max_fee:
        q = q.filter(Doctor.consultation_fee <= max_fee)
    if available_only:
        q = q.filter(Doctor.is_available == True)
    if search:
        q = q.join(User).filter(
            or_(
                User.name.ilike(f"%{search}%"),
                Doctor.clinic_name.ilike(f"%{search}%"),
            )
        )

    doctors = q.offset(skip).limit(limit).all()
    result = []
    for d in doctors:
        result.append(DoctorListItem(
            id=d.id,
            user_id=d.user_id,
            name=d.user.name if d.user else None,
            specialty=d.specialty,
            experience_years=d.experience_years,
            consultation_fee=d.consultation_fee,
            rating=d.rating,
            total_reviews=d.total_reviews,
            is_available=d.is_available,
            avatar_url=d.user.avatar_url if d.user else None,
            clinic_city=d.clinic_city,
        ))
    return result


@router.get("/specialties", tags=["Doctors"])
def list_specialties():
    return [s.value for s in Specialty]


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.schedules))
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DoctorOut(**_enrich_doctor(doctor))


@router.post("", response_model=DoctorOut, status_code=201)
def create_doctor_profile(
    payload: DoctorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.doctor, UserRole.admin):
        raise HTTPException(status_code=403, detail="Only doctors or admins can create doctor profiles")
    if current_user.doctor_profile:
        raise HTTPException(status_code=400, detail="Doctor profile already exists")

    doctor = Doctor(
        user_id=current_user.id,
        specialty=payload.specialty,
        experience_years=payload.experience_years,
        consultation_fee=payload.consultation_fee,
        avg_consultation_minutes=payload.avg_consultation_minutes,
        bio=payload.bio,
        clinic_name=payload.clinic_name,
        clinic_address=payload.clinic_address,
        clinic_city=payload.clinic_city,
        qualification=payload.qualification,
    )
    db.add(doctor)
    db.flush()

    for sched in payload.schedules:
        db.add(DoctorSchedule(doctor_id=doctor.id, **sched.model_dump()))

    db.commit()
    db.refresh(doctor)
    return DoctorOut(**_enrich_doctor(doctor))


@router.put("/{doctor_id}", response_model=DoctorOut)
def update_doctor_profile(
    doctor_id: int,
    payload: DoctorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if current_user.role != UserRole.admin and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return DoctorOut(**_enrich_doctor(doctor))


@router.post("/{doctor_id}/schedules", response_model=ScheduleOut, status_code=201)
def add_schedule(
    doctor_id: int,
    payload: ScheduleBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if current_user.role != UserRole.admin and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    sched = DoctorSchedule(doctor_id=doctor_id, **payload.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.delete("/{doctor_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    doctor_id: int,
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if current_user.role != UserRole.admin and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    sched = db.query(DoctorSchedule).filter(
        DoctorSchedule.id == schedule_id,
        DoctorSchedule.doctor_id == doctor_id
    ).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(sched)
    db.commit()


@router.get("/{doctor_id}/slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    doctor_id: int,
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.schedules))
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    day_of_week = target_date.weekday()  # 0=Mon
    schedule = next(
        (s for s in doctor.schedules if s.day_of_week == day_of_week and s.is_active), None
    )

    if not schedule:
        return AvailableSlotsResponse(date=date_str, doctor_id=doctor_id, slots=[])

    # Get booked slots for this date
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_([AppointmentStatus.pending, AppointmentStatus.confirmed]),
    ).all()
    booked_starts = {a.start_time for a in booked}

    # Generate slots
    slots = []
    slot_minutes = doctor.avg_consultation_minutes
    current = datetime.combine(target_date, schedule.start_time)
    end = datetime.combine(target_date, schedule.end_time)

    now = datetime.now()
    while current + timedelta(minutes=slot_minutes) <= end:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=slot_minutes)).time()
        is_past = target_date == date.today() and current <= now
        is_booked = slot_start in booked_starts
        slots.append(SlotOut(
            start_time=slot_start.strftime("%H:%M"),
            end_time=slot_end.strftime("%H:%M"),
            is_available=not is_booked and not is_past,
        ))
        current += timedelta(minutes=slot_minutes)

    return AvailableSlotsResponse(date=date_str, doctor_id=doctor_id, slots=slots)
