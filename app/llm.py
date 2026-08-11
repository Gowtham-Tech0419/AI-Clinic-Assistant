# gemini-3.1-flash-lite-preview
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from app.tools import (
    show_doctors,
    show_available_slots,
    book_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool
)
# ==================== LLM with tools ====================
# List of tools
tools = [
    show_doctors,
    show_available_slots,
    book_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool
]
api_key = "Your_API_Key_Here"  # Replace with your actual API key
# Bind tools to the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=api_key,
    temperature=0.2,
    convert_system_message_to_human=True
).bind_tools(tools)

# ==================== System prompt ====================
SYSTEM_PROMPT = """You are a helpful assistant for a clinic. Your role is to help patients book, cancel, or reschedule appointments, and to provide information about doctors and available slots.

CRITICAL RULES:
- NEVER diagnose diseases or conditions.
- NEVER prescribe medication or treatment.
- If a user asks for medical advice, politely decline and recommend they consult a doctor.
- Only recommend a department based on symptoms (e.g., "You may want to see a cardiologist for heart issues").
- Always be polite and professional.

For questions about insurance, policies, visiting hours, or doctor profiles, ALWAYS use the retrieved documents if available. If the documents don't contain the answer, say you don't know and suggest contacting the front desk.

You have tools available to help users. Use them when appropriate.
"""

# ==================== Memory / History ====================
chat_histories = {}

def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in chat_histories:
        chat_histories[session_id] = InMemoryChatMessageHistory()
    return chat_histories[session_id]

# ==================== Conversation wrapper with history ====================
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Chain: prompt -> LLM (with tools)
chain = prompt | llm

# Wrap with history
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_chat_history,
    input_messages_key="input",
    history_messages_key="history"
)

# ==================== Main function ====================
def interpret_message(user_message: str, session_id: str = "default") -> dict:
    """
    Process user message, possibly invoking tools, and return a response.
    Returns a dict with 'reply' (the assistant's final message) and optionally 'tool_calls' (for debugging).
    """
    # Invoke chain with history
    response = chain_with_history.invoke(
        {"input": user_message},
        config={"configurable": {"session_id": session_id}}
    )

    # Check if the LLM wants to call any tools
    tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []

    final_reply = None

    if tool_calls:
        # We have tool calls – execute them
        # For simplicity, we'll just call the first tool (most relevant)
        # In a more advanced agent, you'd loop and handle multiple calls.
        tool_call = tool_calls[0]
        tool_name = tool_call['name']
        tool_args = tool_call['args']

        # Map tool name to function
        tool_map = {
            "show_doctors": show_doctors,
            "show_available_slots": show_available_slots,
            "book_appointment_tool": book_appointment_tool,
            "cancel_appointment_tool": cancel_appointment_tool,
            "reschedule_appointment_tool": reschedule_appointment_tool,
        }
        func = tool_map.get(tool_name)
        if func:
            try:
                result = func.invoke(tool_args)  # tool.invoke expects dict of args
                # We need to get the string result (tools return strings)
                # Since our tools are decorated with @tool, they are callable and return string.
                final_reply = result
            except Exception as e:
                final_reply = f"Error executing tool {tool_name}: {str(e)}"
        else:
            final_reply = f"Unknown tool: {tool_name}"

        # Also need to add the assistant's response (which includes tool calls) to history?
        # The wrapper automatically handles adding user and assistant messages.
        # But we also need to add the tool result as a message? Actually, the wrapper only stores the user and AI messages.
        # To keep it simple, we return the final reply and let the frontend display it.
        # For proper multi-turn with tool results, we'd need to manually add a tool result message.
        # But for a simple demo, we'll just return the tool result.
    else:
        # No tool call – just return the assistant's reply
        final_reply = response.content if hasattr(response, 'content') else str(response)

    return {"reply": final_reply}

# For backward compatibility, also expose llm if needed by main.py
__all__ = ['interpret_message', 'llm']