from datetime import datetime, timedelta
from app.database import engine, SessionLocal, Base
from app.models import Department, Doctor, Patient, Availability
import random

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data (optional) - be careful in production
db.query(Availability).delete()
db.query(Doctor).delete()
db.query(Department).delete()
db.query(Patient).delete()
db.commit()

# 1. Departments
departments = [
    "Cardiology", "Neurology", "Orthopedics", "General Medicine", "Pediatrics"
]
dept_objs = []
for name in departments:
    dept = Department(name=name)
    db.add(dept)
    db.flush()
    dept_objs.append(dept)

# 2. Doctors
doctors_data = [
    ("Dr. Ravi", 8, "Cardiology"),
    ("Dr. Meera", 5, "General Medicine"),
    ("Dr. Anjali", 10, "Neurology"),
    ("Dr. Sanjay", 12, "Orthopedics"),
    ("Dr. Priya", 6, "Pediatrics"),
]

doctor_objs = []
for name, exp, dept_name in doctors_data:
    dept = db.query(Department).filter(Department.name == dept_name).first()
    doc = Doctor(name=name, experience_years=exp, department_id=dept.id)
    db.add(doc)
    db.flush()
    doctor_objs.append(doc)

# 3. One patient (for testing)
patient = Patient(name="Test Patient", phone="1234567890")
db.add(patient)
db.flush()

# 4. Generate availability slots for each doctor for the next 7 days
start_date = datetime.now().date()
for days in range(7):
    day_date = start_date + timedelta(days=days)
    for doctor in doctor_objs:
        # For each doctor, create slots every hour from 9 AM to 5 PM
        for hour in range(9, 17):  # 9 AM to 4 PM
            slot_time = datetime.combine(day_date, datetime.min.time().replace(hour=hour))
            # Randomly mark some slots as booked (for testing)
            is_booked = random.choice([True, False]) if days < 2 else False  # first 2 days some booked
            # But we'll keep it simple: all slots available by default
            slot = Availability(
                doctor_id=doctor.id,
                slot_time=slot_time,
                is_booked=False
            )
            db.add(slot)

db.commit()
print(f"✅ Database seeded with {len(doctor_objs)} doctors, {len(departments)} departments, and many slots.")
db.close()