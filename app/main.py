from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Optional
import re
from app.database import SessionLocal
from app import schemas, models
from app.database import get_db
from app.booking import (
    book_appointment_by_slot_id,
    cancel_appointment,
    reschedule_appointment,
    SlotNotAvailableError,
    DoctorNotFoundError,
    AppointmentNotFoundError
)
from app.availability import get_available_slots
from app.llm import interpret_message, llm
from app.embeddings import query_documents
from app.models import Availability, Doctor, Patient, Appointment, Department
app = FastAPI(title="AI Clinic Assistant API", version="1.0")

# Serve static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("app/static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

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


# ----- NEW: Chat endpoint (rule-based) -----
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

# Helper handlers (could be moved to a separate module)
def handle_show_doctors():
    db = SessionLocal()
    try:
        doctors = db.query(models.Doctor).all()
        if not doctors:
            return "No doctors found."
        lines = ["Doctors:"]
        for doc in doctors:
            dept = db.query(models.Department).filter(models.Department.id == doc.department_id).first()
            dept_name = dept.name if dept else "Unknown"
            lines.append(f"ID {doc.id}: {doc.name} ({dept_name}) - {doc.experience_years} yrs")
        return "\n".join(lines)
    finally:
        db.close()

def handle_slots(message):
    match = re.search(r"doctor\s*(\d+)\s+on\s+(\d{4}-\d{2}-\d{2})", message, re.IGNORECASE)
    if not match:
        return "Please specify doctor ID and date, e.g., 'slots for doctor 1 on 2026-08-09'"
    doc_id = int(match.group(1))
    date_str = match.group(2)
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."
    db = SessionLocal()
    try:
        slots = get_available_slots(db, doc_id, target_date)
        if not slots:
            return f"No available slots for doctor {doc_id} on {date_str}."
        lines = [f"Available slots for doctor {doc_id} on {date_str}:"]
        for slot in slots:
            lines.append(f"  - {slot.slot_time}")
        return "\n".join(lines)
    finally:
        db.close()

def handle_book(message):
    match = re.search(r"doctor\s*(\d+)\s+at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", message, re.IGNORECASE)
    if not match:
        return "Please specify doctor ID and slot time, e.g., 'book with doctor 1 at 2026-08-09 10:00:00'"
    doc_id = int(match.group(1))
    time_str = match.group(2)
    try:
        slot_time = datetime.fromisoformat(time_str)
    except ValueError:
        return "Invalid time format. Use YYYY-MM-DD HH:MM:SS."
    patient_id = 1  # hardcoded for now
    db = SessionLocal()
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            return "Patient with ID 1 not found. Please seed the database."
        appointment = book_appointment(db, patient_id, doc_id, slot_time)
        return f"✅ Appointment booked! ID: {appointment.id}, Time: {appointment.appointment_time}"
    except Exception as e:
        return f"❌ Booking failed: {str(e)}"
    finally:
        db.close()

def handle_cancel(message):
    match = re.search(r"appointment\s*(\d+)", message, re.IGNORECASE)
    if not match:
        return "Please specify the appointment ID to cancel, e.g., 'cancel appointment 5'"
    appt_id = int(match.group(1))
    db = SessionLocal()
    try:
        appointment = cancel_appointment(db, appt_id)
        return f"✅ Appointment ID {appointment.id} cancelled."
    except Exception as e:
        return f"❌ Cancellation failed: {str(e)}"
    finally:
        db.close()

def handle_reschedule(message):
    match = re.search(r"appointment\s*(\d+)\s+to\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", message, re.IGNORECASE)
    if not match:
        return "Please specify appointment ID and new time, e.g., 'reschedule appointment 5 to 2026-08-09 11:00:00'"
    appt_id = int(match.group(1))
    time_str = match.group(2)
    try:
        new_time = datetime.fromisoformat(time_str)
    except ValueError:
        return "Invalid time format. Use YYYY-MM-DD HH:MM:SS."
    db = SessionLocal()
    try:
        appointment = reschedule_appointment(db, appt_id, new_time)
        return f"✅ Appointment rescheduled to {appointment.appointment_time}"
    except Exception as e:
        return f"❌ Reschedule failed: {str(e)}"
    finally:
        db.close()

def ensure_string(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        texts = []
        for item in value:
            if isinstance(item, dict) and item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts) if texts else "I didn't understand that."
    return str(value)

