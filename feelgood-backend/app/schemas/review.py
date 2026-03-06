from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    appointment_id: int
    rating: float
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not (1.0 <= v <= 5.0):
            raise ValueError("Rating must be between 1.0 and 5.0")
        return round(v, 1)


class ReviewOut(BaseModel):
    id: int
    appointment_id: int
    doctor_id: int
    patient_id: int
    rating: float
    comment: Optional[str]
    created_at: datetime
    patient_name: Optional[str] = None

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    related_appointment_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkRead(BaseModel):
    notification_ids: list[int]
