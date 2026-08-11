from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from app.llm import llm
from app.tools import (
    show_doctors,
    show_available_slots,
    book_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool
)

tools = [
    show_doctors,
    show_available_slots,
    book_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool
]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a helpful assistant for a clinic. Your role is to help patients book, cancel, or reschedule appointments, and to provide information about doctors and available slots.

CRITICAL RULES:
- NEVER diagnose diseases or conditions.
- NEVER prescribe medication or treatment.
- If a user asks for medical advice, politely decline and recommend they consult a doctor.
- Only recommend a department based on symptoms (e.g., "You may want to see a cardiologist for heart issues").
- Always be polite and professional.

You have access to the following tools. USE THEM whenever appropriate to fulfill the user's request:
- show_doctors: List all doctors.
- show_available_slots: Show slots for a doctor on a given date.
- book_appointment_tool: Book an appointment with a doctor at a specific time.
- cancel_appointment_tool: Cancel an existing appointment.
- reschedule_appointment_tool: Reschedule an existing appointment.

For questions about insurance, policies, visiting hours, or general clinic information, you can use your own knowledge or ask the user for more details. If you don't know, say you don't know.

Always use the tools when the user wants to book, cancel, or reschedule, or see available slots.
"""


# Create a memory saver (in-memory checkpoint)
memory = MemorySaver()

# Create the agent with checkpointer
try:
    agent = create_react_agent(
        model=llm_with_tools,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
except TypeError:
    try:
        agent = create_react_agent(
            model=llm_with_tools,
            tools=tools,
            state_modifier=SystemMessage(content=SYSTEM_PROMPT),
            checkpointer=memory
        )
    except TypeError:
        agent = create_react_agent(
            model=llm_with_tools,
            tools=tools,
            prompt=SYSTEM_PROMPT,
            checkpointer=memory
        )

def run_agent(user_message: str, session_id: str = "default") -> str:
    """
    Run the agent with the given user message, using persistent memory.
    """
    config = {"configurable": {"thread_id": session_id}}
    inputs = {"messages": [("user", user_message)]}
    result = agent.invoke(inputs, config=config)

    # Extract the last AI message content as a string
    for msg in reversed(result["messages"]):
        if hasattr(msg, "type") and msg.type == "ai":
            content = msg.content
            if isinstance(content, list):
                texts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        texts.append(part)
                return "\n".join(texts) if texts else "I couldn't generate a response."
            elif isinstance(content, str):
                return content
            else:
                return str(content)

    # Fallback
    last = result["messages"][-1]
    return str(last.content) if hasattr(last, "content") else str(last)

__all__ = ['run_agent']