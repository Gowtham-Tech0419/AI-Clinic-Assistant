from app.database import SessionLocal
from app.models import Department, Doctor, Patient, Appointment, Availability

db = SessionLocal()

print("\n" + "=" * 60)
print("                  DATABASE CONTENTS")
print("=" * 60)

# Departments
print("\n--- DEPARTMENTS ---")
departments = db.query(Department).all()
for dept in departments:
    print(f"ID: {dept.id}, Name: {dept.name}")

# Doctors
print("\n--- DOCTORS ---")
doctors = db.query(Doctor).all()
for doc in doctors:
    print(f"ID: {doc.id}, Name: {doc.name}, Experience: {doc.experience_years}, Dept ID: {doc.department_id}")

# Patients
print("\n--- PATIENTS ---")
patients = db.query(Patient).all()
for pat in patients:
    print(f"ID: {pat.id}, Name: {pat.name}, Phone: {pat.phone}")

# Availability
print("\n--- AVAILABILITY SLOTS ---")
slots = db.query(Availability).all()
for slot in slots:
    print(f"ID: {slot.id}, Doctor ID: {slot.doctor_id}, Time: {slot.slot_time}, Booked: {slot.is_booked}")

# Appointments
print("\n--- APPOINTMENTS ---")
appointments = db.query(Appointment).all()
for appt in appointments:
    print(f"ID: {appt.id}, Patient ID: {appt.patient_id}, Doctor ID: {appt.doctor_id}, "
          f"Time: {appt.appointment_time}, Status: {appt.status}")

print("\n" + "=" * 60)
print("End of database view.")
print("=" * 60)

db.close()