def extract_text_from_response(response):
    if hasattr(response, 'content'):
        content = response.content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    texts.append(part.get('text', ''))
                elif isinstance(part, str):
                    texts.append(part)
            return "\n".join(texts) if texts else "I couldn't generate a proper response."
        elif isinstance(content, str):
            return content
        else:
            return str(content)
    return str(response)

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        return {"reply": "Please say something."}

    # 1. Get structured interpretation from LLM
    interpretation = interpret_message(user_message)
    action = interpretation.get("action")
    params = interpretation.get("parameters", {})
    reply = ensure_string(interpretation.get("reply", ""))

    # 2. If the action is unknown, try RAG (retrieve + generate)
    if action == "unknown":
        try:
            # Retrieve relevant document chunks
            chunks = query_documents(user_message, top_k=3)
            if chunks:
                # Build context string
                context = "\n\n".join([
                    f"[Source: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
                    for chunk in chunks
                ])
                rag_prompt = f"""You are a helpful clinic assistant. Use the following retrieved documents to answer the user's question.
If the documents don't contain the answer, politely say you don't know and offer to connect them with a human.

Retrieved documents:
{context}

User question: {user_message}

Answer:"""
                try:
                    response = llm.invoke(rag_prompt)
                    final_reply = extract_text_from_response(response)
                except Exception as e:
                    print(f"RAG LLM error: {e}")
                    # Fallback to raw chunks as plain text
                    chunk_texts = [chunk['text'] for chunk in chunks]
                    final_reply = "I found this information in our clinic documents:\n\n" + "\n\n".join(chunk_texts)
            else:
                # No chunks found, use LLM's fallback reply
                final_reply = reply
        except Exception as e:
            print(f"RAG error: {e}")
            final_reply = reply

        return {"reply": ensure_string(final_reply)}

    # 3. Handle structured actions
    try:
        if action == "show_doctors":
            result = handle_show_doctors()
            final_reply = f"{reply}\n\n{result}" if result else reply

        elif action == "show_slots":
            doctor_id = params.get("doctor_id")
            date_str = params.get("date")
            if not doctor_id or not date_str:
                return {"reply": "Missing doctor ID or date. Please provide both."}
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                return {"reply": "Invalid date format. Use YYYY-MM-DD."}
            db = SessionLocal()
            try:
                slots = get_available_slots(db, doctor_id, target_date)
                if not slots:
                    slot_list = "No available slots."
                else:
                    slot_list = "\n".join([f"  - {slot.slot_time}" for slot in slots])
                final_reply = f"{reply}\n\n{slot_list}"
            finally:
                db.close()

        elif action == "book":
            doctor_id = params.get("doctor_id")
            slot_time_str = params.get("slot_time")
            if not doctor_id or not slot_time_str:
                return {"reply": "Missing doctor ID or slot time. Please provide both."}
            try:
                slot_time = datetime.fromisoformat(slot_time_str)
            except ValueError:
                return {"reply": "Invalid time format. Use YYYY-MM-DD HH:MM:SS."}
            patient_id = 1  # hardcoded for now
            db = SessionLocal()
            try:
                # Lookup slot with 1‑second tolerance
                slot = db.query(Availability).filter(
                    Availability.doctor_id == doctor_id,
                    Availability.slot_time >= slot_time - timedelta(seconds=1),
                    Availability.slot_time <= slot_time + timedelta(seconds=1),
                    Availability.is_booked == False
                ).first()
                if not slot:
                    return {"reply": "No available slot found at that time. Please check the time and try again."}
                appointment = book_appointment_by_slot_id(db, patient_id, slot.id)
                final_reply = f"{reply}\n\n✅ Appointment booked! ID: {appointment.id}, Time: {appointment.appointment_time}"
            except Exception as e:
                final_reply = f"❌ Booking failed: {str(e)}"
            finally:
                db.close()

        elif action == "cancel":
            appt_id = params.get("appointment_id")
            if not appt_id:
                return {"reply": "Missing appointment ID."}
            db = SessionLocal()
            try:
                appointment = cancel_appointment(db, appt_id)
                final_reply = f"{reply}\n\n✅ Appointment ID {appointment.id} cancelled."
            except Exception as e:
                final_reply = f"❌ Cancellation failed: {str(e)}"
            finally:
                db.close()

        elif action == "reschedule":
            appt_id = params.get("appointment_id")
            new_time_str = params.get("new_slot_time")
            if not appt_id or not new_time_str:
                return {"reply": "Missing appointment ID or new slot time."}
            try:
                new_time = datetime.fromisoformat(new_time_str)
            except ValueError:
                return {"reply": "Invalid time format. Use YYYY-MM-DD HH:MM:SS."}
            db = SessionLocal()
            try:
                appointment = reschedule_appointment(db, appt_id, new_time)
                final_reply = f"{reply}\n\n✅ Appointment rescheduled to {appointment.appointment_time}"
            except Exception as e:
                final_reply = f"❌ Reschedule failed: {str(e)}"
            finally:
                db.close()

        else:
            final_reply = "I'm not sure how to handle that. Please try again."

    except Exception as e:
        final_reply = f"An error occurred: {str(e)}"

    # 4. Final safety check: ensure string
    return {"reply": ensure_string(final_reply)}