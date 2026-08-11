from langchain_google_genai import ChatGoogleGenerativeAI
api_key = "Your_API_Key_Here"  # Replace with your actual API key
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=api_key,
    temperature=0.2,
    convert_system_message_to_human=True
)

__all__ = ['llm']