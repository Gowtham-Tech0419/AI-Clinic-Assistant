from sqlalchemy.orm import Session
from app.models import Doctor, Patient, Appointment, Availability


class SlotNotAvailableError(Exception):
    pass


class DoctorNotFoundError(Exception):
    pass


class AppointmentNotFoundError(Exception):
    pass


def book_appointment(db: Session, patient_id: int, doctor_id: int, slot_time):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if doctor is None:
        raise DoctorNotFoundError(f"No doctor with id {doctor_id}")

    slot = db.query(Availability).filter(
        Availability.doctor_id == doctor_id,
        Availability.slot_time == slot_time,
        Availability.is_booked == False
    ).first()

    if slot is None:
        raise SlotNotAvailableError(
            f"Doctor {doctor.name} is not available at {slot_time}"
        )

    try:
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_time=slot_time,
            status="booked"
        )
        db.add(appointment)
        slot.is_booked = True
        db.commit()
        db.refresh(appointment)
        return appointment
    except Exception:
        db.rollback()
        raise


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

    new_slot = db.query(Availability).filter(
        Availability.doctor_id == appointment.doctor_id,
        Availability.slot_time == new_slot_time,
        Availability.is_booked == False
    ).first()
    if new_slot is None:
        raise SlotNotAvailableError("The requested new slot is not available")

    try:
        old_slot = db.query(Availability).filter(
            Availability.doctor_id == appointment.doctor_id,
            Availability.slot_time == appointment.appointment_time
        ).first()
        if old_slot is not None:
            old_slot.is_booked = False

        new_slot.is_booked = True
        appointment.appointment_time = new_slot_time

        db.commit()
        db.refresh(appointment)
        return appointment
    except Exception:
        db.rollback()
        raise