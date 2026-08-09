import google.generativeai as genai
api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
response = model.generate_content("Say hello")
print(response.text)

# api_key = "AQ.Ab8RN6IKHO4pNuFxW9--4pXM-3JSLmTLrpC2IJufPhIrF4wm0g"
# genai.configure(api_key=api_key)
# for m in genai.list_models():
#     if 'generateContent' in m.supported_generation_methods:
#         print(m.name)