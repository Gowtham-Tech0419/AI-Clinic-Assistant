
import google.generativeai as genai

api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"

print(f"API Key loaded: {api_key[:5]}...{api_key[-5:]}")  # shows partial

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content("Say hello")
print(response.text)