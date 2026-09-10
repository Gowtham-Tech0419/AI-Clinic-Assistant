from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    doctors = relationship("Doctor", back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    experience_years = Column(Integer, default=0)
    department_id = Column(Integer, ForeignKey("departments.id"))

    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    availability = relationship("Availability", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    appointments = relationship("Appointment", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    appointment_time = Column(DateTime, nullable=False)
    status = Column(String, default="booked")

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    slot_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)

    doctor = relationship("Doctor", back_populates="availability")