import asyncio
from services.nlp_service import NLPService
import traceback
from google.genai import types

async def main():
    nlp = NLPService()
    
    csv_content = """INITIAL_BALANCE;CREDITS;DEBITS;FINAL_BALANCE
0.00;25;210.59;-25;210.59;0.00

RELEASE_DATE;TRANSACTION_TYPE;REFERENCE_ID;TRANSACTION_NET_AMOUNT;PARTIAL_BALANCE
02-09-2026;Transferencia recibida;176884;800.00;800.00"""
    
    with open("test.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    try:
        print("Testing gemini-2.5-flash without response_mime_type...")
        document_file = nlp.client.files.upload(file="test.csv")
        response = nlp.client.models.generate_content(
            model='gemini-3.8-flash',
            contents=["Extrae las transacciones en JSON. Debe empezar con { y terminar con }.", document_file]
        )
        print("Response:", response.text)
    except Exception as e:
        print("Error:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
