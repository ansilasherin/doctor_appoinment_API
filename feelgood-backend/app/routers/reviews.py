from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import Review
from app.schemas.review import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewOut, status_code=201)
def create_review(
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Only patients can leave reviews")

    appt = db.query(Appointment).filter(
        Appointment.id == payload.appointment_id,
        Appointment.patient_id == current_user.id,
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found or not yours")
    if appt.status != AppointmentStatus.completed:
        raise HTTPException(status_code=400, detail="Can only review completed appointments")
    if appt.review:
        raise HTTPException(status_code=409, detail="Review already submitted for this appointment")

    review = Review(
        appointment_id=appt.id,
        doctor_id=appt.doctor_id,
        patient_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)

    # Recalculate doctor rating
    doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
    if doctor:
        all_reviews = db.query(Review).filter(Review.doctor_id == doctor.id).all()
        total_ratings = sum(r.rating for r in all_reviews) + payload.rating
        count = len(all_reviews) + 1
        doctor.rating = round(total_ratings / count, 2)
        doctor.total_reviews = count

    db.commit()
    db.refresh(review)
    return ReviewOut(
        **{k: v for k, v in review.__dict__.items() if not k.startswith("_")},
        patient_name=current_user.name,
    )


@router.get("/doctor/{doctor_id}", response_model=List[ReviewOut])
def get_doctor_reviews(
    doctor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    reviews = (
        db.query(Review)
        .options(joinedload(Review.patient))
        .filter(Review.doctor_id == doctor_id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        ReviewOut(
            **{k: v for k, v in r.__dict__.items() if not k.startswith("_")},
            patient_name=r.patient.name if r.patient else None,
        )
        for r in reviews
    ]
