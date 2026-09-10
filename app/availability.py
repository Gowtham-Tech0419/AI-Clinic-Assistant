from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from typing import List
from app.models import Availability


def get_available_slots(db: Session, doctor_id: int, target_date: date) -> List[Availability]:
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    slots = db.query(Availability).filter(
        and_(
            Availability.doctor_id == doctor_id,
            Availability.slot_time >= start_of_day,
            Availability.slot_time <= end_of_day,
            Availability.is_booked == False
        )
    ).all()
    return slots