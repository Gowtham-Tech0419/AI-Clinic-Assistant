import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"
# gemini-3.1-flash-lite-preview
# 1. LLM instance
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=api_key,
    temperature=0.2,
    convert_system_message_to_human=True
)

# 2. System prompt (static, contains JSON braces)
SYSTEM_PROMPT = """You are a helpful assistant for a clinic. Your role is to help patients book, cancel, or reschedule appointments, and to provide information about doctors and available slots.

CRITICAL RULES:
- NEVER diagnose diseases or conditions.
- NEVER prescribe medication or treatment.
- If a user asks for medical advice, politely decline and recommend they consult a doctor.
- Only recommend a department based on symptoms (e.g., "You may want to see a cardiologist for heart issues").
- Always be polite and professional.

Your task: Given the user's message and the conversation history, determine which action to take. Respond with a JSON object in the following format:
{
  "action": "show_doctors" | "show_slots" | "book" | "cancel" | "reschedule" | "unknown",
  "parameters": {
    // For show_slots: { "doctor_id": <int>, "date": "YYYY-MM-DD" }
    // For book: { "doctor_id": <int>, "slot_time": "YYYY-MM-DD HH:MM:SS" }
    // For cancel: { "appointment_id": <int> }
    // For reschedule: { "appointment_id": <int>, "new_slot_time": "YYYY-MM-DD HH:MM:SS" }
    // For show_doctors: {}
  },
  "reply": "A friendly, natural language reply to the user that acknowledges their request and may ask for clarification if needed."
}

If the user's message is unclear or missing required information, set action to "unknown" and provide a helpful reply asking for the missing details.
Only output the JSON object, no other text.
"""

# 3. Create prompt with static SystemMessage and history placeholder
system_msg = SystemMessage(content=SYSTEM_PROMPT)  # No template parsing
human_msg_template = HumanMessagePromptTemplate.from_template("{input}")

prompt = ChatPromptTemplate.from_messages([
    system_msg,
    MessagesPlaceholder(variable_name="history"),
    human_msg_template
])

# 4. Base chain (prompt → LLM → string output)
base_chain = prompt | llm | StrOutputParser()

# 5. In-memory storage for chat histories
chat_histories = {}

def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in chat_histories:
        chat_histories[session_id] = InMemoryChatMessageHistory()
    return chat_histories[session_id]

# 6. Wrap with history management
chain_with_history = RunnableWithMessageHistory(
    base_chain,
    get_chat_history,
    input_messages_key="input",
    history_messages_key="history"
)

# ==================== Fallback Parser ====================
def fallback_parse(user_message: str) -> dict:
    msg_lower = user_message.lower()
    if "doctors" in msg_lower and "show" in msg_lower:
        return {"action": "show_doctors", "parameters": {}, "reply": "Here are our doctors:"}
    if "slots" in msg_lower:
        match = re.search(r"doctor\s*(\d+)\s+on\s+(\d{4}-\d{2}-\d{2})", user_message, re.IGNORECASE)
        if match:
            return {"action": "show_slots", "parameters": {"doctor_id": int(match.group(1)), "date": match.group(2)}, "reply": f"Showing slots for doctor {match.group(1)} on {match.group(2)}:"}
        else:
            return {"action": "unknown", "parameters": {}, "reply": "Please specify doctor ID and date, e.g., 'slots for doctor 1 on 2026-08-09'."}
    if "book" in msg_lower:
        match = re.search(r"doctor\s*(\d+)\s+at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", user_message, re.IGNORECASE)
        if match:
            return {"action": "book", "parameters": {"doctor_id": int(match.group(1)), "slot_time": match.group(2)}, "reply": f"Booking with doctor {match.group(1)} at {match.group(2)}..."}
        else:
            return {"action": "unknown", "parameters": {}, "reply": "Please specify doctor ID and slot time, e.g., 'book with doctor 1 at 2026-08-09 10:00:00'."}
    if "cancel" in msg_lower:
        match = re.search(r"appointment\s*(\d+)", user_message, re.IGNORECASE)
        if match:
            return {"action": "cancel", "parameters": {"appointment_id": int(match.group(1))}, "reply": f"Cancelling appointment {match.group(1)}..."}
        else:
            return {"action": "unknown", "parameters": {}, "reply": "Please specify appointment ID, e.g., 'cancel appointment 5'."}
    if "reschedule" in msg_lower:
        match = re.search(r"appointment\s*(\d+)\s+to\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", user_message, re.IGNORECASE)
        if match:
            return {"action": "reschedule", "parameters": {"appointment_id": int(match.group(1)), "new_slot_time": match.group(2)}, "reply": f"Rescheduling appointment {match.group(1)} to {match.group(2)}..."}
        else:
            return {"action": "unknown", "parameters": {}, "reply": "Please specify appointment ID and new time, e.g., 'reschedule appointment 5 to 2026-08-09 11:00:00'."}
    return {"action": "unknown", "parameters": {}, "reply": "I'm not sure what you mean. Try: 'show doctors', 'slots for doctor 1 on 2026-08-09', 'book with doctor 1 at 2026-08-09 10:00:00', 'cancel appointment 5', 'reschedule appointment 5 to 2026-08-09 11:00:00'."}

# ==================== Main interpretation function ====================
def interpret_message(user_message: str) -> dict:
    session_id = "default"  # single user; later can be dynamic
    try:
        raw_output = chain_with_history.invoke(
            {"input": user_message},
            config={"configurable": {"session_id": session_id}}
        )
    except Exception as e:
        print(f"LLM error: {e}. Falling back to rule-based parser.")
        return fallback_parse(user_message)

    raw_text = raw_output.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        result = json.loads(raw_text)
        if "action" not in result or "reply" not in result:
            return fallback_parse(user_message)
    except json.JSONDecodeError:
        return fallback_parse(user_message)

    # History is automatically stored by RunnableWithMessageHistory
    return result