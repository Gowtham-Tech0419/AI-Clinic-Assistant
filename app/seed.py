from datetime import datetime, timedelta
from app.database import engine, SessionLocal, Base
from app.models import Department, Doctor, Patient, Appointment, Availability

# Create all tables
Base.metadata.create_all(bind=engine)

# Create a session
db = SessionLocal()

# Create departments
cardiology = Department(name="Cardiology")
general = Department(name="General Medicine")
db.add_all([cardiology, general])
db.commit()

# Create doctors
dr_ravi = Doctor(name="Dr. Ravi", experience_years=8, department_id=cardiology.id)
dr_meera = Doctor(name="Dr. Meera", experience_years=5, department_id=general.id)
db.add_all([dr_ravi, dr_meera])
db.commit()

# Create a patient
patient1 = Patient(name="Arun Kumar", phone="9876543210")
db.add(patient1)
db.commit()

# Create one availability slot for Dr. Ravi (tomorrow at 10 AM)
slot = Availability(
    doctor_id=dr_ravi.id,
    slot_time=datetime.now() + timedelta(days=1, hours=10),
    is_booked=False,
)
db.add(slot)
db.commit()

print("Database seeded successfully!")