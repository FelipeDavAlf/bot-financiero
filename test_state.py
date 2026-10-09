from google import genai
import time
from core.config import settings

def main():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    csv_content = """INITIAL_BALANCE;CREDITS;DEBITS;FINAL_BALANCE
0.00;25;210.59;-25;210.59;0.00"""
    
    with open("test.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    print("Uploading...")
    document_file = client.files.upload(file="test.csv")
    print("State immediately after upload:", document_file.state)
    
    for i in range(5):
        time.sleep(2)
        document_file = client.files.get(name=document_file.name)
        print(f"State after {2*(i+1)}s:", document_file.state)

if __name__ == "__main__":
    main()
