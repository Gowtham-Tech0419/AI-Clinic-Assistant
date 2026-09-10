from langchain.tools import tool
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.availability import get_available_slots
from app.models import Doctor, Department, Patient, Availability
import app.booking as booking_mod

# Helper to get a session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Safely get booking functions, with fallback
def get_booking_func(name):
    try:
        return getattr(booking_mod, name)
    except AttributeError:
        return None  # Function not available

# Get the functions we need (or None if missing)
book_appointment_by_slot_id = get_booking_func("book_appointment_by_slot_id")
cancel_appointment = get_booking_func("cancel_appointment")
reschedule_appointment = get_booking_func("reschedule_appointment")

# Custom exceptions from booking (if defined)
DoctorNotFoundError = getattr(booking_mod, "DoctorNotFoundError", Exception)
SlotNotAvailableError = getattr(booking_mod, "SlotNotAvailableError", Exception)
AppointmentNotFoundError = getattr(booking_mod, "AppointmentNotFoundError", Exception)

# ------------------------------------------------------------------
# TOOLS
# ------------------------------------------------------------------

@tool
def show_doctors() -> str:
    """Show all doctors with ID, name, department, and experience."""
    db = next(get_db())
    try:
        doctors = db.query(Doctor).all()
        if not doctors:
            return "No doctors found."
        lines = ["Doctors:"]
        for doc in doctors:
            dept = db.query(Department).filter(Department.id == doc.department_id).first()
            dept_name = dept.name if dept else "Unknown"
            lines.append(f"ID {doc.id}: {doc.name} ({dept_name}) - {doc.experience_years} yrs")
        return "\n".join(lines)
    finally:
        db.close()

@tool
def show_available_slots(doctor_id: int, date_str: str) -> str:
    """Show available slots for a doctor on a given date (YYYY-MM-DD)."""
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."
    db = next(get_db())
    try:
        slots = get_available_slots(db, doctor_id, target_date)
        if not slots:
            return f"No available slots for doctor {doctor_id} on {date_str}."
        lines = [f"Available slots for doctor {doctor_id} on {date_str}:"]
        for slot in slots:
            lines.append(f"  - {slot.slot_time}")
        return "\n".join(lines)
    finally:
        db.close()

@tool
def book_appointment_tool(doctor_id: int, slot_time: str, patient_id: Optional[int] = 1) -> str:
    """
    Book an appointment. slot_time must be 'YYYY-MM-DD HH:MM:SS'.
    This uses your `book_appointment_by_slot_id` function.
    """
    if book_appointment_by_slot_id is None:
        return "❌ Booking function not available. Please check your booking.py."

    try:
        slot_dt = datetime.fromisoformat(slot_time)
    except ValueError:
        return "Invalid time format. Use YYYY-MM-DD HH:MM:SS."

    db = next(get_db())
    try:
        # 1. Find the slot ID for this doctor and time (with 1‑second tolerance)
        slot = db.query(Availability).filter(
            Availability.doctor_id == doctor_id,
            Availability.slot_time >= slot_dt - timedelta(seconds=1),
            Availability.slot_time <= slot_dt + timedelta(seconds=1),
            Availability.is_booked == False
        ).first()
        if not slot:
            return f"❌ No available slot found for doctor {doctor_id} at {slot_time}. Please check the time."

        # 2. Check patient exists
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return f"❌ Patient with ID {patient_id} not found."

        # 3. Book using your function
        appointment = book_appointment_by_slot_id(db, patient_id, slot.id)
        return f"✅ Appointment booked! ID: {appointment.id}, Time: {appointment.appointment_time}"
    except Exception as e:
        return f"❌ Booking failed: {str(e)}"
    finally:
        db.close()

@tool
def cancel_appointment_tool(appointment_id: int) -> str:
    """Cancel an appointment by ID."""
    if cancel_appointment is None:
        return "❌ Cancel function not available in booking.py."
    db = next(get_db())
    try:
        appointment = cancel_appointment(db, appointment_id)
        return f"✅ Appointment ID {appointment.id} cancelled."
    except AppointmentNotFoundError as e:
        return f"❌ Appointment not found: {e}"
    except Exception as e:
        return f"❌ Cancellation failed: {str(e)}"
    finally:
        db.close()

@tool
def reschedule_appointment_tool(appointment_id: int, new_slot_time: str) -> str:
    """Reschedule an appointment to a new time (YYYY-MM-DD HH:MM:SS)."""
    if reschedule_appointment is None:
        return "❌ Reschedule function not available in booking.py."
    try:
        new_dt = datetime.fromisoformat(new_slot_time)
    except ValueError:
        return "Invalid time format. Use YYYY-MM-DD HH:MM:SS."
    db = next(get_db())
    try:
        appointment = reschedule_appointment(db, appointment_id, new_dt)
        return f"✅ Appointment rescheduled to {appointment.appointment_time}"
    except AppointmentNotFoundError as e:
        return f"❌ Appointment not found: {e}"
    except SlotNotAvailableError as e:
        return f"❌ New slot not available: {e}"
    except Exception as e:
        return f"❌ Reschedule failed: {str(e)}"
    finally:
        db.close()