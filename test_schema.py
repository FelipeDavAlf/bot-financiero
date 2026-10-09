from google import genai
from google.genai import types
from core.models import TransactionList
from core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

csv_content = """INITIAL_BALANCE;CREDITS;DEBITS;FINAL_BALANCE
0.00;25;210.59;-25;210.59;0.00"""

with open("test2.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)

document_file = client.files.upload(file="test2.csv")

prompt = "Extract transactions."

print("Calling API...")
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[prompt, document_file],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TransactionList,
        temperature=0.0 
    )
)
print("Response text:")
print(response.text)
