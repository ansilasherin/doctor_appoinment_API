from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, time, datetime
from app.models.appointment import AppointmentStatus, AppointmentType


class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: date
    start_time: time
    appointment_type: AppointmentType = AppointmentType.in_person
    symptoms: Optional[str] = None

    @field_validator("appointment_date")
    @classmethod
    def date_not_past(cls, v):
        from datetime import date as dt
        if v < dt.today():
            raise ValueError("Cannot book appointment in the past")
        return v


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    payment_status: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    appointment_type: AppointmentType
    symptoms: Optional[str]
    notes: Optional[str]
    consultation_fee: float
    payment_status: str
    booking_ref: str
    created_at: datetime
    # Nested
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AppointmentCancel(BaseModel):
    reason: Optional[str] = None
