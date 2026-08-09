# import google.generativeai as genai
# api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"
# genai.configure(api_key=api_key)
# for m in genai.list_models():
#     if 'generateContent' in m.supported_generation_methods:
#         print(m.name)
import json
import google.generativeai as genai



api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")  # or "gemini-1.5-pro"


SYSTEM_PROMPT = """
You are a helpful assistant for a clinic. Your role is to help patients book, cancel, or reschedule appointments, and to provide information about doctors and available slots.

CRITICAL RULES:
- NEVER diagnose diseases or conditions.
- NEVER prescribe medication or treatment.
- If a user asks for medical advice, politely decline and recommend they consult a doctor.
- Only recommend a department based on symptoms (e.g., "You may want to see a cardiologist for heart issues").
- Always be polite and professional.

Your task: Given the user's message, determine which action to take. Respond with a JSON object in the following format:
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
if user provide the slot information as today , tommorow or day after tommorow then convert it to the date format and provide the date in the parameters.
If the user's message is unclear or missing required information, set action to "unknown" and provide a helpful reply asking for the missing details.                               
If a user asks to reschedule an appointment but doesn't specify a valid available time, first fetch available slots and suggest them.
Only output the JSON object, no other text.
"""

def interpret_message(user_message: str) -> dict:
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}"
    response = model.generate_content(full_prompt)
    raw_text = response.text.strip()

    # Clean markdown code blocks if present
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()


    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "action": "unknown",
            "parameters": {},
            "reply": "I'm sorry, I didn't understand that. Could you rephrase?"
        }

    if "action" not in result or "reply" not in result:
        return {
            "action": "unknown",
            "parameters": {},
            "reply": "I'm having trouble processing your request. Please try again."
        }

    return result