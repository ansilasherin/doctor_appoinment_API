from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey,
    DateTime, Date, Time, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class AppointmentType(str, enum.Enum):
    in_person = "in_person"
    video = "video"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.pending)
    appointment_type = Column(SAEnum(AppointmentType), default=AppointmentType.in_person)
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)          # doctor's notes post-consultation
    consultation_fee = Column(Float, nullable=False)
    payment_status = Column(String(50), default="pending")  # pending, paid, refunded
    booking_ref = Column(String(20), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("User", back_populates="appointments_as_patient", foreign_keys=[patient_id])
    doctor = relationship("Doctor", back_populates="appointments", foreign_keys=[doctor_id])
    review = relationship("Review", back_populates="appointment", uselist=False)
