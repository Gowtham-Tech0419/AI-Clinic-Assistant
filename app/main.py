from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from datetime import datetime, date

import re
import os
import tempfile
import io
import numpy as np
import soundfile as sf

# === HF VOICE === local STT + TTS imports
from faster_whisper import WhisperModel
from transformers import pipeline as hf_pipeline

from app.database import SessionLocal
from app import  models

from app.booking import (
    cancel_appointment,
    reschedule_appointment,

)
from app.availability import get_available_slots
from app.embeddings import query_documents

from app.agent import run_agent
from app.embeddings import query_documents
from app.llm import llm

app = FastAPI(title="AI Clinic Assistant API", version="1.0")

# === HF VOICE === lazy-loaded models (loaded once, reused)
_stt_model = None
_tts_pipeline = None


def get_stt_model():
    """Load faster-whisper once. 'small' is a good CPU/quality trade-off."""
    global _stt_model
    if _stt_model is None:
        _stt_model = WhisperModel(
            "small",              # or "base", "medium", "large-v3"
            device="cpu",         # change to "cuda" if you have a GPU
            compute_type="int8",  # 8-bit quantization for CPU speed
        )
    return _stt_model


def get_tts_pipeline():
    """Load the TTS model once. MOSS-TTS-Nano is CPU-optimised."""
    global _tts_pipeline
    if _tts_pipeline is None:
        _tts_pipeline = hf_pipeline(
            "text-to-speech",
            model="OpenMOSS/MOSS-TTS-Nano",   # CPU-friendly, ~100M params
            device=-1,                        # -1 = CPU; 0 = first GPU
        )
    return _tts_pipeline


# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("app/static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ---------------- Chat helpers (unchanged logic) ----------------
class ChatRequest(BaseModel):
    message: str


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
    patient_id = 1
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


# === HF VOICE === The old /chat body, extracted so both text and voice use it.
async def process_chat(user_message: str) -> str:
    """Run the existing agent → RAG fallback pipeline and return a clean string."""
    if not user_message:
        return "Please say something."

    session_id = "default"
    try:
        reply = run_agent(user_message, session_id=session_id)
        if not isinstance(reply, str):
            reply = str(reply)

        if not reply or any(phrase in reply.lower() for phrase in
                            ["i don't know", "apologize", "not sure", "cannot"]):
            chunks = query_documents(user_message, top_k=3)
            if chunks:
                context = "\n\n".join(
                    [f"[Source: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
                     for chunk in chunks]
                )
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
                    final_reply = "I found this information:\n\n" + "\n\n".join(
                        [chunk['text'] for chunk in chunks]
                    )
            else:
                final_reply = reply
        else:
            final_reply = reply

    except Exception as e:
        print(f"Agent error: {e}. Falling back to RAG.")
        chunks = query_documents(user_message, top_k=3)
        if chunks:
            context = "\n\n".join(
                [f"[Source: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
                 for chunk in chunks]
            )
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
                final_reply = "I found this information:\n\n" + "\n\n".join(
                    [chunk['text'] for chunk in chunks]
                )
        else:
            final_reply = "I'm sorry, I couldn't find an answer. Please contact the clinic directly."

    return ensure_string(final_reply)


# ---------------- /chat (now just calls the helper) ----------------
@app.post("/chat")
async def chat(request: ChatRequest):
    reply = await process_chat(request.message.strip())
    return {"reply": reply}


# === HF VOICE === New endpoint: audio in → transcript + reply + spoken audio out
@app.post("/voice/chat")
async def voice_chat(audio: UploadFile = File(...)):
    """
    Accepts a browser-recorded audio file (webm/ogg/wav/mp3),
    transcribes it with faster-whisper,
    runs it through the SAME chatbot pipeline,
    and returns the reply plus a WAV of the spoken answer.
    """
    # 1) Save uploaded audio to a temp file
    suffix = os.path.splitext(audio.filename or "clip.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        audio_path = tmp.name

    # 2) STT — faster-whisper
    try:
        model = get_stt_model()
        segments, info = model.transcribe(
            audio_path,
            language="en",
            beam_size=5,
            vad_filter=True,           # voice activity detection
        )
        transcript = "".join(segment.text for segment in segments).strip()
    except Exception as e:
        print(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        try:
            os.unlink(audio_path)
        except OSError:
            pass

    if not transcript:
        return {"transcript": "", "reply": "I couldn't hear anything. Please try again.", "audio_b64": ""}

    # 3) Same pipeline as /chat
    reply = await process_chat(transcript)

    # 4) TTS — Hugging Face pipeline → WAV bytes → base64
    audio_b64 = ""
    try:
        tts = get_tts_pipeline()
        output = tts(reply)
        waveform = output["audio"]
        sampling_rate = output["sampling_rate"]

        # Convert to 16-bit PCM WAV in memory
        if isinstance(waveform, np.ndarray) and waveform.ndim > 1:
            waveform = waveform.squeeze()

        buffer = io.BytesIO()
        sf.write(buffer, waveform, sampling_rate, format="WAV", subtype="PCM_16")
        buffer.seek(0)
        import base64
        audio_b64 = base64.b64encode(buffer.read()).decode("utf-8")
    except Exception as e:
        print(f"TTS error: {e}")
        # Text reply is still returned; frontend will just skip playback.

    return {
        "transcript": transcript,
        "reply": reply,
        "audio_b64": audio_b64,
    }