from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List
from app import schemas, models
from app.database import get_db
from app.booking import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    SlotNotAvailableError,
    DoctorNotFoundError,
    AppointmentNotFoundError
)
from app.availability import get_available_slots

app = FastAPI(title="AI Clinic Assistant API", version="1.0")


@app.get("/availability", response_model=List[schemas.SlotResponse])
def get_availability(
    doctor_id: int = Query(..., description="Doctor ID"),
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    slots = get_available_slots(db, doctor_id, target_date)
    return slots


@app.post("/appointments", response_model=schemas.AppointmentResponse, status_code=201)
def create_appointment(
    patient_id: int = Query(..., description="Patient ID"),
    doctor_id: int = Query(..., description="Doctor ID"),
    slot_time: datetime = Query(..., description="Slot time in ISO format, e.g. 2026-08-08T10:00:00"),
    db: Session = Depends(get_db)
):
    try:
        new_appointment = book_appointment(db, patient_id, doctor_id, slot_time)
    except DoctorNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SlotNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch patient and doctor names for the response
    patient = db.query(models.Patient).filter(models.Patient.id == new_appointment.patient_id).first()
    doctor = db.query(models.Doctor).filter(models.Doctor.id == new_appointment.doctor_id).first()

    response = schemas.AppointmentResponse(
        id=new_appointment.id,
        patient_id=new_appointment.patient_id,
        doctor_id=new_appointment.doctor_id,
        appointment_time=new_appointment.appointment_time,
        status=new_appointment.status,
        patient_name=patient.name if patient else None,
        doctor_name=doctor.name if doctor else None
    )
    return response


@app.delete("/appointments/{appointment_id}", status_code=204)
def cancel_appointment_endpoint(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:
        cancel_appointment(db, appointment_id)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None  # 204 No Content


@app.put("/appointments/{appointment_id}", response_model=schemas.AppointmentResponse)
def reschedule_appointment_endpoint(
    appointment_id: int,
    new_slot_time: datetime = Query(..., description="New slot time in ISO format"),
    db: Session = Depends(get_db)
):
    try:
        updated = reschedule_appointment(db, appointment_id, new_slot_time)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SlotNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch patient and doctor names
    patient = db.query(models.Patient).filter(models.Patient.id == updated.patient_id).first()
    doctor = db.query(models.Doctor).filter(models.Doctor.id == updated.doctor_id).first()

    response = schemas.AppointmentResponse(
        id=updated.id,
        patient_id=updated.patient_id,
        doctor_id=updated.doctor_id,
        appointment_time=updated.appointment_time,
        status=updated.status,
        patient_name=patient.name if patient else None,
        doctor_name=doctor.name if doctor else None
    )
    return response