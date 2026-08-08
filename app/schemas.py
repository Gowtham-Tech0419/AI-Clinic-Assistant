from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class SlotResponse(BaseModel):
    id: int
    slot_time: datetime
    is_booked: bool

    class Config:
        orm_mode = True


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    slot_id: int


class AppointmentUpdate(BaseModel):
    new_slot_id: int


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_time: datetime
    status: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None

    class Config:
        orm_mode = True