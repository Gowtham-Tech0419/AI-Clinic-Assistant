from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Doctor, Patient, Availability
from app.booking import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    SlotNotAvailableError
)

# Create a database session
db = SessionLocal()

# Fetch Dr. Ravi, a patient, and a free slot
doctor = db.query(Doctor).filter(Doctor.name == "Dr. Ravi").first()
patient = db.query(Patient).first()
free_slot = db.query(Availability).filter(
    Availability.doctor_id == doctor.id,
    Availability.is_booked == False
).first()

print("Booking appointment...")
appt = book_appointment(db, patient.id, doctor.id, free_slot.slot_time)
print(f"Booked: appointment id={appt.id}, status={appt.status}")

print("\nTrying to double-book the same slot (should fail)...")
try:
    book_appointment(db, patient.id, doctor.id, free_slot.slot_time)
except SlotNotAvailableError as e:
    print(f"Correctly rejected: {e}")

print("\nRescheduling to a new slot...")
new_slot_time = free_slot.slot_time + timedelta(hours=1)
new_availability = Availability(
    doctor_id=doctor.id,
    slot_time=new_slot_time,
    is_booked=False
)
db.add(new_availability)
db.commit()

appt = reschedule_appointment(db, appt.id, new_slot_time)
print(f"Rescheduled: appointment id={appt.id}, new time={appt.appointment_time}")

print("\nCancelling appointment...")
appt = cancel_appointment(db, appt.id)
print(f"Cancelled: appointment id={appt.id}, status={appt.status}")