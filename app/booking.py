from sqlalchemy.orm import Session
from app.models import Doctor, Patient, Appointment, Availability


class SlotNotAvailableError(Exception):
    pass


class DoctorNotFoundError(Exception):
    pass


class AppointmentNotFoundError(Exception):
    pass


def book_appointment_by_slot_id(db: Session, patient_id: int, slot_id: int) -> Appointment:
    # Get the slot and lock it
    slot = db.query(Availability).filter(Availability.id == slot_id).first()
    if not slot:
        raise ValueError("Slot not found")
    if slot.is_booked:
        raise ValueError("Slot is already booked")
    
    # Mark as booked and create appointment
    slot.is_booked = True
    db.add(slot)
    db.flush()
    
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=slot.doctor_id,
        appointment_time=slot.slot_time,
        status="booked"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

def cancel_appointment(db: Session, appointment_id: int):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise AppointmentNotFoundError(f"No appointment with id {appointment_id}")

    try:
        appointment.status = "cancelled"
        slot = db.query(Availability).filter(
            Availability.doctor_id == appointment.doctor_id,
            Availability.slot_time == appointment.appointment_time
        ).first()
        if slot is not None:
            slot.is_booked = False
        db.commit()
        db.refresh(appointment)
        return appointment
    except Exception:
        db.rollback()
        raise


def reschedule_appointment(db: Session, appointment_id: int, new_slot_time):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise AppointmentNotFoundError(f"No appointment with id {appointment_id}")

    # Find or create the new slot
    new_slot = db.query(Availability).filter(
        Availability.doctor_id == appointment.doctor_id,
        Availability.slot_time == new_slot_time
    ).first()
    
    if new_slot is None:
        new_slot = Availability(
            doctor_id=appointment.doctor_id,
            slot_time=new_slot_time,
            is_booked=False
        )
        db.add(new_slot)
        db.flush()

    if new_slot.is_booked:
        raise SlotNotAvailableError("The requested new slot is already booked")

    try:
        # Free old slot
        old_slot = db.query(Availability).filter(
            Availability.doctor_id == appointment.doctor_id,
            Availability.slot_time == appointment.appointment_time
        ).first()
        if old_slot is not None:
            old_slot.is_booked = False

        # Book new slot
        new_slot.is_booked = True
        appointment.appointment_time = new_slot_time

        db.commit()
        db.refresh(appointment)
        return appointment
    except Exception:
        db.rollback()
        raise