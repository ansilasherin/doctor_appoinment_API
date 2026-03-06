from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey,
    Boolean, DateTime, Time, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class Specialty(str, enum.Enum):
    cardiologist = "Cardiologist"
    dentist = "Dentist"
    dermatologist = "Dermatologist"
    neurologist = "Neurologist"
    orthopedic = "Orthopedic"
    pediatrician = "Pediatrician"
    general_physician = "General Physician"
    gynecologist = "Gynecologist"
    ophthalmologist = "Ophthalmologist"
    psychiatrist = "Psychiatrist"
    ent_specialist = "ENT Specialist"
    urologist = "Urologist"


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialty = Column(SAEnum(Specialty), nullable=False)
    experience_years = Column(Integer, default=0)
    consultation_fee = Column(Float, nullable=False)
    avg_consultation_minutes = Column(Integer, default=30)
    bio = Column(Text, nullable=True)
    clinic_name = Column(String(200), nullable=True)
    clinic_address = Column(String(500), nullable=True)
    clinic_city = Column(String(100), nullable=True)
    qualification = Column(String(300), nullable=True)
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="doctor_profile")
    schedules = relationship("DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship(
        "Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id"
    )
    reviews = relationship("Review", back_populates="doctor")


class DoctorSchedule(Base):
    """Defines recurring weekly availability for a doctor."""
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)   # 0=Mon, 6=Sun
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="schedules")
