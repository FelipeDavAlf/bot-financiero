import asyncio
import sys
import traceback
from services.nlp_service import NLPService

async def main():
    if len(sys.argv) < 2:
        print("Uso: python test_doc.py <ruta_al_archivo>")
        print("Ejemplo: python test_doc.py estado_de_cuenta.pdf")
        return
        
    file_path = sys.argv[1]
    nlp = NLPService()
    
    try:
        print(f"Probando procesar el archivo: {file_path}")
        print("Enviando a Gemini... (esperando a que lo procese internamente)")
        
        transactions = nlp.process_document(file_path)
        
        print(f"\n✅ ¡Éxito! Se extrajeron {len(transactions)} transacciones.")
        for t in transactions:
            print(f"- {t.date} | {t.transaction_type} | ${t.amount} | {t.description} | {t.source_account}")
            
    except Exception:
        print("\n❌ ERROR OCURRIDO:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
