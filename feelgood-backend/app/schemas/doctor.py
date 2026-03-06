from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import time
from app.models.doctor import Specialty


class ScheduleBase(BaseModel):
    day_of_week: int   # 0=Mon, 6=Sun
    start_time: time
    end_time: time
    is_active: bool = True

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v):
        if v not in range(7):
            raise ValueError("day_of_week must be 0-6")
        return v


class ScheduleOut(ScheduleBase):
    id: int
    doctor_id: int
    model_config = {"from_attributes": True}


class DoctorCreate(BaseModel):
    specialty: Specialty
    experience_years: int = 0
    consultation_fee: float
    avg_consultation_minutes: int = 30
    bio: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_city: Optional[str] = None
    qualification: Optional[str] = None
    schedules: List[ScheduleBase] = []


class DoctorUpdate(BaseModel):
    specialty: Optional[Specialty] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[float] = None
    avg_consultation_minutes: Optional[int] = None
    bio: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_city: Optional[str] = None
    qualification: Optional[str] = None
    is_available: Optional[bool] = None


class DoctorOut(BaseModel):
    id: int
    user_id: int
    specialty: Specialty
    experience_years: int
    consultation_fee: float
    avg_consultation_minutes: int
    bio: Optional[str]
    clinic_name: Optional[str]
    clinic_address: Optional[str]
    clinic_city: Optional[str]
    qualification: Optional[str]
    rating: float
    total_reviews: int
    is_available: bool
    schedules: List[ScheduleOut] = []
    # User fields flattened
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class DoctorListItem(BaseModel):
    id: int
    user_id: int
    name: Optional[str] = None
    specialty: Specialty
    experience_years: int
    consultation_fee: float
    rating: float
    total_reviews: int
    is_available: bool
    avatar_url: Optional[str] = None
    clinic_city: Optional[str] = None

    model_config = {"from_attributes": True}


class SlotOut(BaseModel):
    start_time: str   # "HH:MM"
    end_time: str
    is_available: bool


class AvailableSlotsResponse(BaseModel):
    date: str
    doctor_id: int
    slots: List[SlotOut]
